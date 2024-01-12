import inspect
import re

import click
from rich import print, table
from sqlalchemy import create_engine, orm, text

from spiders_for_all.database import schema
from spiders_for_all.spiders import bilibili, xhs

# regex to match tablename from sql, case insensitive
RGX_FIND_TABLENAME = re.compile(r"FROM\s+([^\s;]+)", re.IGNORECASE)


def is_select(sql: str):
    return sql.lstrip().upper().startswith("SELECT")


def is_dml(sql: str):
    return any(
        [sql.lstrip().upper().startswith(s) for s in ["INSERT", "UPDATE", "DELETE"]]
    )


def is_ddl(sql: str):
    return any(
        [sql.lstrip().upper().startswith(s) for s in ["CREATE", "ALTER", "DROP"]]
    )


def get_session_manager(module: str):
    if module == "bilibili":
        return bilibili.db.SessionManager
    elif module == "xhs":
        return xhs.db.SessionManager
    else:
        print(f"[red bold]Unknown or unsupported module: {module}")
        exit(1)


class Base(orm.DeclarativeBase):
    pass


class Schemas(Base):
    __tablename__ = "t_schemas"

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    module: orm.Mapped[str]
    classname: orm.Mapped[str]
    tablename: orm.Mapped[str]


engine = create_engine("sqlite:///:memory:")
session = orm.sessionmaker(bind=engine)

_MODULES = [bilibili, xhs]


def _init_schemas():
    Base.metadata.create_all(engine)
    schema_items = []
    for module in _MODULES:
        if not hasattr(module, "schema"):
            continue
        for name, obj in inspect.getmembers(module.schema):
            if (
                inspect.isclass(obj)
                and issubclass(obj, schema.BaseTable)
                and hasattr(obj, "__tablename__")
            ):
                schema_items.append(
                    Schemas(
                        module=module.__name__,
                        classname=name,
                        tablename=obj.__tablename__,
                    )
                )
    with session() as s:
        s.add_all(schema_items)
        s.commit()


@click.group("database")
def cli():
    """Helpful commands for database management"""
    pass


@cli.command("sql")
@click.argument("sql", type=str)
@click.option(
    "--database", "-d", type=click.Choice(["bilibili", "xhs"]), required=False
)
def execute(sql: str, database: str | None = None):
    _init_schemas()

    if is_ddl(sql):
        if not database:
            print(
                "[red bold]DDL statement must specify a database[/red bold] (bilibili or xhs)"
            )
            exit(1)
        session_manager = get_session_manager(database)

        with session_manager.session() as s:
            s.execute(text(sql))
            s.commit()
            print("[bold]Finished[/bold]")
            exit(0)

    tablename = RGX_FIND_TABLENAME.search(sql)
    if tablename is None:
        print(
            "[red bold]Table not found. Run `python -m spiders_for_all database list-schema` to check the tablename[/red bold]"
        )
        exit(1)
    tablename = tablename.group(1)  # type: ignore
    with session() as s:
        module = s.query(Schemas).filter_by(tablename=tablename).first()
        if module is None:
            print(
                "[red bold]Module not found. Run `python -m spiders_for_all database list-schema` to check the module and tablename[/red bold]"
            )
            exit(1)
    module_name = module.module.split(".")[-1]
    session_manager = get_session_manager(module_name)
    stmt = text(sql)

    with session_manager.session() as s:
        results = s.execute(stmt)
        if is_select(sql):
            results = results.fetchall()
        elif is_dml(sql):
            s.commit()
            print("[bold]Finished[/bold]")
            exit(0)
        else:
            print("[red bold]Unknown statement[/red bold]")
            exit(1)

    count = len(results)
    if count == 0:
        print("[bold light_green]No results[/bold light_green]")
        exit(0)
    headers = results[0]._asdict().keys()
    t = table.Table(*headers, title=f"{count} Results")
    for row in results:
        t.add_row(*[str(v) for v in row])
    print(t)


@cli.command("list-schema")
@click.option("--where", "-w", type=str, default=None, help="Where clause.")
def list_schema(where: str | None = None):
    _init_schemas()
    t = table.Table("module", "classname", "tablename", title="Schemas")

    with session() as s:
        stmt = s.query(Schemas)

        sql = str(stmt.statement.compile(compile_kwargs={"literal_binds": True}))

        if where is not None:
            sql += f" WHERE {where}"

        rows = s.execute(text(sql)).fetchall()

        for row in rows:
            t.add_row(row.module, row.classname, row.tablename)

    print(t)
