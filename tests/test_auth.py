import importlib
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastmcp.server.auth.providers.jwt import RSAKeyPair
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

KEY = RSAKeyPair.generate()
KID = "test-key"


def public_jwk():
    from cryptography.hazmat.primitives import serialization
    import base64
    pem = KEY.public_key.get_secret_value() if hasattr(KEY.public_key, "get_secret_value") else KEY.public_key
    numbers = serialization.load_pem_public_key(pem.encode()).public_numbers()
    b64 = lambda n: base64.urlsafe_b64encode(n.to_bytes((n.bit_length() + 7) // 8, "big")).rstrip(b"=").decode()
    return {"kty": "RSA", "kid": KID, "use": "sig", "alg": "RS256", "n": b64(numbers.n), "e": b64(numbers.e)}
ISSUER = "https://auth.test"
AUTH_SERVER = "https://auth.test/sso"
MCP_BASE = "https://mcp.test"
RESOURCE = MCP_BASE + "/mcp"


class Upstream(BaseHTTPRequestHandler):
    """Serves the JWKS and a fake layer1 that records the forwarded Authorization header."""
    seen_auth = []

    def do_GET(self):
        if self.path == "/jwks.json":
            body = json.dumps({"keys": [public_jwk()]}).encode()
        else:
            Upstream.seen_auth.append(self.headers.get("Authorization"))
            body = b'{"orgs": []}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def upstream():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def load_server(monkeypatch, upstream, auth=True):
    monkeypatch.setenv("MMS_URL", upstream)
    if auth:
        monkeypatch.setenv("AUTH_ISSUER_URL", AUTH_SERVER)
        monkeypatch.setenv("MCP_BASE_URL", MCP_BASE)
        monkeypatch.setenv("JWKS_URL", upstream + "/jwks.json")
        monkeypatch.setenv("JWT_ISSUER", ISSUER)
    else:
        for name in ("AUTH_ISSUER_URL", "MCP_BASE_URL", "JWKS_URL", "JWT_ISSUER", "JWT_AUDIENCE"):
            monkeypatch.delenv(name, raising=False)
    import server
    return importlib.reload(server)


def token(audience=(("layer1-audience", RESOURCE)), issuer=ISSUER, expires_in=3600):
    return KEY.create_token(
        subject="alice", issuer=issuer, audience=list(audience), expires_in_seconds=expires_in, kid=KID,
        additional_claims={"username": "alice", "groups": ["engineers"]},
    )


def rpc(client, method, params=None, token_value=None, session=None, id_=1):
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if token_value:
        headers["Authorization"] = f"Bearer {token_value}"
    if session:
        headers["mcp-session-id"] = session
    payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if id_ is not None:
        payload["id"] = id_
    return client.post("/mcp", headers=headers, json=payload)


def parse(response):
    text = response.text
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        text = next(line[5:] for line in text.splitlines() if line.startswith("data:"))
    return json.loads(text)


def call_tool(client, token_value):
    init = rpc(client, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                      "clientInfo": {"name": "test", "version": "1"}}, token_value)
    assert init.status_code == 200, init.text
    session = init.headers.get("mcp-session-id")
    rpc(client, "notifications/initialized", token_value=token_value, session=session, id_=None)
    return rpc(client, "tools/call", {"name": "read_all_orgs", "arguments": {}}, token_value, session, id_=2)


def test_unauthenticated_request_gets_oauth_challenge(monkeypatch, upstream):
    server = load_server(monkeypatch, upstream)
    with TestClient(server.mcp.http_app(path="/mcp")) as client:
        response = rpc(client, "initialize")
        assert response.status_code == 401
        challenge = response.headers["www-authenticate"]
        assert "Bearer" in challenge and "resource_metadata=" in challenge


def test_protected_resource_metadata_points_at_auth_service(monkeypatch, upstream):
    server = load_server(monkeypatch, upstream)
    with TestClient(server.mcp.http_app(path="/mcp")) as client:
        response = client.get("/.well-known/oauth-protected-resource/mcp")
        assert response.status_code == 200
        body = response.json()
        assert body["resource"] == RESOURCE
        assert body["authorization_servers"] == [AUTH_SERVER + "/"] or body["authorization_servers"] == [AUTH_SERVER]


@pytest.mark.parametrize("bad", [
    token(audience=["layer1-audience"]),
    token(issuer="https://evil.test"),
    token(expires_in=-60),
    "not-a-jwt",
])
def test_invalid_tokens_are_rejected(monkeypatch, upstream, bad):
    server = load_server(monkeypatch, upstream)
    with TestClient(server.mcp.http_app(path="/mcp")) as client:
        assert rpc(client, "initialize", token_value=bad).status_code == 401


def test_valid_token_is_forwarded_unchanged_to_layer1(monkeypatch, upstream):
    server = load_server(monkeypatch, upstream)
    good = token()
    Upstream.seen_auth.clear()
    with TestClient(server.mcp.http_app(path="/mcp")) as client:
        result = parse(call_tool(client, good))
    assert result["result"]["isError"] is False, result
    assert Upstream.seen_auth == [f"Bearer {good}"]


def test_extra_audiences_accept_legacy_layer1_tokens(monkeypatch, upstream):
    monkeypatch.setenv("JWT_AUDIENCE", f"{RESOURCE},layer1-audience")
    server = load_server(monkeypatch, upstream)
    with TestClient(server.mcp.http_app(path="/mcp")) as client:
        assert call_tool(client, token(audience=["layer1-audience"])).status_code == 200


def test_without_auth_config_header_is_passed_through(monkeypatch, upstream):
    server = load_server(monkeypatch, upstream, auth=False)
    Upstream.seen_auth.clear()
    with TestClient(server.mcp.http_app(path="/mcp")) as client:
        result = parse(call_tool(client, "opaque-api-jwt"))
    assert result["result"]["isError"] is False, result
    assert Upstream.seen_auth == ["Bearer opaque-api-jwt"]
