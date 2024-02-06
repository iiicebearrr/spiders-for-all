from pathlib import Path

import click
import sqlalchemy as sa

from spiders_for_all.core.spider import SPIDERS as _SPIDERS
from spiders_for_all.core.spider import DbActionOnInit, DbActionOnSave
from spiders_for_all.spiders import xhs

_ = xhs.spiders

SPIDERS = _SPIDERS.get("xhs", {})


@click.group("xhs")
def cli():
    """Commands for xhs platform"""
    pass


@cli.command("list")
def list_spiders():
    """List all available spiders."""
    print("Available spiders:")
    for spider in {v: k for k, v in SPIDERS.items()}:
        print(f"  - {spider}")


@cli.command("download-by-author")
@click.argument("uid")
@click.option(
    "--on-init",
    type=click.Choice(
        choices=(
            str(DbActionOnInit.CREATE_IF_NOT_EXIST.value),
            str(DbActionOnInit.DROP_AND_CREATE.value),
        )
    ),
    default=str(DbActionOnInit.CREATE_IF_NOT_EXIST.value),
    help="Action to take on database initialization. "
    "1: Create if not exist."
    "2: Drop and create."
    "Default: 1",
)
@click.option(
    "--on-save",
    type=click.Choice(
        choices=(
            str(DbActionOnSave.DELETE_AND_CREATE.value),
            str(DbActionOnSave.UPDATE_OR_CREATE.value),
        )
    ),
    default=str(DbActionOnSave.UPDATE_OR_CREATE.value),
    help="Action to take on database save. "
    "1: Delete and create."
    "2: Update or create(upsert)."
    "Default: 2",
)
@click.option(
    "--save-dir",
    "-s",
    help="If set `--save-dir`, will download all the notes data to the directory when the spider finished",
    type=Path,
    required=True,
)
def download_by_author(
    uid: str,
    on_init: str,
    on_save: str,
    save_dir: Path | None = None,
):
    """Crawl author's notes, and download them."""
    spider = xhs.spiders.XhsAuthorSpider(
        uid=uid,
        db_action_on_init=DbActionOnInit(int(on_init)),
        db_action_on_save=DbActionOnSave(int(on_save)),
        record=True,
    )
    spider.run()

    note_ids = spider.record_note_id_list

    if not note_ids:
        print(
            "No notes found to be downloaded, may be you should run the spider first or check the `--where` option?"
        )
        exit(1)

    downloader = xhs.downloader.XhsNoteBatchDownloader(
        note_ids=note_ids,
        save_dir=save_dir,  # type: ignore
    )

    downloader.download()


@cli.command("download-by-id")
@click.option(
    "--note-ids",
    "-i",
    required=True,
    help="A string of comma separated note ids, or a file path.",
)
@click.option("--save-dir", "-s", type=Path, required=True)
@click.option("--max-workers", "-w", type=int, default=4)
def download_notes(note_ids: str | Path, save_dir: Path, max_workers: int = 4):
    """Download notes by note ids.

    For example:

    >> python -m spiders_for_all xhs download -i id_1,id_2 -s /path/to/save/dir

    >> python -m spiders_for_all xhs download -i /path/to/note/ids.txt -s /path/to/save/dir

    /path/to/note/ids.txt:

    \b
        1234567890
        1234567891
        ...
    """
    downloader = xhs.downloader.XhsNoteBatchDownloader(
        note_ids=note_ids, save_dir=save_dir, max_workers=max_workers
    )

    downloader.download()


@cli.command("download-by-sql")
@click.argument("sql")
@click.option("--save-dir", "-s", type=Path, required=True)
@click.option("--max-workers", "-w", type=int, default=4)
def download_by_sql(sql: str, save_dir: Path, max_workers: int):
    """Download notes by sql."""
    with xhs.db.Session() as s:
        stmt = sa.text(sql)
        rows = s.execute(stmt)
        note_ids: list[str] = [getattr(row, "note_id", None) for row in rows]  # type: ignore

        if not note_ids:
            print("[bold yellow]No notes found to be downloaded...")
            print(f"Statement: {sql}")
            return

    downloader = xhs.downloader.XhsNoteBatchDownloader(
        note_ids=note_ids, save_dir=save_dir, max_workers=max_workers
    )

    downloader.download()


@cli.command("get-comments")
@click.argument("note_id")
@click.option("--disable-rate-limit", "-d", is_flag=True)
def get_comments(note_id: str, disable_rate_limit: bool = False):
    """Get comments by note id"""

    spider = xhs.spiders.XhsCommentSpider(
        note_id=note_id,
        sleep_before_next_request=(3, 6) if not disable_rate_limit else None,
    )
    spider.run()


@cli.command("search")
@click.argument("keyword")
@click.option("--total", "-t", type=int, default=100)
@click.option(
    "--sort",
    "-s",
    type=click.Choice(["general", "time_descending", "popularity_descending"]),
    default="general",
)
@click.option(
    "--note-type", "-n", type=int, default=0, help="0: all 1: video 2: normal"
)
def search(keyword: str, total: int, sort: str, note_type: int):
    """Search notes by keyword"""
    spider = xhs.spiders.XhsSearchSpider(
        keyword=keyword,
        total=total,
        sort=xhs.models.XhsSortType(sort),
        note_type=xhs.models.XhsSearchNoteType(note_type),
        sleep_before_next_request=(3, 6),
    )
    spider.run()
