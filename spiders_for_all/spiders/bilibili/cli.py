from pathlib import Path

import click
import sqlalchemy as sa
from rich import print

from spiders_for_all.conf import settings
from spiders_for_all.core.spider import SPIDERS
from spiders_for_all.spiders.bilibili import analysis, const, db, downloader, spiders

_ = spiders  # to call init_subclass

BILIBILI_SPIDERS = SPIDERS.get("bilibili", {})


@click.group("bilibili")
def cli():
    """Commands for bilibili platform"""
    pass


@click.argument("name")
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
@click.option(
    "--where", "-w", type=str, help="Where conditions to specify the bvid to download. "
)
@cli.command()
def run_spider(
    name: str,
    params: tuple[tuple[str, str]],
    save_dir: Path | None = None,
    sess_data: str | None = settings.BILIBILI_COOKIE_SESS_DATA,
    download_only: bool = False,
    where: str | None = None,
):
    """Run a spider by name"""
    if name not in BILIBILI_SPIDERS:
        raise ValueError(f"Spider {name} not found")  # pragma: no cover
    spider = BILIBILI_SPIDERS[name](**{k: v for k, v in params})  # type: ignore

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
            if where:
                select_bvid_stmt = select_bvid_stmt.where(sa.text(where))
            bvid_list = [row.bvid for row in s.execute(select_bvid_stmt)]

            if not bvid_list:
                print("[bold yellow]No videos found to be downloaded...")
                print(f"Statement: {select_bvid_stmt}")
                return

            print(f"[bold yellow]{len(bvid_list)} videos found to be downloaded...")

            multiple_downloader = downloader.BilibiliBatchDownloader(
                bvid_list=bvid_list,
                save_dir=save_dir,
                sess_data=sess_data,
                from_cli=True,
                max_workers=4,
            )

            multiple_downloader.download()


@cli.command("list")
def list_spiders():
    """List all available spiders"""
    for spider in {v: k for k, v in BILIBILI_SPIDERS.items()}:
        print(f"  - {spider.string()}")


@cli.command()
@click.option("--name", "-n", help="Spider name", required=True)
@click.option("--top-n", "-t", help="Top N", required=True, type=int, default=10)
def data_analysis(name: str, top_n: int):
    """List the data as table for a spider"""
    if name not in BILIBILI_SPIDERS:
        raise ValueError(f"Spider {name} not found")  # pragma: no cover
    spider = BILIBILI_SPIDERS[name]
    print(f"Running analysis: {spider.string()}")
    analysis.Analysis(spider.database_model, top_n).show()  # type: ignore


@cli.command("download-by-id")
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
    default=downloader.const.HIGHEST_QUALITY,
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
    quality: int = const.HIGHEST_QUALITY,
    codecs: str | None = None,
    ffmpeg_params: list[str] | None = None,
):
    """Download a video by bvid"""
    _downloader = downloader.BilibiliDownloader(
        bvid=bvid,
        save_dir=save_dir,
        filename=filename,
        remove_temp_dir=remove_temp_dir,
        sess_data=sess_data,
        quality=quality,
        codecs=codecs,
        ffmpeg_params=ffmpeg_params,
    )

    list(_downloader.download())


@cli.command("download-by-ids")
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

    You can do this by providing the list of bvid with `,`, `\n`, `\t`, or space separated:

    >> python -m spiders_for_all bilibili download-videos -b BVID1 BVID2 BVID3

    Or by providing a file contains bvid data like:

    \b
    bvid.txt:

    \b
    BVID1
    BVID2
    ...

    >> python -m spiders_for_all bilibili download-videos -b bvid.txt
    """

    path_bvid = Path(bvids)

    if path_bvid.exists():
        bvids = path_bvid

    multiple_downloader = downloader.BilibiliBatchDownloader(
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
@click.option(
    "--total",
    "-t",
    help="Total number of videos to fetch. If not set, will fetch all the videos of this user.",
    type=int,
)
def download_by_author(
    mid: int,
    save_dir: Path,
    sess_data: str | None = None,
    max_workers: int = 4,
    total: int | None = None,
):
    """Download videos by author id"""
    author_spider = spiders.AuthorSpider(
        mid=mid, sess_data=sess_data, total=total, record=True
    )
    author_spider.run()
    bvids = author_spider.get_record_bvid_list()

    if not bvids:
        print(f"[bold yellow]No videos found for author {mid}...")
        return

    print(
        f"[bold yellow]{len(bvids)} videos found to be downloaded for author {mid}..."
    )

    multiple_downloader = downloader.BilibiliBatchDownloader(
        bvid_list=bvids, save_dir=save_dir, sess_data=sess_data, max_workers=max_workers
    )

    multiple_downloader.download()


@cli.command("download-by-sql")
@click.argument("sql")
@click.option(
    "--save-dir",
    "-s",
    help="Path to save the downloaded videos",
    type=Path,
    required=True,
)
@click.option("--sess-data", "-ss", help="`SESSDATA`", required=False)
@click.option("--max-workers", "-w", help="max workers", type=int, default=4)
def download_by_sql(
    sql: str, save_dir: Path, sess_data: str | None = None, max_workers: int = 4
):
    """Download videos by sql"""
    with db.Session() as s:
        rows = s.execute(sa.text(sql))
        bvid_list: list[str] = list(
            filter(
                lambda bvid: bvid is not None,
                [getattr(row, "bvid", None) for row in rows],
            )
        )  # type: ignore

        if not bvid_list:
            print("[bold yellow]No videos found to be downloaded...")
            print(f"Statement: {sql}")
            return

    multiple_downloader = downloader.BilibiliBatchDownloader(
        bvid_list=bvid_list,
        save_dir=save_dir,
        sess_data=sess_data,
        max_workers=max_workers,
    )

    multiple_downloader.download()


@cli.command("fetch-feed")
@click.argument("mid")
def fetch_feed(mid: str):
    """Fetch feed by mid"""
    feed_spider = spiders.AuthorFeedSpaceSpider(
        mid=mid, sleep_before_next_request=(3, 6)
    )
    feed_spider.run()


if __name__ == "__main__":
    cli()  # pragma: no cover
