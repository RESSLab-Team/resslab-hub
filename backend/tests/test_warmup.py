"""The cache warmup runs in the app's lifespan and keeps its task (#265)."""

import asyncio

import pytest
from fastapi import FastAPI

from resslab_hub.utils import warmup as warmup_module
from resslab_hub.utils.warmup import warmup


@pytest.fixture
def small_app(monkeypatch):
    hits = []
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        hits.append(1)
        return {"ok": True}

    monkeypatch.setattr(warmup_module, "warm_paths", lambda: ["/ping"])
    return app, hits


async def test_warmup_keeps_its_task_and_cancels_it_at_shutdown(small_app):
    app, hits = small_app

    async with warmup(app, interval=3600):
        task = app.state.warmup_task
        assert isinstance(task, asyncio.Task)
        for _ in range(100):
            if app.state.warmed:
                break
            await asyncio.sleep(0.01)
        assert app.state.warmed
        assert hits == [1]
        assert not task.done()  # now sleeping until the next refresh

    assert task.cancelled()


async def test_no_warmup_when_caching_is_off(small_app):
    app, hits = small_app

    async with warmup(app, interval=0):
        assert app.state.warmed
        assert not hasattr(app.state, "warmup_task")

    assert hits == []


def test_app_uses_the_lifespan_not_on_event():
    from resslab_hub.main import app

    assert app.router.on_startup == []
    assert app.router.on_shutdown == []
