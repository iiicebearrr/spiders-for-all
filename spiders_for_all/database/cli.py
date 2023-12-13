import click
import inspect
import re
from sqlalchemy import orm, create_engine, text
from rich import print, table
from spiders_for_all.spiders import bilibili, xhs
from spiders_for_all.database import schema, manager

# regex to match tablename from sql, case insensitive
RGX_FIND_TABLENAME = re.compile(r"FROM\s+([^\s;]+)", re.IGNORECASE)


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
    pass


@cli.command("query-schema")
@click.argument("sql", type=str)
def query(sql: str):
    _init_schemas()
    tablename = RGX_FIND_TABLENAME.search(sql)
    if tablename is None:
        print(
            "[red bold]Table not found. Run `python -m spiders_for_all database list-schema` to check the tablename[/red bold]"
        )
        exit(1)
    tablename = tablename.group(1)
    with session() as s:
        module = s.query(Schemas).filter_by(tablename=tablename).first()
        if module is None:
            print(
                "[red bold]Module not found. Run `python -m spiders_for_all database list-schema` to check the module and tablename[/red bold]"
            )
            exit(1)
    module = module.module.split(".")[-1]
    dql = manager.DQL(raw_sql=sql)
    if module == "bilibili":
        session_manager = bilibili.db.SessionManager
    elif module == "xhs":
        session_manager = xhs.db.SessionManager
    else:
        print(f"[red bold]Unknown or unsupported module: {module}[/red bold]")
        exit(1)
    rows = dql.execute(session_manager)
    if not rows:
        print("[red bold]No result[/red bold]")
        exit(1)
    headers = rows[0]._asdict().keys()
    t = table.Table(*headers, title="Results")
    for row in rows:
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
