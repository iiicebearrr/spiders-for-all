from pathlib import Path

import click
from rich import print

from bilibili import analysis, spiders, download
from core.base import SPIDERS

_ = spiders  # to call init_subclass


@click.group()
def cli():
    pass


@cli.command()
@click.option("--name", "-n", help="Spider name", required=True)
@click.option(
    "--params",
    "-p",
    help="Spider params",
    required=False,
    type=click.Tuple([str, str]),
    multiple=True,
)
def run_spider(name: str, params: tuple[str, str]):
    if name not in SPIDERS:
        raise ValueError(f"Spider {name} not found")
    spider = SPIDERS[name](**{k: v for k, v in params})
    print(f"Running spider: {spider.string()}")
    spider.run()


@cli.command()
def list_spiders():
    print("Available spiders:")
    REVERSED = {v: k for k, v in SPIDERS.items()}
    for spider in REVERSED:
        print(f"  - {spider.string()})")


@cli.command()
@click.option("--name", "-n", help="Spider name", required=True)
@click.option("--top-n", "-t", help="Top N", required=True, type=int, default=10)
def data_analysis(name: str, top_n: int):
    if name not in SPIDERS:
        raise ValueError(f"Spider {name} not found")
    spider = SPIDERS[name]
    print(f"Running analysis: {spider.string()}")
    analysis.Analysis(spider.database_model, top_n).show()  # type: ignore


@cli.command()
@click.option("--bvid", "-b", help="Bvid of the video", required=True, type=str)
@click.option(
    "--save-path", "-s", help="Save path of the video", required=True, type=Path
)
@click.option(
    "--filename",
    "-f",
    help="Filename of the video. By default, will use the bvid as the output filename",
    required=False,
    type=str,
)
@click.option(
    "--suffix",
    "-x",
    help="Suffix of the video",
    required=False,
    type=str,
    default=".mp4",
)
@click.option(
    "--remove-temp-dir",
    "-r",
    help="Whether to remove the temp dir after download",
    required=False,
    type=bool,
    default=True,
)
@click.option(
    "--sess-data",
    "-d",
    help="Pass to requests as cookies to download high quality video. "
    "You should get this from:"
    "your browser -> Devtools -> Choose any request -> Cookies -> SESSDATA.",
    required=False,
    type=str,
)
@click.option(
    "--video-idx",
    "-i",
    help="Index of video chosen to be processed by ffmpeg. "
    "0 means the highest quality video.",
    required=False,
    type=int,
    default=0,
)
def download_videos(
    bvid: str,
    save_path: str | Path,
    filename: str | None = None,
    suffix: str = ".mp4",
    remove_temp_dir: bool = True,
    sess_data: str | None = None,
    video_idx: int = 0,
):
    downloader = download.Downloader(
        bvid,
        save_path,
        filename=filename,
        suffix=suffix,
        remove_temp_dir=remove_temp_dir,
        sess_data=sess_data,
    )

    downloader.download()
    downloader.process(video_idx=video_idx)


if __name__ == "__main__":
    cli()
