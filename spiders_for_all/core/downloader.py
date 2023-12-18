import logging
import typing as t
from concurrent import futures
from datetime import datetime
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from traceback import format_exc

import requests
from rich import progress as p
from rich.console import Console

from spiders_for_all import const
from spiders_for_all.conf import settings
from spiders_for_all.core import media
from spiders_for_all.utils import helper
from spiders_for_all.utils.decorator import retry
from spiders_for_all.utils.logger import default_logger as logger

Size = t.NewType("Size", int)

NOT_SET = object()


def get_filename_by_dt() -> str:
    return datetime.now().strftime("%Y%m%d-%H_%M_%S")


class DownloaderState(Enum):
    NOT_STARTED = auto()
    STARTED = auto()
    FINISHED = auto()
    FAILED = auto()
    PAUSED = auto()
    CANCELLED = auto()


class Task(t.Protocol):
    def start(self, *args, **kwargs):
        pass


class Downloader(t.Protocol):
    def download(*args, **kwargs):
        pass


class BaseTask:
    def __init__(self, *args, **kwargs) -> None:
        self._finished = False
        super().__init__(*args, **kwargs)

    @property
    def finished(self):
        return self._finished

    @finished.setter
    def finished(self, value):
        self._finished = bool(value)

    def start(self):
        raise NotImplementedError()


