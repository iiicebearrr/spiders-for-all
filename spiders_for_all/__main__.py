import click

from spiders_for_all.database import cli as database_cli
from spiders_for_all.spiders.bilibili import cli as bilibili_cli
from spiders_for_all.spiders.xhs import cli as xhs_cli


@click.group()
def cli():
    pass


cli.add_command(bilibili_cli.cli)
cli.add_command(xhs_cli.cli)
cli.add_command(database_cli.cli)

if __name__ == "__main__":
    cli()
