import requests
import subprocess
import pathlib
from concurrent import futures

API_GET_PLAY_ID = "https://yhdmoe.com/myapp/_get_ep_plays"
API_GET_M3U8_URL = "https://yhdmoe.com/myapp/_get_raw"

SAVE_DIR = pathlib.Path("~/Downloads/Attack_on_Titan").expanduser()
SAVE_DIR.mkdir(exist_ok=True)


def get_play_id(anime_id: str, ep: str) -> int:
    resp = requests.get(API_GET_PLAY_ID, params={"ep": ep, "anime_id": anime_id})
    return resp.json()["result"][0]["id"]


def get_m3u8_url(play_id: int) -> str:
    resp = requests.get(API_GET_M3U8_URL, params={"id": play_id})
    return resp.text


def download(anime_id: str, ep: str, season: str = "S1"):
    season_dir = SAVE_DIR / season
    season_dir.mkdir(exist_ok=True)
    play_id = get_play_id(anime_id, ep)
    url = get_m3u8_url(play_id)
    file = season_dir / f"{ep}.mp4"
    if file.exists():
        file.unlink()
    # TODO: sometime this ffmpeg will stuck forever
    cmd = ["ffmpeg", "-i", url, "-bsf:a", "aac_adtstoasc", "-c", "copy", str(file)]
    print(cmd)
    subprocess.call(cmd)

    print(f"Downloaded {file}")


def main():
    anime_id = "20180179"

    def f(ep):
        download(anime_id, ep, season="S3")

    with futures.ThreadPoolExecutor(max_workers=16) as executor:
        executor.map(f, [f"EP{i}" for i in range(1, 23)])


if __name__ == "__main__":
    main()
