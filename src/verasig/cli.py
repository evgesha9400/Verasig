import typer
from sqlalchemy import text

from verasig.config import Settings
from verasig.foundation.db import make_engine

app = typer.Typer(help="Verasig — local observer CLI.")


@app.callback()
def main() -> None:
    """Verasig — local observer CLI (one subcommand per pipeline stage)."""


@app.command()
def health() -> None:
    """Verify the app can connect to the configured Postgres database."""
    with make_engine(Settings().database_url).connect() as connection:
        connection.execute(text("select 1"))
    typer.echo("OK: db connected")


if __name__ == "__main__":
    app()
