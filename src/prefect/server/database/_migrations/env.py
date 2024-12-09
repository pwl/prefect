# Originally generated from `alembic init`
# https://alembic.sqlalchemy.org/en/latest/tutorial.html#creating-an-environment

import contextlib
from typing import Optional

import sqlalchemy
from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine

from prefect.server.database.configurations import SQLITE_BEGIN_MODE
from prefect.server.database.dependencies import provide_database_interface
from prefect.server.utilities.database import get_dialect
from prefect.utilities.asyncutils import run_async_from_worker_thread

db_interface = provide_database_interface()
config = context.config
target_metadata = db_interface.Base.metadata
dialect = get_dialect(db_interface.database_config.connection_url)


def include_object(
    object: sqlalchemy.schema.SchemaItem,
    name: str,
    type_: str,
    reflected: bool,
    compare_to: Optional[sqlalchemy.schema.SchemaItem],
) -> bool:
    """
    Determines whether or not alembic should include an object when autogenerating
    database migrations.

    Args:
        object: a sqlalchemy.schema.SchemaItem object such as a
            sqlalchemy.schema.Table, sqlalchemy.schema.Column,
            sqlalchemy.schema.Index sqlalchemy.schema.UniqueConstraint, or
            sqlalchemy.schema.ForeignKeyConstraint object.
        name: the name of the object. This is typically available via object.name.
        type: a string describing the type of object; currently "table", "column",
            "index", "unique_constraint", or "foreign_key_constraint"
        reflected: True if the given object was produced based on table reflection,
            False if it's from a local .MetaData object.
        compare_to: the object being compared against, if available, else None.

    Returns:
        bool: whether or not the specified object should be included in autogenerated
            migration code.
    """

    # because of the dynamic inheritance pattern used by the Prefect database,
    # it is difficult to get alembic to resolve references to indexes on inherited models
    #
    # to keep autogenerated migration code clean, we ignore the following indexes:
    # * functional indexes (ending in 'desc', 'asc'), if an index with the same name already exists
    # * trigram indexes that already exist
    # * case_insensitive indexes that already exist
    # * indexes that don't yet exist but have .ddl_if(dialect=...) metadata that doesn't match
    #   the current dialect.
    if type_ == "index":
        if not reflected:
            if name.endswith(("asc", "desc")):
                return compare_to is None or object.name != compare_to.name
            if (ddl_if := object._ddl_if) is not None and ddl_if.dialect is not None:
                desired: set[str] = (
                    {ddl_if.dialect}
                    if isinstance(ddl_if.dialect, str)
                    else set(ddl_if.dialect)
                )
                return dialect.name in desired

        else:  # reflected
            if name.startswith("gin") or name.endswith("case_insensitive"):
                return False

    # SQLite doesn't have an enum type, so reflection always comes back with
    # a VARCHAR column, which doesn't match. Skip columns where the type
    # doesn't match
    if (
        dialect.name == "sqlite"
        and type_ == "column"
        and object.type.__visit_name__ == "enum"
        and compare_to is not None
    ):
        return compare_to.type.__visit_name__ == "enum"

    return True


def dry_run_migrations() -> None:
    """
    Perform a dry run of migrations.

    This will create the sql statements without actually running them against the
    database and output them to stdout.
    """
    url = db_interface.database_config.connection_url
    context.script.version_locations = [db_interface.orm.versions_dir]

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_object=include_object,
        dialect_opts={"paramstyle": "named"},
        # Only use batch statements by default on sqlite
        #
        # The SQLite database presents a challenge to migration
        # tools in that it has almost no support for the ALTER statement
        # which relational schema migrations rely upon.
        # Migration tools are instead expected to produce copies of SQLite tables
        # that correspond to the new structure, transfer the data from the existing
        # table to the new one, then drop the old table.
        #
        # see https://alembic.sqlalchemy.org/en/latest/batch.html#batch-migrations
        render_as_batch=dialect.name == "sqlite",
        # Each migration is its own transaction
        transaction_per_migration=True,
        template_args={"dialect": dialect.name},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: AsyncEngine) -> None:
    """
    Run Alembic migrations using the connection.

    Args:
        connection: a database engine.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_object=include_object,
        # Only use batch statements by default on sqlite
        #
        # The SQLite database presents a challenge to migration
        # tools in that it has almost no support for the ALTER statement
        # which relational schema migrations rely upon.
        # Migration tools are instead expected to produce copies of SQLite tables
        # that correspond to the new structure, transfer the data from the existing
        # table to the new one, then drop the old table.
        #
        # see https://alembic.sqlalchemy.org/en/latest/batch.html#batch-migrations
        render_as_batch=dialect.name == "sqlite",
        # Each migration is its own transaction
        transaction_per_migration=True,
        template_args={"dialect": dialect.name},
    )

    # We override SQLAlchemy's handling of BEGIN on SQLite and Alembic bypasses our
    # typical transaction context manager so we set the mode manually here
    token = SQLITE_BEGIN_MODE.set("IMMEDIATE")
    try:
        with disable_sqlite_foreign_keys(context):
            with context.begin_transaction():
                context.run_migrations()
    finally:
        SQLITE_BEGIN_MODE.reset(token)


@contextlib.contextmanager
def disable_sqlite_foreign_keys(context):
    """
    Disable foreign key constraints on sqlite.
    """
    if dialect.name == "sqlite":
        context.execute("COMMIT")
        context.execute("PRAGMA foreign_keys=OFF")
        context.execute("BEGIN IMMEDIATE")

    yield

    if dialect.name == "sqlite":
        context.execute("END")
        context.execute("PRAGMA foreign_keys=ON")
        context.execute("BEGIN IMMEDIATE")


async def apply_migrations() -> None:
    """
    Apply migrations to the database.
    """
    engine = await db_interface.engine()
    context.script.version_locations = [db_interface.orm.versions_dir]

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    dry_run_migrations()
else:
    # Running `apply_migrations` via `asyncio.run` causes flakes in the tests
    # like: `cache lookup failed for type 338396`. Using `run_async_from_worker_thread`
    # does not cause this issue, but it is not clear why. The current working theory is
    # that running `apply_migrations` in another thread gives the migrations enough
    # isolation to avoid caching issues.
    run_async_from_worker_thread(apply_migrations)