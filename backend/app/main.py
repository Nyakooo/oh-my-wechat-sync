from fastapi import FastAPI


app = FastAPI(
    title="WeChat Archive",
    version="0.1.0",
    description="Import-first, read-only archive service.",
)


@app.get("/healthz", tags=["system"])
def healthz() -> dict[str, str]:
    return {"status": "ok", "mode": "import-first"}
