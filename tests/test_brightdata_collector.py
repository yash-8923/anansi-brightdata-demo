import os
import pytest
import respx
from httpx import Response

from anansi.collectors.brightdata import (
    BrightDataCollector,
    BrightDataCollectorError,
    TRIGGER_URL,
    RESULT_URL,
    SYNC_TRIGGER_URL,
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "test-key")
    monkeypatch.setenv("BRIGHTDATA_COLLECTOR_ID", "c_test123")


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("BRIGHTDATA_API_KEY", raising=False)
    with pytest.raises(BrightDataCollectorError):
        BrightDataCollector()


def test_missing_collector_id_raises(monkeypatch):
    monkeypatch.delenv("BRIGHTDATA_COLLECTOR_ID", raising=False)
    with pytest.raises(BrightDataCollectorError):
        BrightDataCollector()


@pytest.mark.asyncio
@respx.mock
async def test_run_triggers_and_polls():
    respx.post(TRIGGER_URL).mock(
        return_value=Response(200, json={"snapshot_id": "snap_1"})
    )
    respx.get(RESULT_URL).mock(
        return_value=Response(
            200,
            json=[{"title": "Widget", "price": 9.99, "url": "https://x.test/1"}],
        )
    )

    collector = BrightDataCollector()
    items = await collector.run()

    assert len(items) == 1
    assert items[0].data["title"] == "Widget"
    assert items[0].source_url == "https://x.test/1"
    assert items[0].spider_name == "brightdata:c_test123"


@pytest.mark.asyncio
@respx.mock
async def test_run_sync_path():
    respx.post(SYNC_TRIGGER_URL).mock(
        return_value=Response(200, json=[{"title": "Fast item"}])
    )

    collector = BrightDataCollector()
    items = await collector.run_sync()

    assert len(items) == 1
    assert items[0].data["title"] == "Fast item"


@pytest.mark.asyncio
@respx.mock
async def test_trigger_error_raises():
    respx.post(TRIGGER_URL).mock(return_value=Response(401, text="unauthorized"))

    collector = BrightDataCollector()
    with pytest.raises(BrightDataCollectorError):
        await collector.trigger()
