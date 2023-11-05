import click

from bilibili import analysis, spiders

from core.base import SPIDERS

from rich import print

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


if __name__ == "__main__":
    cli()
