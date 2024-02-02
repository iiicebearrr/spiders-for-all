import json
import logging
import re
import subprocess
import typing as t
from functools import cached_property
from operator import attrgetter
from pathlib import Path
from typing import BinaryIO, Callable, TypeAlias

from bs4 import BeautifulSoup

from spiders_for_all.core import downloader as base_downloader
from spiders_for_all.core import media as base_media
from spiders_for_all.spiders.bilibili import const, models, patterns
from spiders_for_all.utils.helper import read_ids_to_list
from spiders_for_all.utils.logger import get_logger

logger = get_logger("bilibili")

Media: TypeAlias = models.PlayVideo | models.PlayAudio
Medias: TypeAlias = list[Media]
Videos: TypeAlias = list[models.PlayVideo]
Audios: TypeAlias = list[models.PlayAudio]
VideoPath: TypeAlias = Path
AudioPath: TypeAlias = Path
BvidList: TypeAlias = str | list[str] | Path | list[Path] | BinaryIO


class BilibiliDownloader(base_downloader.BaseDownloader):
    origin: str = const.MAIN_PAGE
    api: str = const.API_GET_VIDEO_INFO

    def __init__(
        self,
        bvid: str,
        save_dir: Path | str,
        sess_data: str | None = None,
        quality: int = const.HIGHEST_QUALITY,
        codecs: str | None = None,
        ffmpeg_params: list[str] | None = None,
        process_func: Callable[[VideoPath, AudioPath], None] | None = None,
        temp_audio_name: str = "audio-temp.wav",
        **kwargs: t.Unpack[base_downloader.DownloaderKwargs],
    ) -> None:
        self.bvid = bvid
        self.api = self.api.format(bvid=bvid)
        super().__init__(
            save_dir,
            media=base_media.Mp4(base_url=self.api),
            **kwargs,
        )

        self.sess_data = sess_data
        self.quality = quality
        self.codecs = codecs
        self.ffmpeg_params = ffmpeg_params
        self.process_func = process_func

        # audio files to be merged
        self.audios: list[AudioPath] = []

        # Merged audio file
        self.temp_audio_file = self.temp_dir / temp_audio_name

        self.temp_video_file: Path | None = None

        if self.sess_data:
            self.client.set_cookies("SESSDATA", self.sess_data)

    def get_output_filename(self) -> str:
        return self.title

    @cached_property
    def play_info(self) -> models.PlayInfoData:
        # TODO: Let get_play_info be a task
        return self.get_play_info()

    @cached_property
    def html_content(self) -> str:
        with self.client:
            return self.client.get(self.api).text

    def get_play_info(self) -> models.PlayInfoData:
        playinfo = patterns.RGX_FIND_PLAYINFO.search(self.html_content)
        if playinfo is None:
            raise ValueError(f"Playinfo not found from {self.html_content}")
        playinfo = playinfo.group(1)  # type: ignore
        return models.PlayInfoResponse(**json.loads(playinfo)).data  # type: ignore

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
    def title(self) -> str:
        soup = BeautifulSoup(self.html_content, "html.parser")
        title_tag = soup.find("title")
        if title_tag is None:
            raise ValueError(f"Title not found from {self.html_content}")
        title = title_tag.text
        self.log(f"Title: {title}")
        return title

    def get_log_filename(self) -> str:
        return super().get_log_filename() + f"-{self.bvid}"

    def filter_quality(self, videos: Videos) -> Videos:
        if self.quality is const.HIGHEST_QUALITY:
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

    def process(self, video_path: VideoPath, audio_path: AudioPath):
        """Process video and audio with ffmpeg

        Args:
            video_path (Path): video path
            audio_path (Path): audio path
        """
        # process with ffmpeg
        self.log(
            f"Merging audio and video files to {self.output_file}",
        )

        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            str(self.output_file),
            "-y",
        ]

        if self.ffmpeg_params:
            cmd.extend(self.ffmpeg_params)

        self.log(
            f"Process {video_path} with FFMPEG: {' '.join(cmd)}",
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

    def get_download_client(self):
        client = self.client.new()
        client.logger = logger
        client.headers.update(
            {
                "Referer": self.origin,
            }
        )

        return client

    def add_video_download_task(self):
        client = self.get_download_client()

        # test connection to video url and backup url

        task = base_downloader.DownloadTask(
            base_media.Mp4(
                base_url=self.video_to_download.base_url,
                backup_url=self.video_to_download.backup_url,
                name=self.play_info.quality_map[self.video_to_download.quality],
            ),
            self.temp_dir
            / f"video-{self.video_to_download.quality}-{self.video_to_download.codecs}.mp4",
            logger=logger,
            client=client,
        )

        self.download_tasks.append(task)

        self.temp_video_file = task.output_file

    def add_audio_download_task(self):
        audio: models.PlayAudio = self.play_info.dash.audio[0]
        client = self.get_download_client()
        task = base_downloader.DownloadTask(
            base_media.Mp3(base_url=audio.base_url, backup_url=audio.backup_url),
            self.temp_dir / f"audio-{audio.audio_id}.mp4",
            logger=logger,
            client=client,
        )
        self.download_tasks.append(task)
        self.temp_audio_file = task.output_file

    def prepare_tasks(self):
        self.tasks.append(
            base_downloader.LinerTask(
                self.add_video_download_task, name="Search video links"
            )
        )
        self.tasks.append(
            base_downloader.LinerTask(
                self.add_audio_download_task, name="Search audio links"
            )
        )
        if self.from_cli:
            self.tasks.append(
                base_downloader.LinerTask(
                    self.run_download_tasks_with_progress,
                    name="Download video and audio",
                )
            )
        else:
            self.tasks.append(
                base_downloader.LinerTask(
                    self.run_download_tasks_directly, name="Download video and audio"
                )
            )

        if self.process_func is not None and callable(self.process_func):
            self.tasks.append(
                base_downloader.LinerTask(
                    self.process_func,
                    name="Merge video and audio files",
                    delay_args=lambda: (self.temp_video_file, self.temp_audio_file),
                )
            )
        else:
            self.tasks.append(
                base_downloader.LinerTask(
                    self.process,
                    name="Merge video and audio files",
                    delay_args=lambda: (self.temp_video_file, self.temp_audio_file),
                )
            )

        self.tasks.append(base_downloader.LinerTask(self.clean, name="Clean up"))
        super().prepare_tasks()

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} {self.bvid}>"


