import requests
import re
import json
import subprocess
from pathlib import Path
from utils.helper import user_agent_headers
from bilibili import models
from utils.logger import default_logger as logger
from enum import Enum
from operator import attrgetter

type Media = models.PlayVideo | models.PlayAudio
type Medias = list[Media]
type Videos = list[models.PlayVideo]
type Audios = list[models.PlayAudio]


class MediaType(Enum):
    VIDEO = "video"
    AUDIO = "audio"


API_PREFIX = "https://www.bilibili.com/video/"

# Regex to find playinfo in <script>window.__playinfo__=</script>
RGX_FIND_PLAYINFO = re.compile(r"<script>window\.__playinfo__=(.*?)</script>")


class Downloader:
    origin: str = "https://www.bilibili.com"
    api: str = "https://www.bilibili.com/video/{bvid}/"
    default_video_suffix: str = ".mp4"
    valid_video_suffixs: list[str] = [".mp4", ".mkv"]

    def __init__(
        self,
        bvid: str,
        save_path: str | Path,
        filename: str | None = None,
        remove_temp_dir: bool = True,
        suffix: str = default_video_suffix,
    ):
        self.bvid = bvid
        self.save_path = save_path if isinstance(save_path, Path) else Path(save_path)
        self.temp_dir = save_path / ".temp"  # type: ignore
        self.remove_temp_dir = remove_temp_dir
        # The final filename processed by ffmpeg
        self.filename = self.save_path / f"{filename or bvid}"

        if self.filename.suffix not in self.valid_video_suffixs:
            self.filename = self.filename.with_suffix(suffix)

        self.api = self.__class__.api.format(bvid=bvid)

        self.save_path.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)

        self.videos: list[Path] = []
        self.audios: list[Path] = []
        self.temp_audio: Path | None = None

    def get_play_info(self) -> models.PlayInfoData:
        headers = {**user_agent_headers()}
        response = requests.get(self.api, headers=headers)
        response.raise_for_status()
        html_content = response.text
        playinfo = RGX_FIND_PLAYINFO.search(html_content)
        if playinfo is None:
            raise ValueError(f"Playinfo not found from {html_content}")
        playinfo = playinfo.group(1)
        return models.PlayInfoResponse(**json.loads(playinfo)).data

    def _download(self, media: Media, save_path: Path) -> Path:
        if not isinstance(save_path, Path):
            save_path = Path(save_path)
        headers = {
            "Referer": self.origin,
            **user_agent_headers(),
        }
        save_path.unlink(missing_ok=True)
        logger.debug(f"Downloading {media.base_url} to {save_path}. Headers: {headers}")
        with requests.get(media.base_url, headers=headers, stream=True) as resp:  # type: ignore
            resp.raise_for_status()
            size = 0
            with save_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    size += len(chunk)

        logger.debug(f"Downloaded: {size / 1024 / 1024} MB")

        return save_path

    def download_videos(self, medias: Videos):
        # By default, will download the highest quality video
        for idx, media in enumerate(medias):
            logger.info(f"[{media.quality}] Downloading video...")
            path = self._download(media, self.temp_dir / f"video-temp-{idx}.mp4")
            self.videos.append(path)

    def download_audios(self, medias: Audios):
        for idx, media in enumerate(medias):
            logger.debug("Downloading audio...")
            path = self._download(media, self.temp_dir / f"audio-temp-{idx}.mp4")
            self.audios.append(path)

    def clean(self):
        if self.remove_temp_dir:
            self.temp_dir.rmdir()

    def process(self, video_idx: int | None = None):
        # process with ffmpeg
        # By default, will concat the first video and all audios
        if video_idx is None:
            video_idx = 0
        video_path = self.videos[video_idx]

        # concat audios
        audio_path = self.temp_dir / "audio-temp.wav"

        with audio_path.open("wb") as f:
            for audio in self.audios:
                f.write(audio.read_bytes())

        # merge video and audio
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
            str(self.filename),
        ]

        logger.debug(f"FFMPEG: {' '.join(cmd)}")

        subprocess.run(cmd, check=True)

    def download(self):
        play_info = self.get_play_info()

        # NOTE: Anonymouse user can only download the lowest quality video,
        # choose the highest quality video
        videos = sorted(play_info.dash.video, key=attrgetter("quality"), reverse=True)
        self.download_videos(videos)
        self.download_audios(play_info.dash.audio)
        self.process()


if __name__ == "__main__":
    from conf import settings

    test_bvid = "BV1kg4y1R7Tj"
    save_path = settings.BASE_DIR / "tmp"
    downloader = Downloader(test_bvid, save_path, remove_temp_dir=False)
    downloader.download()
