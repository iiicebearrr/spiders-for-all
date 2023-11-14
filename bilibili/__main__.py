from pathlib import Path

import click
from rich import print

from bilibili import analysis, spiders, download
from core.base import SPIDERS

_ = spiders  # to call init_subclass


@click.group()
def cli():
    pass


@click.option("--name", "-n", help="Spider name", required=True)
@click.option(
    "--params",
    "-p",
    help="Spider params",
    required=False,
    type=click.Tuple([str, str]),
    multiple=True,
)
@cli.command()
def run_spider(name: str, params: tuple[str, str]):
    if name not in SPIDERS:
        raise ValueError(f"Spider {name} not found")  # pragma: no cover
    spider = SPIDERS[name](**{k: v for k, v in params})
    print(f"Running spider: {spider.string()}")
    spider.run()


@cli.command()
def list_spiders():
    print("Available spiders:")
    reversed_map = {v: k for k, v in SPIDERS.items()}
    for spider in reversed_map:
        print(f"  - {spider.string()})")


@cli.command()
@click.option("--name", "-n", help="Spider name", required=True)
@click.option("--top-n", "-t", help="Top N", required=True, type=int, default=10)
def data_analysis(name: str, top_n: int):
    if name not in SPIDERS:
        raise ValueError(f"Spider {name} not found")  # pragma: no cover
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
    "--quality",
    "-q",
    help="Quality of the video to download. Defaults to HIGHEST_QUALITY.",
    required=False,
    type=int,
    default=download.HIGHEST_QUALITY,
)
@click.option(
    "--codecs",
    "-c",
    help="Regex to filter video codecs. Defaults to None.",
    required=False,
    type=str,
)
@click.option(
    "--ffmpeg-params",
    "-fp",
    help="Additional ffmpeg parameters. Defaults to None.",
    required=False,
    type=str,
    multiple=True,
)
def download_video(
    bvid: str,
    save_path: str | Path,
    filename: str | None = None,
    remove_temp_dir: bool = True,
    sess_data: str | None = None,
    quality: int = download.HIGHEST_QUALITY,
    codecs: str | None = None,
    ffmpeg_params: list[str] | None = None,
):
    downloader = download.Downloader(
        bvid,
        save_path,
        filename,
        remove_temp_dir,
        sess_data,
        quality,
        codecs,
        ffmpeg_params,
    )

    downloader.download()


if __name__ == "__main__":
    cli()  # pragma: no cover
