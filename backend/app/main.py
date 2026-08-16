from fastapi import FastAPI

app = FastAPI(
    title="Research Atlas API",
    description="Conference-aware research discovery and evaluation.",
    version="0.1.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "Research Atlas API", "docs": "/docs"}

