from pathlib import Path

import click
import sqlalchemy as sa
from rich import print

from spiders_for_all.bilibili import spiders, download
from spiders_for_all.bilibili import analysis
from spiders_for_all.bilibili import db
from spiders_for_all.core.base import SPIDERS

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
@click.option(
    "--save-dir",
    "-s",
    help="If set `--save-dir`, all the videos will be downloaded when the spider finished",
    type=Path,
    required=False,
)
@click.option("--sess-data", "-ss", help="`SESSDATA`", required=False)
@click.option(
    "--download-only",
    "-d",
    is_flag=True,
)
@cli.command()
def run_spider(
    name: str,
    params: tuple[tuple[str, str]],
    save_dir: Path | None = None,
    sess_data: str | None = None,
    download_only: bool = False,
):
    """Run a spider by name"""
    if name not in SPIDERS:
        raise ValueError(f"Spider {name} not found")  # pragma: no cover
    spider = SPIDERS[name](**{k: v for k, v in params})

    if not download_only:
        print(f"[bold light_green]Running spider: {spider.string()}")
        spider.run()

    if download_only and save_dir is None:
        click.echo("You must set `--save-path` to download the videos")
        exit(1)

    if save_dir is not None:
        with db.Session() as s:
            db_model = spider.database_model
            select_bvid_stmt = sa.select(getattr(db_model, "bvid"))
            bvid_list = [row.bvid for row in s.execute(select_bvid_stmt)]

            print(f"[bold yellow]{len(bvid_list)} videos found to be downloaded...")

            multiple_downloader = download.MultiThreadDownloader(
                bvid_list=bvid_list,
                save_dir=save_dir,
                sess_data=sess_data,
                from_cli=True,
                max_workers=4,
            )

            multiple_downloader.download()


@cli.command()
def list_spiders():
    """List all available spiders"""
    print("Available spiders:")
    reversed_map = {v: k for k, v in SPIDERS.items()}
    for spider in reversed_map:
        print(f"  - {spider.string()})")


@cli.command()
@click.option("--name", "-n", help="Spider name", required=True)
@click.option("--top-n", "-t", help="Top N", required=True, type=int, default=10)
def data_analysis(name: str, top_n: int):
    """List the data as table for a spider"""
    if name not in SPIDERS:
        raise ValueError(f"Spider {name} not found")  # pragma: no cover
    spider = SPIDERS[name]
    print(f"Running analysis: {spider.string()}")
    analysis.Analysis(spider.database_model, top_n).show()  # type: ignore


@cli.command()
@click.option("--bvid", "-b", help="Bvid of the video", required=True, type=str)
@click.option(
    "--save-dir", "-s", help="Save directory of the video", required=True, type=Path
)
@click.option(
    "--filename",
    "-f",
    help="Filename of the video. By default, will use the bvid as the output filename.",
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
    save_dir: str | Path,
    filename: str | None = None,
    remove_temp_dir: bool = True,
    sess_data: str | None = None,
    quality: int = download.HIGHEST_QUALITY,
    codecs: str | None = None,
    ffmpeg_params: list[str] | None = None,
):
    """Download a video by bvid"""
    downloader = download.Downloader(
        bvid,
        save_dir,
        filename,
        remove_temp_dir,
        sess_data,
        quality,
        codecs,
        ffmpeg_params,
    )

    with downloader:
        downloader.download()


@cli.command()
@click.option(
    "--bvids",
    "-b",
    help="bvid list provided to download the videos",
    required=True,
)
@click.option(
    "--save-dir",
    "-s",
    help="Path to save the downloaded videos",
    type=Path,
    required=True,
)
@click.option("--sess-data", "-ss", help="`SESSDATA`", required=False)
@click.option("--max-workers", "-w", help="max workers", type=int, default=4)
def download_videos(
    bvids: str | Path,
    save_dir: Path,
    sess_data: str | None = None,
    max_workers: int = 4,
):
    """Download multiple videos once

    You can do this by providing the list of bvid with `,`, `\n`, `\t`, or space seperated:

    >> python -m spiders_for_all.bilibili download-videos -b BVID1 BVID2 BVID3

    Or by providing a file contains bvid data like:

    \b
    bvid.txt:

    \b
    BVID1
    BVID2
    ...

    >> python -m spiders_for_all.bilibili download-videos -b bvid.txt
    """

    path_bvid = Path(bvids)

    if path_bvid.exists():
        bvids = path_bvid

    multiple_downloader = download.MultiThreadDownloader(
        bvid_list=bvids, save_dir=save_dir, sess_data=sess_data, max_workers=max_workers
    )

    multiple_downloader.download()


@cli.command()
@click.option("--mid", "-m", help="mid of the author", required=True, type=int)
@click.option(
    "--save-dir",
    "-s",
    help="Path to save the downloaded videos",
    type=Path,
    required=True,
)
@click.option("--sess-data", "-ss", help="`SESSDATA`", required=False)
@click.option("--max-workers", "-w", help="max workers", type=int, default=4)
def download_by_author(
    mid: int, save_dir: Path, sess_data: str | None = None, max_workers: int = 4
):
    with db.Session() as s:
        bvids = [
            row.bvid
            for row in s.execute(
                sa.select(db.BilibiliAuthorVideo.bvid).where(
                    db.BilibiliAuthorVideo.mid == mid
                )
            )
        ]

    print(
        f"[bold yellow]{len(bvids)} videos found to be downloaded for author {mid}..."
    )

    multiple_downloader = download.MultiThreadDownloader(
        bvid_list=bvids, save_dir=save_dir, sess_data=sess_data, max_workers=max_workers
    )

    multiple_downloader.download()


if __name__ == "__main__":
    cli()  # pragma: no cover
