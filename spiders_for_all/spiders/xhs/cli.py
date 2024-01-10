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
    pass


@cli.command("list")
def list_spiders():
    """List all available spiders."""
    print("Available spiders:")
    for spider in {v: k for k, v in SPIDERS.items()}:
        print(f"  - {spider}")


@cli.command("spider-author")
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
    "--download-only",
    "-d",
    is_flag=True,
    help="Only download the notes data depending on the local database, without running the spider again",
)
@click.option(
    "--save-dir",
    "-s",
    help="If set `--save-dir`, will download all the notes data to the directory when the spider finished",
    type=Path,
    required=False,
)
@click.option(
    "--where",
    "-w",
    type=str,
    help="Where conditions to specify the note_id to download. "
    'For example: "author_id=1234567890"',
)
def author_spider(
    uid: str,
    on_init: str,
    on_save: str,
    download_only: bool,
    save_dir: Path | None = None,
    where: str | None = None,
):
    """Crawl author's notes, and download them if specified."""
    if not download_only:
        spider = xhs.spiders.XhsAuthorSpider(
            uid=uid,
            db_action_on_init=DbActionOnInit(int(on_init)),
            db_action_on_save=DbActionOnSave(int(on_save)),
        )
        spider.run()

    if download_only and not save_dir:
        print("You must specify `-s` or `--save-dir`")
        exit(1)

    if save_dir:
        with xhs.db.Session() as s:
            note_ids_query = sa.select(xhs.schema.XhsAuthorNotes.note_id)
            if where:
                note_ids_query = note_ids_query.where(sa.text(where))
            note_ids = [row.note_id for row in s.execute(note_ids_query)]

        if not note_ids:
            print(
                "No notes found to be downloaded, may be you should run the spider first or check the `--where` option?"
            )
            print(f"SQL: {note_ids_query}")
            exit(1)

        downloader = xhs.downloader.XhsNoteBatchDownloader(
            note_ids=note_ids,
            save_dir=save_dir,  # type: ignore
        )

        downloader.download()


@cli.command("download")
@click.option(
    "--note-ids",
    "-i",
    required=True,
    help="A string of comma separated note ids, or a file path.",
)
@click.option("--save-dir", "-s", type=Path, required=True)
def download_notes(note_ids: str | Path, save_dir: Path):
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
        note_ids=note_ids, save_dir=save_dir
    )

    downloader.download()