class BilibiliBatchDownloader(base_downloader.BaseBatchDownloader):
    rgx_split_bvid_list = re.compile(r"[\s,\t\n]+")

    def __init__(
        self,
        bvid_list: BvidList,
        save_dir: str | Path,
        sess_data: str | None = None,
        quality: int = const.HIGHEST_QUALITY,
        codecs: str | None = None,
        ffmpeg_params: list[str] | None = None,
        process_func: Callable[[VideoPath, AudioPath], None] | None = None,
        **kwargs: t.Unpack[base_downloader.MultipleDownloaderKwargs],
    ):
        if "logger" not in kwargs:
            kwargs["logger"] = logger
        super().__init__(save_dir, **kwargs)

        self.bvid_list = list(set(sorted(read_ids_to_list(bvid_list))))
        self.sess_data = sess_data
        self.quality = quality
        self.codecs = codecs
        self.ffmpeg_params = ffmpeg_params
        self.process_func = process_func

    def get_downloaders(self) -> list[BilibiliDownloader]:
        return [
            BilibiliDownloader(
                bvid=bvid,
                save_dir=self.get_downloader_save_dir(bvid),
                sess_data=self.sess_data,
                quality=self.quality,
                codecs=self.codecs,
                ffmpeg_params=self.ffmpeg_params,
                process_func=self.process_func,
                from_cli=False,
                disable_terminal_log=True,
            )
            for bvid in self.bvid_list
        ]
