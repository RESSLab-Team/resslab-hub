import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from resslab_hub.routers import analytics


@pytest.fixture
async def analytics_client(monkeypatch):
    # No GA property: a valid request answers -1 without calling Google.
    monkeypatch.setattr(analytics.settings, "analytics_property_id", "")
    app = FastAPI()
    app.include_router(analytics.router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.parametrize("days", ["0", "-1", "3651", "99999999"])
async def test_users_days_out_of_range_answers_422(analytics_client, days):
    """Each `days` is a cache key: the window is bounded (#264 Low)."""
    response = await analytics_client.get("/analytics/users", params={"days": days})
    assert response.status_code == 422


@pytest.mark.parametrize("params", [{}, {"days": "1"}, {"days": "3650"}])
async def test_users_days_in_range_is_accepted(analytics_client, params):
    response = await analytics_client.get("/analytics/users", params=params)
    assert response.status_code == 200
    assert response.json() == -1
