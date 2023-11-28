import json
import re
import subprocess
from enum import Enum
from operator import attrgetter
from pathlib import Path
from functools import cached_property
from typing import Callable, TypeAlias

import requests

from spiders_for_all.bilibili import models
from spiders_for_all.utils.helper import user_agent_headers
from spiders_for_all.utils.logger import default_logger as logger

Media: TypeAlias = models.PlayVideo | models.PlayAudio
Medias: TypeAlias = list[Media]
Videos: TypeAlias = list[models.PlayVideo]
Audios: TypeAlias = list[models.PlayAudio]
VideoPath: TypeAlias = Path
AudioPath: TypeAlias = Path

FFMPEG: str | None = None


class MediaType(Enum):
    VIDEO = "video"
    AUDIO = "audio"


API_PREFIX = "https://www.bilibili.com/video/"

# Regex to find playinfo in <script>window.__playinfo__=</script>
RGX_FIND_PLAYINFO = re.compile(r"<script>window\.__playinfo__=(.*?)</script>")

HIGHEST_QUALITY = 0


class Downloader:
    origin: str = "https://www.bilibili.com"
    api: str = "https://www.bilibili.com/video/{bvid}/"
    default_video_suffix: str = ".mp4"

    def __init__(
        self,
        bvid: str,
        save_path: str | Path,
        filename: str | None = None,
        remove_temp_dir: bool = True,
        sess_data: str | None = None,
        quality: int = HIGHEST_QUALITY,
        codecs: str | None = None,
        ffmpeg_params: list[str] | None = None,
        process_func: Callable[[VideoPath, AudioPath], None] | None = None,
    ):
        """Download bilibili video

        Args:
            bvid (str): bilibili video id
            save_path (str | Path): save path
            filename (str | None, optional): output filename. Defaults to `bvid`.
            remove_temp_dir (bool, optional): Whether to remove the temporary directory after processing. Defaults to True.
            sess_data (str | None, optional): Login session data to download high quality video. Defaults to None.
                Where to find sess_data:
                    1. Open www.bilibili.com in browser
                    2. Open developer tools
                    3. Select Network tab
                    4. Refresh the page
                    5. Select the first request
                    6. Find the cookie in Request Headers
                    7. Copy the value of SESSDATA
            quality (int, optional): Quality of the video to download. Defaults to HIGHEST_QUALITY.
            codecs (str | None, optional): Regex to filter video codecs. Defaults to None.
            ffmpeg_params (list[str] | None, optional): Additional ffmpeg parameters. Defaults to None.
            process_func (Callable[[VideoPath, AudioPath], None] | None, optional): Custom process function to take place of `self.process`. Defaults to None.

        """
        self.bvid = bvid
        self.save_path = save_path if isinstance(save_path, Path) else Path(save_path)
        self.temp_dir = save_path / ".temp"  # type: ignore
        self.remove_temp_dir = remove_temp_dir
        self.sess_data = sess_data
        self.quality = quality
        self.codecs = codecs
        self.ffmpeg_params = ffmpeg_params

        self.process_func = process_func
        # The final filename processed by ffmpeg
        self.filename = self.save_path / f"{filename or bvid}"

        if not self.filename.suffix:
            self.filename = self.filename.with_suffix(self.default_video_suffix)

        self.api = self.__class__.api.format(bvid=bvid)

        self.save_path.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)

        self.audios_path: list[Path] = []
        self.temp_audio: Path | None = None

    @cached_property
    def play_info(self) -> models.PlayInfoData:
        return self.get_play_info()

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

    def get_play_info(self) -> models.PlayInfoData:
        headers = {**user_agent_headers()}
        cookies = {"SESSDATA": self.sess_data} if self.sess_data is not None else {}
        logger.debug(
            f"Requesting {self.api}{f' with cookies {cookies}' if cookies else ''}"
        )
        response = requests.get(self.api, headers=headers, cookies=cookies)
        response.raise_for_status()
        html_content = response.text
        playinfo = RGX_FIND_PLAYINFO.search(html_content)
        if playinfo is None:
            raise ValueError(f"Playinfo not found from {html_content}")
        playinfo = playinfo.group(1)  # type: ignore
        return models.PlayInfoResponse(**json.loads(playinfo)).data  # type: ignore

    def _download(self, media: Media, save_path: Path) -> Path:
        if not isinstance(save_path, Path):
            save_path = Path(save_path)
        headers = {
            "Referer": self.origin,
            **user_agent_headers(),
        }

        save_path.unlink(missing_ok=True)

        logger.debug(f"Downloading {media.base_url} to {save_path}")
        with requests.get(media.base_url, headers=headers, stream=True) as resp:  # type: ignore
            resp.raise_for_status()
            size = 0
            with save_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    size += len(chunk)

        logger.debug(f"Downloaded: {size / 1024 / 1024} MB")

        return save_path

    def download_video(self, video: models.PlayVideo) -> Path:
        logger.info(f"[{video.quality}] Downloading video...")
        return self._download(
            video,
            self.temp_dir
            / f"video-{self.play_info.quality_map[video.quality]}-{video.codecs}.mp4",
        )

    def download_audios(self, medias: Audios) -> Path:
        for idx, media in enumerate(medias):
            logger.debug("Downloading audio...")
            path = self._download(media, self.temp_dir / f"audio-temp-{idx}.mp4")
            self.audios_path.append(path)
        # concat audios
        audio_path = self.temp_dir / "audio-temp.wav"

        with audio_path.open("wb") as f:
            for audio in self.audios_path:
                f.write(audio.read_bytes())

        return audio_path

    def clean(self):
        if self.remove_temp_dir:
            self.temp_dir.rmdir()

    def process(self, video_path: VideoPath, audio_path: AudioPath):
        """Process video and audio with ffmpeg

        Args:
            video_path (Path): video path
            audio_path (Path): audio path
        """
        # process with ffmpeg

        global FFMPEG
        if FFMPEG is None:
            FFMPEG = subprocess.check_output(["which", "ffmpeg"]).decode().strip()

        cmd = [
            FFMPEG,
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            str(self.filename),
        ]

        if self.ffmpeg_params:
            cmd.extend(self.ffmpeg_params)

        logger.debug(f"Process {video_path} with FFMPEG: {' '.join(cmd)}")

        subprocess.run(cmd, check=True)

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

    def download(self):
        video_path = self.download_video(self.video_to_download)
        audio_path = self.download_audios(self.play_info.dash.audio)
        if self.process_func is not None and callable(self.process_func):
            self.process_func(video_path, audio_path)
        else:
            self.process(video_path, audio_path)
