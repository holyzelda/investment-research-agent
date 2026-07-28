from pathlib import Path


def test_run_entrypoint_does_not_create_an_unused_fastapi_application():
    source = Path("run.py").read_text(encoding="utf-8")

    assert "from app.main import create_app" not in source
    assert "app = create_app()" not in source
    assert 'uvicorn.run(\n        "app.main:app",' in source
