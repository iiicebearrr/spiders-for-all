import json
import logging
import re
import subprocess
from bs4 import BeautifulSoup
from enum import Enum, auto
from operator import attrgetter
from pathlib import Path
from functools import cached_property
from typing import Callable, TypeAlias, Generator, BinaryIO, Any, Optional
from itertools import chain
from traceback import format_tb

from rich.progress import (
    Progress,
    DownloadColumn,
    TransferSpeedColumn,
    TaskID,
    TextColumn,
    SpinnerColumn,
    TimeElapsedColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from concurrent import futures
from rich.console import Console
import requests

from spiders_for_all.bilibili import models
from spiders_for_all.utils.helper import user_agent_headers, rm_tree
from spiders_for_all.utils.logger import default_logger as logger
from spiders_for_all.conf import settings

Media: TypeAlias = models.PlayVideo | models.PlayAudio
Medias: TypeAlias = list[Media]
Videos: TypeAlias = list[models.PlayVideo]
Audios: TypeAlias = list[models.PlayAudio]
VideoPath: TypeAlias = Path
AudioPath: TypeAlias = Path
BvidList: TypeAlias = str | list[str] | Path | list[Path] | BinaryIO

API_PREFIX = "https://www.bilibili.com/video/"

# Regex to find playinfo in <script>window.__playinfo__=</script>
RGX_FIND_PLAYINFO = re.compile(r"<script>window\.__playinfo__=(.*?)</script>")
RGX_FIND_TITLE = re.compile(r"<title>(.*?)</title>")
RGX_CHECK_FILENAME = re.compile(r"[\\/:*?\"<>|]")

HIGHEST_QUALITY = 0

CHUNK_SIZE = 1024 * 1024

NOT_SET = object()


def get_ffmpeg_executable() -> str:
    return "ffmpeg"
    # FIXME: which may not work on windows
    # return subprocess.check_output(["which", "ffmpeg"]).decode().strip()


class MediaType(Enum):
    VIDEO = "video"
    AUDIO = "audio"


class DownloadState(Enum):
    NOT_STARTED = auto()
    STARTED = auto()
    FINISHED = auto()
    FAILED = auto()


class BaseTask:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._finished = False

    @property
    def finished(self) -> bool:
        return self._finished

    def start(self) -> Any:
        raise NotImplementedError()


class LinerTask(BaseTask):
    def __init__(
        self,
        fn: Callable,
        name: str | None = None,
        args: tuple | None = None,
        kwargs: dict | None = None,
        delay_args: Optional[Callable] = None,
        delay_kwargs: Optional[Callable] = None,
    ):
        """
        Liner task
        Args:
            fn: Function to call
            name: Name of the task
            args: Args to pass to the function
            kwargs: Kwargs to pass to the function
            delay_args: A callable object to return the args to pass to the function when calling
            delay_kwargs: A callable object to return the kwargs to pass to the function when calling

        About delay_args and delay_kwargs:

            Example:

                class A:

                    def __init__(self):
                        self.val = 1

                def fn_1(inst: A):
                    inst.val = 2

                def fn_2(val):
                    pass

                inst = A()

                task_1 = LinerTask(fn_1, args=(inst,))
                task_2 = LinerTask(fn_2, delay_args=lambda: (inst.val,))
                task_3 = LinerTask(fn_2, args=(inst.val,))

                task_1.start() # inst.val set to 2
                task_2.start() # will call fn_2 with new value 2
                task_3.start() # will call fn_2 with old value 1

        """
        self.fn = fn
        self.args = tuple() if args is None else args
        self.kwargs = {} if kwargs is None else kwargs
        self.task_name = name or str(fn)
        self.delay_args = delay_args
        self.delay_kwargs = delay_kwargs

        self.delay = any((self.delay_args, self.delay_kwargs))
        super().__init__()

    def start(self):
        if self.delay:
            if callable(self.delay_args):
                self.args = self.delay_args()
            if callable(self.delay_kwargs):
                self.kwargs = self.delay_kwargs()
        ret = self.fn(*self.args, **self.kwargs)
        self._finished = True
        return ret


class DownloadMediaTask(BaseTask):
    referer = "https://www.bilibili.com"

    def __init__(
        self,
        media: Media,
        save_dir: Path | str,
        *args,
        chunk_size: int = CHUNK_SIZE,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.media = media
        self.save_dir = Path(save_dir) if not isinstance(save_dir, Path) else save_dir
        self.chunk_size = chunk_size
        self.save_dir.unlink(missing_ok=True)
        self._total_size: int | None = None

    @property
    def total_size(self) -> int:
        if self._total_size is None:
            raise ValueError("Total size not fetched yet")
        return self._total_size

    @cached_property
    def headers(self) -> dict[str, str]:
        return {
            "Referer": self.referer,
            **user_agent_headers(),
        }

    def start(self) -> Generator[bytes | int, None, None]:
        with open(self.save_dir, "wb") as f:
            with requests.get(
                self.media.base_url, headers=self.headers, stream=True
            ) as resp:
                resp.raise_for_status()
                if self._total_size is None:
                    self._total_size = int(resp.headers["Content-Length"])
                    yield self._total_size
                for chunk in resp.iter_content(chunk_size=self.chunk_size):
                    yield chunk
                    f.write(chunk)

        self._finished = True

    def __str__(self):
        return str(self.media)


class DownloadVideoTask(DownloadMediaTask):
    def __init__(
        self,
        media: models.PlayVideo,
        save_dir: Path | str,
        quality_map: dict[int, str],
        chunk_size: int = CHUNK_SIZE,
    ):
        super().__init__(media, save_dir, chunk_size=chunk_size)
        self.quality_map = quality_map

    def __str__(self):
        return f"Download video <{self.quality_map[self.media.quality]}>"  # type: ignore


class DownloadAudioTask(DownloadMediaTask):
    def __str__(self):
        return "Download audio"


class Downloader:
    origin: str = "https://www.bilibili.com"
    api: str = "https://www.bilibili.com/video/{bvid}/"
    default_video_suffix: str = ".mp4"

    def __init__(
        self,
        bvid: str,
        save_dir: str | Path,
        filename: str | None = None,
        remove_temp_dir: bool = True,
        sess_data: str | None = None,
        quality: int = HIGHEST_QUALITY,
        codecs: str | None = None,
        ffmpeg_params: list[str] | None = None,
        process_func: Callable[[VideoPath, AudioPath], None] | None = None,
        from_cli: bool = True,
        exit_on_error: bool = False,
        ffmpeg: str | None = None,
        disable_terminal_log: bool = False,
    ):
        self.bvid = bvid
        self.save_dir = save_dir if isinstance(save_dir, Path) else Path(save_dir)
        self.temp_dir = self.save_dir / ".temp"

        self.audio_temp_path = self.temp_dir / "audio-temp.wav"
        self.remove_temp_dir = remove_temp_dir
        self.sess_data = sess_data
        self.quality = quality
        self.codecs = codecs
        self.ffmpeg_params = ffmpeg_params
        self.from_cli = from_cli

        self.process_func = process_func

        self.api = self.__class__.api.format(bvid=bvid)

        self.save_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.log_file = self.get_logfile()

        self.audios_path: list[Path] = []
        self.temp_audio: Path | None = None
        self.video_path: Path | None = None

        self.tasks: list[LinerTask] = []
        self.downloading_tasks: list[DownloadMediaTask] = []

        self.exit_on_error = exit_on_error
        self.ffmpeg = ffmpeg or get_ffmpeg_executable()
        self.disable_terminal_log = disable_terminal_log
        self.console: Console | None = None

        self._filename = filename

        self.exc_info: tuple[Any, Any, Any] = (NOT_SET, NOT_SET, NOT_SET)
        self.state: DownloadState = DownloadState.NOT_STARTED

    def __enter__(self):
        self.state = DownloadState.STARTED

        self.console = self.get_console()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.state = DownloadState.FAILED
            self.exc_info = (exc_type, exc_val, exc_tb)
            self.log(
                f"[{self.downloader_name}] Error occurred: {exc_val}",
                level=logging.ERROR,
                traceback=exc_tb,
            )

        else:
            self.state = DownloadState.FINISHED
            self.log(
                f"[{self.downloader_name}] Download finished successfully",
                level=logging.INFO,
            )

        if self.console.record:  # type: ignore
            self.console.save_text(str(self.log_file))  # type: ignore

        return exc_type is None

    def get_console(self) -> Console:
        if self.disable_terminal_log:
            return Console(file=open(self.log_file, "w"))
        return Console(record=True)

    def get_logfile(self) -> Path:
        log_file = self.save_dir / f"{self.bvid}.log"
        log_file.touch(exist_ok=True)
        return log_file

    @cached_property
    def play_info(self) -> models.PlayInfoData:
        return self.get_play_info()

    @cached_property
    def filepath(self) -> Path:
        _filename = self._filename or self.get_title()

        # Replace invalid characters with _
        _filename = RGX_CHECK_FILENAME.sub("_", _filename)

        _filepath = self.save_dir / _filename

        if _filepath.suffix not in (".mp4", ".mkv", ".avi"):
            _filepath = _filepath.with_suffix(self.default_video_suffix)

        return _filepath

    @cached_property
    def html_content(self) -> str:
        headers = {**user_agent_headers()}
        cookies = {"SESSDATA": self.sess_data} if self.sess_data is not None else {}
        self.log(
            f"[{self.downloader_name}] Requesting {self.api}{f' with cookies {cookies}' if cookies else ''}"
        )
        response = requests.get(self.api, headers=headers, cookies=cookies)
        response.raise_for_status()
        html_content = response.text
        return html_content

    @cached_property
    def videos(self) -> Videos:
        """Get all videos sorted by quality in descending order"""
        return sorted(
            self.play_info.dash.video, key=attrgetter("quality"), reverse=True
        )

    @cached_property
    def video_to_download(self) -> models.PlayVideo:
        """Get the video to download according to quality and codecs"""
        return self.choose_codecs(self.filter_quality(self.videos))

    @cached_property
    def downloader_name(self) -> str:
        return self.__str__()

    def log(self, msg: str, level: int = logging.DEBUG, traceback: Any = None):
        if self.console is None:
            logger.log(level, msg, exc_info=traceback is not None)
        else:
            if level >= settings.LOG_LEVEL:
                self.console.log(f"[{logging.getLevelName(level)}] {msg}")
                if traceback:
                    self.console.log(f"Traceback: \n{''.join(format_tb(traceback))}")

    def get_play_info(self) -> models.PlayInfoData:
        playinfo = RGX_FIND_PLAYINFO.search(self.html_content)
        if playinfo is None:
            raise ValueError(f"Playinfo not found from {self.html_content}")
        playinfo = playinfo.group(1)  # type: ignore
        return models.PlayInfoResponse(**json.loads(playinfo)).data  # type: ignore

    def get_title(self) -> str:
        soup = BeautifulSoup(self.html_content, "html.parser")
        title_tag = soup.find("title")
        if title_tag is None:
            raise ValueError(f"Title not found from {self.html_content}")
        title = title_tag.text
        self.log(f"[{self.downloader_name}] Title: {title}", level=logging.INFO)
        return title

    def clean(self):
        if self.remove_temp_dir:
            # move file to the parent directory and remove save dir
            rm_tree(self.temp_dir)
            self.log(
                f"[{self.downloader_name}] Remove temporary directory",
                level=logging.INFO,
            )

        self.log(
            f"[{self.downloader_name}] Finished. File save to: {self.filepath}",
            level=logging.INFO,
        )

    def process(self, video_path: VideoPath, audio_path: AudioPath):
        """Process video and audio with ffmpeg

        Args:
            video_path (Path): video path
            audio_path (Path): audio path
        """
        # process with ffmpeg
        self.log(
            f"[{self.downloader_name}] Merging audio and video files to {self.filepath}",
            level=logging.INFO,
        )

        cmd = [
            self.ffmpeg,
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            str(self.filepath),
            "-y",
        ]

        if self.ffmpeg_params:
            cmd.extend(self.ffmpeg_params)

        self.log(
            f"[{self.downloader_name}] Process {video_path} with FFMPEG: {' '.join(cmd)}",
            level=logging.DEBUG,
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
        )

        if result.returncode:
            raise ValueError(
                f"{cmd} failed with code {result.returncode}."
                f"Detail: {result.stderr.decode().strip()}"
            )

    def filter_quality(self, videos: Videos) -> Videos:
        if self.quality is HIGHEST_QUALITY:
            videos = videos[:1]
        else:
            videos = list(filter(lambda video: video.quality == self.quality, videos))
        if not videos:
            raise ValueError(
                f"No video with quality {self.quality} found, available qualities: {self.play_info.quality_map.items()}"
            )
        return videos

    def choose_codecs(self, videos: Videos) -> models.PlayVideo:
        if self.codecs is None:
            return videos[0]
        for video in videos:
            if re.search(self.codecs, video.codecs):
                return video

        codecs = ", ".join([video.codecs for video in videos])
        raise ValueError(
            f"No video with codec {self.codecs} matched, available codecs: {codecs}"
        )

    def run_task_directly(self, task: DownloadMediaTask):
        iterator = task.start()
        total_size: int = next(iterator)  # type: ignore
        for chunk in iterator:
            self.log(
                f"[{self.downloader_name}] {task}: {len(chunk) / total_size * 100:.2f}%",  # type: ignore
                level=logging.INFO,
            )

    def add_video_task(self):
        process_video_task = DownloadVideoTask(
            self.video_to_download,
            self.temp_dir
            / f"video-{self.video_to_download.quality}-{self.video_to_download.codecs}.mp4",
            self.play_info.quality_map,
        )
        self.downloading_tasks.append(process_video_task)

        self.video_path = process_video_task.save_dir

    def add_audio_task(self):
        for audio in self.play_info.dash.audio:
            self.downloading_tasks.append(
                DownloadAudioTask(
                    audio,
                    self.temp_dir / f"audio-{audio.audio_id}.mp4",
                )
            )

    def prepare_tasks(self):
        self.tasks.append(LinerTask(self.add_video_task, name="Search video links"))
        self.tasks.append(LinerTask(self.add_audio_task, name="Search audio links"))
        if self.from_cli:
            self.tasks.append(
                LinerTask(self.download_with_progress, name="Download video and audio")
            )
        else:
            self.tasks.append(
                LinerTask(self.download_directly, name="Download video and audio")
            )
        self.tasks.append(LinerTask(self.concat_audio, name="Merge audio files"))

        if self.process_func is not None and callable(self.process_func):
            self.tasks.append(
                LinerTask(
                    self.process_func,
                    name="Merge video and audio files",
                    delay_args=lambda: (self.video_path, self.audio_temp_path),
                )
            )
        else:
            self.tasks.append(
                LinerTask(
                    self.process,
                    name="Merge video and audio files",
                    delay_args=lambda: (self.video_path, self.audio_temp_path),
                )
            )

        self.tasks.append(LinerTask(self.clean, name="Clean up"))

    def run_tasks(self):
        total_tasks = len(self.tasks)
        for task_idx, task in enumerate(self.tasks):
            self.log(
                f"[{self.downloader_name}] [{task_idx + 1}/{total_tasks}]: {task.task_name}",
                level=logging.INFO,
            )
            task.start()

    def iter_tasks(self) -> Generator[LinerTask, None, None]:
        for task in self.tasks:
            task.start()
            yield task

    def download(
        self, yield_tasks: bool = False
    ) -> Optional[Generator[LinerTask, None, None]]:
        self.prepare_tasks()

        return self.run_tasks() if not yield_tasks else self.iter_tasks()

    @staticmethod
    def _update_progress(task: DownloadMediaTask, task_id: TaskID, progress: Progress):
        progress.start_task(task_id)
        while not task.finished:
            iterator = task.start()
            total_size = next(iterator)
            for chunk in iterator:
                progress.update(task_id, total=total_size, advance=len(chunk))  # type: ignore

    def download_with_progress(self):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        ) as progress:
            tasks_map = {
                task: progress.add_task(str(task), start=False)
                for task in self.downloading_tasks
            }
            with futures.ThreadPoolExecutor() as executor:
                tasks = {
                    executor.submit(
                        self._update_progress, task, task_id, progress
                    ): task
                    for task, task_id in tasks_map.items()
                }

                self.handle_tasks(tasks)

    def download_directly(self):
        with futures.ThreadPoolExecutor() as executor:
            tasks = {
                executor.submit(self.run_task_directly, task): task
                for task in self.downloading_tasks
            }

            self.handle_tasks(tasks)

    def concat_audio(self):
        with open(self.audio_temp_path, "wb") as f:
            for audio_task in filter(
                lambda t: isinstance(t, DownloadAudioTask), self.downloading_tasks
            ):
                f.write(audio_task.save_dir.read_bytes())

        self.log(
            f"[{self.downloader_name}] Audio file saved to {self.audio_temp_path}",
            level=logging.INFO,
        )

    def handle_tasks(self, tasks: dict[futures.Future, DownloadMediaTask]):
        for f in futures.as_completed(tasks):
            task = tasks[f]
            try:
                f.result()
            except Exception as e:
                self.log(
                    f"[{self.downloader_name}] Error occurred when downloading {task}: {e}",
                    level=logging.ERROR,
                )

                if self.exit_on_error:
                    exit(1)

    def __str__(self):
        return f"<Downloader {self.bvid}>"


class MultiThreadDownloader:
    rgx_split_bvid_list = re.compile(r"[\s,\t\n]+")

    def __init__(
        self,
        bvid_list: BvidList,
        save_dir: str | Path,
        remove_temp_dir: bool = True,
        sess_data: str | None = None,
        quality: int = HIGHEST_QUALITY,
        codecs: str | None = None,
        ffmpeg_params: list[str] | None = None,
        process_func: Callable[[VideoPath, AudioPath], None] | None = None,
        max_workers: int = settings.CPU_COUNT,
        from_cli: bool = True,
        exit_on_error: bool = False,
        ffmpeg: str | None = None,
    ):
        self.bvid_list = list(set(sorted(self.read_bvid_list(bvid_list))))
        self.save_dir = Path(save_dir) if not isinstance(save_dir, Path) else save_dir
        self.ffmpeg = ffmpeg or get_ffmpeg_executable()
        self.downloaders = [
            Downloader(
                bvid,
                self.save_dir / bvid,
                remove_temp_dir=remove_temp_dir,
                sess_data=sess_data,
                quality=quality,
                codecs=codecs,
                ffmpeg_params=ffmpeg_params,
                process_func=process_func,
                from_cli=False,
                ffmpeg=self.ffmpeg,
                disable_terminal_log=True,
                exit_on_error=True,
            )
            for bvid in self.bvid_list
        ]

        self.max_workers = max_workers
        self.from_cli = from_cli
        self.exit_on_error = exit_on_error
        self.log_dir = self.save_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)

        self.success_count = 0
        self.failed_count = 0

    def read_bvid_list(self, bvid_list: BvidList) -> list[str]:
        match bvid_list:
            case str():
                return self.rgx_split_bvid_list.split(bvid_list.strip())
            case Path():
                return self.read_bvid_list(bvid_list.read_text())
            case BinaryIO():
                return self.read_bvid_list(bvid_list.read().decode())
            case list():
                return list(
                    chain.from_iterable(
                        filter(
                            lambda _bvid: _bvid,
                            map(
                                self.read_bvid_list,
                                bvid_list,
                            ),
                        )
                    )
                )
            case _:
                raise TypeError(
                    f"bvid_list should be str, Path, BinaryIO or list, got {type(bvid_list)}"
                )

    def download_directly(self):
        with futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            tasks = {
                executor.submit(downloader.download): downloader
                for downloader in self.downloaders
            }

            self.handle_tasks(tasks)

    def _worker_update_progress(
        self,
        downloader: Downloader,
        progress: Progress,
        overall_task_id: TaskID,
    ):
        downloader.prepare_tasks()
        total = len(downloader.tasks)
        task_id = progress.add_task(
            f"[green] {downloader.downloader_name}: ",
            event="Preparing",
            start=True,
            total=total,
        )

        try:
            with downloader:
                for idx, task in enumerate(downloader.iter_tasks()):
                    progress.update(
                        task_id,
                        completed=idx + 1,
                        total=total,
                        event=f"[green bold][{idx + 1}/{total}] {task.task_name}",
                    )
        except KeyboardInterrupt:
            exit(1)

        except:  # noqa: E722
            progress.update(task_id=task_id, event="[red bold] Failed!")
            self.failed_count += 1
        else:
            progress.update(overall_task_id, advance=1, event="")
            progress.update(task_id, event="[green bold] Finished!")
            self.success_count += 1
        finally:
            downloader.log_file = downloader.log_file.rename(
                self.log_dir / downloader.log_file.name
            )
            if downloader.state is DownloadState.FAILED:
                logger.error(
                    f"[{downloader.downloader_name}] Failed, please check the log file: {downloader.log_file} for detail",
                )
            else:
                downloader.filepath = downloader.filepath.rename(
                    self.save_dir / downloader.filepath.name
                )
                logger.info(
                    f"[{downloader.downloader_name}] Success, file saved to: {downloader.filepath}"
                )
            rm_tree(downloader.save_dir)
            progress.remove_task(task_id)
            progress.update(
                overall_task_id,
                event=f"[bold green]{self.success_count} succeeded {self.failed_count} failed",
            )

    def download_with_progress(self):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TextColumn("{task.fields[event]}"),
            refresh_per_second=2,
        ) as progress:
            overall_task = progress.add_task(
                "[green] All jobs: ", total=len(self.downloaders), event=""
            )

            with futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                progress.start_task(overall_task)
                tasks = {
                    executor.submit(
                        self._worker_update_progress,
                        downloader,
                        progress,
                        overall_task,
                    ): downloader
                    for downloader in self.downloaders
                }

                self.handle_tasks(tasks)

        logger.info(f"All jobs finished, files saved to: {self.save_dir}")

    def download(self):
        if self.from_cli:
            self.download_with_progress()
        else:
            self.download_directly()

    def handle_tasks(
        self,
        tasks: dict[futures.Future, Downloader],
    ):
        for f in futures.as_completed(tasks):
            downloader = tasks[f]
            try:
                f.result()
            except Exception as e:
                logger.error(
                    f"Error occurred for {downloader}: {e}",
                    exc_info=True,
                )

                if self.exit_on_error:
                    exit(1)
