from pathlib import Path

from fastapi import FastAPI

from archive_core.database import connect, initialize

from .api import build_router, connection_factory_for, default_paths


def create_app(database_path: str | Path | None = None) -> FastAPI:
    configured_db, archive_root = default_paths()
    db_path = Path(database_path) if database_path is not None else configured_db
    factory = connection_factory_for(db_path)

    app = FastAPI(
        title="WeChat Archive",
        version="0.1.0",
        description="Import-first, read-only archive service.",
    )

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict[str, object]:
        with factory() as connection:
            initialize(connection)
            account_count = connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
            message_count = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        return {
            "status": "ok",
            "mode": "import-first",
            "storage": {"database": str(db_path), "archive_root": str(archive_root)},
            "counts": {"accounts": account_count, "messages": message_count},
        }

    app.include_router(build_router(factory, archive_root))
    return app


app = create_app()
