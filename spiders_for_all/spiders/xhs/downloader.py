import shutil
import typing as t
from functools import cached_property
from pathlib import Path

from spiders_for_all.core.downloader import (
    BaseBatchDownloader,
    BaseDownloader,
    DownloaderKwargs,
    DownloadTask,
    LinerTask,
    MultipleDownloaderKwargs,
)
from spiders_for_all.core.media import WEBP, Mp4, Text
from spiders_for_all.spiders.xhs import const, models, patterns
from spiders_for_all.utils import helper
from spiders_for_all.utils.logger import get_logger

logger = get_logger("xhs")


class Note(Text):
    description = "小红书笔记"


class XhsNoteDownloader(BaseDownloader):
    api: str = const.API_NOTE_PAGE

    def __init__(
        self,
        note_id: str,
        save_dir: Path | str,
        **kwargs: t.Unpack[DownloaderKwargs],
    ) -> None:
        self.note_id = note_id
        super().__init__(
            save_dir,
            media=Note(base_url=self.api.format(note_id=note_id)),
            **kwargs,
        )
        self.images: list[WEBP] = []
        self.videos: list[Mp4] = []

    @cached_property
    def html_content(self) -> models.XhsNote:
        return self.get_html_content()

    def get_html_content(self) -> models.XhsNote:  # type: ignore
        with self.client:
            resp = self.client.get(self.media.url)
            initial_data = patterns.RGX_FIND_INITIAL_INFO.search(resp.text)
            if not initial_data:
                raise ValueError("Initial data not found.")
            initial_data = initial_data.group(1)  # type: ignore
            detail = helper.javascript_to_dict(initial_data)

            note_detail_maps = detail.get("note", {}).get("noteDetailMap", {}).values()

            for note_detail in note_detail_maps:
                note = models.XhsNote(**note_detail["note"])
                for image in note.image_list:
                    self.images.append(WEBP(base_url=image.url_default))

                if note.video:
                    for v in note.video.media.iter_video_item():
                        self.videos.append(
                            Mp4(
                                base_url=v.master_url,
                                name=f"{v.quality_type}-{v.video_codec}",
                            )
                        )
                return note

    def get_output_filename(self) -> str:
        return self.html_content.title

    def get_log_filename(self) -> str:
        return super().get_log_filename() + f"-{self.note_id}"

    def add_image_download_task(self):
        if not self.images:
            return
        image_dir = self.save_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        for idx, img in enumerate(self.images):
            self.download_tasks.append(
                DownloadTask(
                    media=img,
                    output_file=image_dir / f"img-{idx}{img.suffix}",
                    logger=self.console,
                )
            )

    def add_video_download_task(self):
        if not self.videos:
            return

        video_dir = self.save_dir / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)

        for idx, video in enumerate(self.videos):
            self.download_tasks.append(
                DownloadTask(
                    media=video,
                    output_file=video_dir / f"video-{idx}-{video.name}{video.suffix}",
                    logger=self.console,
                )
            )

    def download_note_content(self):
        with open(self.output_file, "w") as f:
            f.write(self.html_content.desc or "")

    def prepare_tasks(self):
        self.tasks.append(
            LinerTask(fn=lambda: self.html_content, name="Get html content")
        )

        self.tasks.append(
            LinerTask(
                fn=self.download_note_content,
                name="Download note content",
            )
        )

        self.tasks.append(
            LinerTask(fn=self.add_image_download_task, name="Add image download tasks")
        )

        self.tasks.append(
            LinerTask(fn=self.add_video_download_task, name="Add video download tasks")
        )

        if self.from_cli:
            self.tasks.append(
                LinerTask(
                    fn=self.run_download_tasks_with_progress,
                    name="Download note content",
                )
            )
        else:
            self.tasks.append(
                LinerTask(
                    fn=self.run_download_tasks_directly,
                    name="Download note content",
                )
            )

        self.tasks.append(LinerTask(fn=self.clean, name="Clean up temporary files"))

        super().prepare_tasks()

    def after_download(self):
        dst = self.save_dir.parent / helper.correct_filename(self.html_content.title)

        # FIXME: Sometime the dst is already exists
        if not dst.exists():
            shutil.move(self.save_dir, dst)

        self.save_dir = dst


class XhsNoteBatchDownloader(BaseBatchDownloader):
    def __init__(
        self,
        note_ids: helper.Ids,
        save_dir: Path | str,
        **kwargs: t.Unpack[MultipleDownloaderKwargs],
    ):
        if "logger" not in kwargs:
            kwargs["logger"] = logger

        # Videos and images are saved to the downloader's save_dir
        kwargs["remove_downloader_save_dir"] = False
        kwargs["move_output_file_to_parent_dir"] = False
        kwargs["move_log_file_to_log_dir"] = False
        self.note_ids = helper.read_ids_to_list(note_ids)

        if not self.note_ids:
            raise ValueError("No note ids provided.")

        super().__init__(save_dir=save_dir, **kwargs)

    def get_downloaders(self) -> list[XhsNoteDownloader]:  # type: ignore
        return [
            XhsNoteDownloader(
                note_id=note_id,
                save_dir=self.get_downloader_save_dir(note_id),
                from_cli=False,
                disable_terminal_log=True,
            )
            for note_id in self.note_ids
        ]
