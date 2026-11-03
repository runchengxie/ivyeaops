"""Compatibility boundaries retained when porting upstream reliability fixes."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request


def test_agent_errors_are_strings_without_changing_other_api_contracts():
    from app.main import _error_body

    for path in ("/api/agents/missing", "/api/emag/missing"):
        request = Request({"type": "http", "path": path, "headers": []})
        request.state.request_id = "test-id"
        body = _error_body(request, 404, "Missing")
        assert body["detail"] == "Missing"
        if path.startswith("/api/agents/"):
            assert body["error"] == "Missing"
            assert body["error_info"]["request_id"] == "test-id"
        else:
            assert body["error"]["code"] == "NOT_FOUND"


def test_plugin_stub_lists_empty_and_rejects_mutations():
    from app.agents.router import api_router

    app = FastAPI()
    app.include_router(api_router, prefix="/api/agents")
    client = TestClient(app)
    assert client.get("/api/agents/plugins").json() == {"plugins": []}
    response = client.post("/api/agents/plugins/install", json={"url": "unused"})
    assert response.status_code == 501
    assert isinstance(response.json()["error"], str)


def test_plugin_methods_have_distinct_openapi_operation_ids():
    from app.agents.routers.plugins import router

    app = FastAPI()
    app.include_router(router, prefix="/plugins")
    operations = app.openapi()["paths"]["/plugins/{rest}"]
    identifiers = [operation["operationId"] for operation in operations.values()]
    assert len(identifiers) == len(set(identifiers))