class LinerTask(BaseTask):
    def __init__(
        self,
        fn: t.Callable,
        name: str | None = None,
        args: tuple | None = None,
        kwargs: dict | None = None,
        delay_args: t.Optional[t.Callable] = None,
        delay_kwargs: t.Optional[t.Callable] = None,
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


class DownloadTask(BaseTask):
    def __init__(
        self,
        url: str,
        save_dir: Path | str,
        media: media.Media,
        *args,
        chunk_size: int = const.CHUNK_SIZE,
        request_method: str = "GET",
        max_retries: int = settings.REQUEST_MAX_RETRIES,
        retry_interval: int = settings.REQUEST_RETRY_INTERVAL,
        retry_step: int = settings.REQUEST_RETRY_STEP,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.url = url
        self.save_dir = Path(save_dir) if isinstance(save_dir, str) else save_dir
        self.chunk_size = chunk_size
        self._total_size: int | None = None
        self.media = media
        self.request_method = request_method
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.retry_step = retry_step

    def __str__(self) -> str:
        return f"<{self.media.media_type}> {self.media.name or self.url}"

    def get_request_args(self) -> dict:
        return {
            "headers": helper.user_agent_headers(),
        }

    def request(self) -> t.Generator[Size | bytes, None, None]:
        @retry(
            max_retries=self.max_retries,
            interval=self.retry_interval,
            step=self.retry_step,
        )
        def _request():
            with requests.request(
                self.request_method, self.url, stream=True, **self.get_request_args()
            ) as r:
                r.raise_for_status()
                if self._total_size is None:
                    self._total_size = int(r.headers.get("Content-Length", 0))
                    yield self._total_size
                for chunk in r.iter_content(chunk_size=self.chunk_size):
                    yield chunk

        yield from _request()

    def start(self) -> t.Generator[Size | bytes, None, None]:
        with open(self.save_dir, "wb") as f:
            generator = self.request()
            total_size = next(generator)
            yield total_size
            for chunk in generator:
                f.write(chunk)  # type: ignore
                yield chunk

        self._finished = True


class BaseDownloader:
    def __init__(
        self,
        save_dir: Path | str,
        media: media.Media,
        *args,
        filename: str | None = None,
        disable_terminal_log: bool = False,
        from_cli: bool = True,
        request_method: str = "GET",
        chunk_size: int = const.CHUNK_SIZE,
        max_retries: int = settings.REQUEST_MAX_RETRIES,
        retry_interval: int = settings.REQUEST_RETRY_INTERVAL,
        retry_step: int = settings.REQUEST_RETRY_STEP,
        remove_temp_dir: bool = True,
        exit_on_download_failed: bool = True,
        **kwargs,
    ) -> None:
        self.save_dir = Path(save_dir) if isinstance(save_dir, str) else save_dir
        self.temp_dir = self.save_dir / ".temp"
        self.media = media
        self.filename = filename
        self.disable_terminal_log = disable_terminal_log
        self.from_cli = from_cli
        self.request_method = request_method
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.retry_step = retry_step
        self.remove_temp_dir = remove_temp_dir
        self.exit_on_download_failed = exit_on_download_failed

        self.state = DownloaderState.NOT_STARTED
        self.exc_info: tuple[Exception | object, str | object] = (NOT_SET, NOT_SET)
        self.tasks: list[LinerTask] = []
        self.download_tasks: list[DownloadTask] = []

        self.console: Console = self.get_console()
        self.log_file = self.create_log_file()

        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        super().__init__(*args, **kwargs)

    @cached_property
    def name(self) -> str:
        return self.__str__()

    def get_console(self) -> Console:
        if self.disable_terminal_log:
            return Console(file=open(self.log_file, "w"))
        return Console(record=True)

    def create_log_file(self) -> Path:
        log_file = self.save_dir / f"{get_filename_by_dt()}.log"
        log_file.touch(exist_ok=True)
        return log_file

    def get_output_filename(self) -> str:
        return get_filename_by_dt()

    @cached_property
    def output_file(self) -> Path:
        filename = self.filename or self.get_output_filename()

        filename = helper.correct_filename(filename)

        filepath = self.save_dir / filename

        if filepath.suffix != self.media.suffix:
            filepath = filepath.with_suffix(self.media.suffix)

        return filepath

    def log(
        self,
        msg: str,
        level: int = logging.INFO,
        exc_info: bool = False,
        exc_detail: str | None = None,
        log_downloader_name: bool = True,
    ):
        if level >= settings.LOG_LEVEL:
            self.console.log(
                f"{self.name if log_downloader_name else ''}[{logging.getLevelName(level)}] {msg}"
            )
            if exc_info:
                self.console.log(
                    f"{self.name + '\n' if log_downloader_name else ''}Traceback: \n{format_exc() if exc_detail is None else exc_detail}"
                )

    def clean(self):
        if self.remove_temp_dir:
            helper.rm_tree(self.temp_dir)
            self.log(
                f"Remove temp dir {self.temp_dir}",
            )

    def prepare_tasks(self):
        pass

    def run_tasks(self):
        total_tasks = len(self.tasks)
        for task_idx, task in enumerate(self.tasks):
            self.log(
                f"[{task_idx + 1}/{total_tasks}]: {task.task_name}",
            )
            task.start()

    def iter_tasks(self) -> t.Generator[LinerTask, None, None]:
        for task in self.tasks:
            task.start()
            yield task

    def download(
        self, yield_tasks: bool = False
    ) -> t.Optional[t.Generator[LinerTask, None, None]]:
        """Entry point of the downloader

        Args:
            yield_tasks (bool, optional): Run the tasks directly of yield it for progress bar. Defaults to False.

        Returns:
            t.Optional[t.Generator[LinerTask, None, None]]: if yield_tasks is True, return a generator of tasks

        Yields:
            Iterator[t.Optional[t.Generator[LinerTask, None, None]]]: A generator of tasks
        """

        self.state = DownloaderState.STARTED

        try:
            self.prepare_tasks()

            if not yield_tasks:
                self.run_tasks()
            else:
                yield from self.iter_tasks()

        except KeyboardInterrupt:
            raise

        except Exception as e:
            self.state = DownloaderState.FAILED
            exc = format_exc()
            self.exc_info = (e, exc)
            self.log(
                f"Error: {e.args[0]}",
                level=logging.ERROR,
                exc_info=True,
                exc_detail=exc,
            )
        else:
            self.state = DownloaderState.FINISHED
            self.log(
                "Finished successfully",
            )
        finally:
            if self.console.record:
                self.console.save_text(str(self.log_file))

    def run_download_task(self, task: DownloadTask):
        generator = task.start()
        total_size = next(generator)
        for chunk in generator:
            self.log(
                f"{task}: {len(chunk) / total_size * 100:.2f}%",  # type: ignore
                level=logging.INFO,
            )

    def run_download_tasks_directly(self):
        with futures.ThreadPoolExecutor() as executor:
            fs = {
                executor.submit(self.run_download_task, task): task
                for task in self.download_tasks
            }
            self.handle_futures(fs)

    @staticmethod
    def _update_progress(task: DownloadTask, task_id: p.TaskID, progress: p.Progress):
        progress.start_task(task_id)
        while not task.finished:
            iterator = task.start()
            total_size = next(iterator)
            for chunk in iterator:
                progress.update(task_id, total=total_size, advance=len(chunk))  # type: ignore

    def run_download_tasks_with_progress(self):
        with p.Progress(
            p.SpinnerColumn(),
            p.TextColumn("[progress.description]{task.description}"),
            p.BarColumn(),
            p.TaskProgressColumn(),
            p.TimeRemainingColumn(),
            p.DownloadColumn(),
            p.TransferSpeedColumn(),
        ) as progress:
            tasks_map = {
                task: progress.add_task(str(task), start=False)
                for task in self.download_tasks
            }

            with futures.ThreadPoolExecutor() as executor:
                fs = {
                    executor.submit(
                        self._update_progress, task, task_id, progress
                    ): task
                    for task, task_id in tasks_map.items()
                }

                self.handle_futures(fs)

    def handle_futures(self, fs: dict[futures.Future, DownloadTask]):
        for f in futures.as_completed(fs):
            download_task = fs[f]

            try:
                f.result()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.log(
                    f"Error for task {download_task}: {e.args[0]}",
                    level=logging.ERROR,
                    exc_info=True,
                    exc_detail=format_exc(),
                )
                if self.exit_on_download_failed:
                    exit(1)

    def __str__(self) -> str:
        return f"<Downloader {self.__class__.name} {self.state}>"


class BaseBatchDownloader:
    def __init__(
        self,
        downloaders: list[BaseDownloader],
        save_dir: Path | str,
        *args,
        from_cli: bool = True,
        request_method: str = "GET",
        chunk_size: int = const.CHUNK_SIZE,
        max_retries: int = settings.REQUEST_MAX_RETRIES,
        retry_interval: int = settings.REQUEST_RETRY_INTERVAL,
        retry_step: int = settings.REQUEST_RETRY_STEP,
        remove_downloader_save_dir: bool = True,
        exit_on_download_failed: bool = True,
        max_workers: int = settings.CPU_COUNT,
        logger: logging.Logger = logger,
        **kwargs,
    ):
        self.downloaders = downloaders
        self.save_dir = Path(save_dir) if isinstance(save_dir, str) else save_dir
        self.from_cli = from_cli
        self.max_workers = max_workers
        self.exit_on_download_failed = exit_on_download_failed
        self.logger = logger
        self.remove_downloader_save_dir = remove_downloader_save_dir
        self.log_dir = self.save_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.success_count = 0
        self.failed_count = 0

        super().__init__(*args, **kwargs)

    def get_downloader_save_dir(self, idx: int) -> Path:
        return self.save_dir / f"downloader-{idx}"

    def run_downloaders_directly(self):
        with futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            self.handle_downloader_futures(
                {
                    executor.submit(self.run_downloader, downloader): downloader
                    for downloader in self.downloaders
                }
            )

    def run_downloaders_with_progress(self):
        with p.Progress(
            p.SpinnerColumn(),
            p.TextColumn("[progress.description]{task.description}"),
            p.BarColumn(),
            p.MofNCompleteColumn(),
            p.TaskProgressColumn(),
            p.TimeElapsedColumn(),
            p.TextColumn("{tasks.fields[event]}"),
            refresh_per_second=2,
        ) as progress:
            overall_task = progress.add_task(
                "[green] All jobs: ", total=len(self.downloaders), event=""
            )

            with futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                progress.start_task(overall_task)
                self.handle_downloader_futures(
                    {
                        executor.submit(
                            self.update_downloader_progress,
                            downloader,
                            progress,
                            overall_task,
                        ): downloader
                        for downloader in self.downloaders
                    }
                )

    def run_downloader(self, downloader: BaseDownloader):
        downloader.download()
        self.clean_downloader_save_dir(downloader)

    def update_downloader_progress(
        self,
        downloader: BaseDownloader,
        progress: p.Progress,
        overall_task_id: p.TaskID,
    ):
        downloader.prepare_tasks()
        total = len(downloader.tasks)
        task_id = progress.add_task(
            f"[green] {downloader.name}: ",
            event="Preparing",
            start=True,
            total=total,
        )

        try:
            for idx, task in enumerate(downloader.iter_tasks()):
                progress.update(
                    task_id,
                    completed=idx + 1,
                    total=total,
                    event=f"[green bold][{idx + 1}/{total}] {task.task_name}",
                )
        except KeyboardInterrupt:
            raise

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
            if downloader.state is DownloaderState.FAILED:
                logger.error(
                    f"<{downloader.name}> Failed, please check the log file: {downloader.log_file} for detail",
                )
            else:
                downloader.output_file = downloader.output_file.rename(
                    self.save_dir / downloader.output_file.name
                )
                logger.info(
                    f"<{downloader.name}> Success, file saved to: {downloader.output_file}"
                )
            self.clean_downloader_save_dir(downloader)
            progress.remove_task(task_id)
            progress.update(
                overall_task_id,
                event=f"[bold green]{self.success_count} succeeded {self.failed_count} failed",
            )

    def handle_downloader_futures(self, fs: dict[futures.Future, BaseDownloader]):
        for f in futures.as_completed(fs):
            downloader = fs[f]
            try:
                f.result()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.logger.error(
                    f"Error for downloader {downloader}: {e.args[0]}",
                    exc_info=True,
                )

                if self.exit_on_download_failed:
                    exit(1)

    def clean_downloader_save_dir(self, downloader: BaseDownloader):
        if self.remove_downloader_save_dir:
            helper.rm_tree(downloader.save_dir)

    def download(self):
        if self.from_cli:
            self.run_downloaders_with_progress()
        else:
            self.run_downloaders_directly()
