import concurrent.futures
import pytest
from app.services import store_artifacts as artifacts
from app.services import emag_playbooks as service


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)

    def create(store="demo-ro", stock=2):
        return artifacts.import_snapshot(
            {
                "store_id": store,
                "platform": "emag",
                "marketplace": "RO",
                "captured_at": "2026-11-07T00:00:00Z",
                "source": "synthetic",
                "coverage": ["offers"],
                "limitations": ["Synthetic"],
                "data": {"offers": [{"id": 1, "name": "Example", "part_number": "SKU", "general_stock": stock}]},
            }
        )

    return create


def save(source, **kwargs):
    args = {
        "store_id": source["store_id"],
        "snapshot_id": source["snapshot_id"],
        "kind": "listing",
        "product_id": "1",
        "payload": {"title": "Example"},
        "actor": "operator",
    }
    args.update(kwargs)
    return service.save(**args)


def test_immutable_revisions_and_store_identity(snapshot):
    source = snapshot()
    first = save(source)
    second = save(source, record_id=first["record_id"], revision=1, payload={"title": "Revised"})
    assert second["revision"] == 2 and second["marketplace_writes"] is False
    records = service.view("demo-ro")["records"]
    assert [r["revision"] for r in records] == [2, 1]
    assert records[1]["payload"]["title"] == "Example"
    for update in ({"revision": 1}, {"revision": 2, "kind": "competitor"}, {"revision": 2, "product_id": "999"}):
        with pytest.raises(service.Conflict):
            save(source, record_id=first["record_id"], **update)
    other = snapshot("other")
    assert service.view("other")["records"] == []
    with pytest.raises(service.Conflict):
        save(other, record_id=first["record_id"], revision=2)


def test_stale_assessments_never_present_current_checks(snapshot):
    source = snapshot()
    first = save(source)
    newer = snapshot(stock=0)
    record = service.view("demo-ro")["records"][0]
    assert record["stale"] is True and record["assessment"]["metrics"] == {}
    assert all(c["status"] == "unknown" for c in record["assessment"]["checks"])
    assert record["historical_assessment"] == first["assessment"]
    with pytest.raises(service.Conflict):
        save(source)
    assert save(newer, record_id=first["record_id"], revision=1)["stale"] is False


def test_parallel_revision_updates_have_one_winner(snapshot):
    source = snapshot()
    first = save(source)

    def update(_):
        try:
            return save(source, record_id=first["record_id"], revision=1)["revision"]
        except service.Conflict:
            return "conflict"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(str(v) for v in pool.map(update, range(2))) == ["2", "conflict"]
    assert len(service.view("demo-ro")["records"]) == 2


def test_private_database(snapshot):
    from app.core.config import settings

    save(snapshot())
    assert (settings.data_dir / "emag-playbooks.sqlite3").stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_admin_api_validation_and_actor(snapshot):
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    from app.core.security import require_admin
    from app.routers.emag_operations import router

    source = snapshot()
    app = FastAPI()
    app.include_router(router, prefix="/api/emag")
    url = "/api/emag/stores/demo-ro/playbooks"
    payload = {
        "snapshot_id": source["snapshot_id"],
        "kind": "listing",
        "product_id": "1",
        "payload": {"title": "Example"},
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get(url)).status_code == 401
        assert (await client.post(url + "/records", json=payload)).status_code == 401
        app.dependency_overrides[require_admin] = lambda: "server-actor"
        assert (await client.get("/api/emag/stores/missing/playbooks")).status_code == 404
        assert (await client.post("/api/emag/stores/missing/playbooks/records", json=payload)).status_code == 404
        assert (await client.post(url + "/records", json={**payload, "actor": "forged"})).status_code == 422
        assert (
            await client.post(url + "/records", json={**payload, "payload": {"unexpected": True}})
        ).status_code == 422
        assert (await client.post(url + "/records", json={**payload, "product_id": "999"})).status_code == 409
        result = await client.post(url + "/records", json=payload)
        assert result.status_code == 200, result.text
        assert result.json()["actor"] == "server-actor"
        view = (await client.get(url)).json()
        assert view["marketplace_writes"] is False
        assert view["products"] == [{"product_id": "1", "name": "Example", "sku": "SKU", "stock": 2}]


def test_superseded_revisions_are_not_current_and_history_is_explicit(snapshot):
    source = snapshot()
    first = save(source)
    save(source, record_id=first["record_id"], revision=1)
    result = service.view("demo-ro")
    assert [r["current"] for r in result["records"]] == [True, False]
    assert result["records_truncated"] is False
    assert result["records_limit"] == 500


def test_history_cursor_keeps_global_current_identity(snapshot):
    source = snapshot()
    first = save(source)
    save(source, record_id=first["record_id"], revision=1)
    newest = service.view("demo-ro")["records"][0]
    older = service.view("demo-ro", before_sequence=newest["sequence"])
    assert len(older["records"]) == 1
    assert older["records"][0]["current"] is False
    assert older["records_next_before"] is None
    with pytest.raises(ValueError):
        service.view("demo-ro", before_sequence=0)
