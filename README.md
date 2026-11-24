# MMS Flexo Layer 1 MCP Server

A Model Context Protocol (MCP) server that provides a FastMCP-based interface to the MMS5 (Model Management System) Layer 1 Service. This server exposes MMS operations as MCP tools, enabling AI assistants and other MCP clients to interact with MMS repositories, branches, models, and access control resources.

## Overview

This MCP server wraps the MMS5 Layer 1 REST API, providing tools for:

- **Structural Operations**: Read and manage organizations, repositories, and branches
- **Model Operations**: Read, load, query, and commit changes to RDF models using SPARQL
- **Version Control**: Manage locks and diffs between commits
- **Access Control**: Create and manage policies, groups, and collections

The server supports a **read-only mode** via the `READ_ONLY` environment variable, which restricts available tools to only read and query operations.

## Features

- **Conditional Tool Registration**: When `READ_ONLY=true`, only read and query operations are available
- **Per-user OAuth**: Optional OAuth 2.1 resource server backed by the Flexo MMS SSO auth service; validated user tokens are forwarded to the MMS API
- **Authentication Passthrough**: Without OAuth configured, forwards `Authorization` headers from MCP requests to the MMS API
- **FastMCP Framework**: Built on FastMCP for streamable HTTP transport
- **RDF/SPARQL Support**: Works with Turtle-formatted RDF and SPARQL 1.1 queries/updates

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MMS_URL` | Base URL of the MMS Layer 1 API | `http://localhost:8080` | Yes |
| `READ_ONLY` | Enable read-only mode (only read/query tools) | `true` | No |
| `MCPPATH` | Path the MCP endpoint is served on | `/mcp` | No |
| `AUTH_ISSUER_URL` | Public URL of the SSO auth service (OAuth issuer, including context path). Enables OAuth when set | - | No |
| `MCP_BASE_URL` | Public base URL of this server; `MCP_BASE_URL` + `MCPPATH` is the OAuth resource | - | With OAuth |
| `JWKS_URL` | JWKS used to verify tokens | `AUTH_ISSUER_URL/.well-known/jwks.json` | No |
| `JWT_ISSUER` | Expected `iss` claim; must equal the auth service's `JWT_DOMAIN` | `AUTH_ISSUER_URL` | No |
| `JWT_AUDIENCE` | Comma-separated accepted audiences (any match) | `MCP_BASE_URL` + `MCPPATH` | No |

## Docker

### Building the Image

```bash
docker build -t flexo-mms-layer1-mcp .
```

### Running the Container

Run with custom MMS URL:

```bash
docker run -d \
  -p 8000:8000 \
  -e MMS_URL=https://your-flexo-mms-server \
  flexo-mms-layer1-mcp
```

Run in read-write mode (enables create/update/delete operations):

```bash
docker run -d \
  -p 8000:8000 \
  -e MMS_URL=https://your-mms-server \
  -e READ_ONLY=false \
  flexo-mms-layer1-mcp
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MMS_URL=http://mms-api:8080
      - READ_ONLY=true
```

## Local Development

### Prerequisites

- Python 3.13+
- pip

### Installation

```bash
pip install -r requirements.txt
```

### Running Locally

```bash
export MMS_URL=http://localhost:8080
export READ_ONLY=false
python server.py
```

The server will start on `http://0.0.0.0:8000` using FastMCP's streamable HTTP transport.

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Available Tools

### Read Operations (Always Available)

- `read_all_orgs` - List all organizations
- `read_org` - Get a specific organization
- `read_all_repos` - List repositories in an organization
- `read_repo` - Get a specific repository
- `read_all_branches` - List branches in a repository
- `read_branch` - Get a specific branch
- `read_model` - Read the model at the HEAD of a branch
- `query_model` - Query a branch's model with SPARQL
- `read_all_locks` - List locks in a repository
- `read_lock` - Get a specific lock
- `query_lock` - Query the model at a locked commit
- `query_diff` - Query a diff between commits
- `query_repo` - Query repository metadata

### Write Operations (Only when `READ_ONLY=false`)

- `create_org`, `update_org` - Create/update organizations
- `create_repo`, `update_repo` - Create/update repositories
- `create_branch`, `update_branch` - Create/update branches
- `load_model` - Replace a branch's model with new RDF content
- `commit_model` - Apply SPARQL UPDATE to commit changes
- `create_lock` - Create a lock on a commit
- `create_diff` - Create a diff between commits
- `create_collection` - Create a collection
- `create_policy` - Create an access control policy
- `create_group` - Create a user group

## Authentication

### Per-user OAuth (recommended)

Set `AUTH_ISSUER_URL` and `MCP_BASE_URL` to make this server an OAuth 2.1 protected resource that uses the [Flexo MMS SSO auth service](https://github.com/Open-MBEE/flexo-mms-sso-auth-service) as its authorization server:

1. An unauthenticated MCP request gets `401` with a `WWW-Authenticate` header pointing at `/.well-known/oauth-protected-resource/mcp`, which names the auth service.
2. The MCP client runs the authorization code + PKCE flow against the auth service; the user signs in with the configured SSO.
3. The client calls this server with `Authorization: Bearer <jwt>`. The token's RS256 signature (via JWKS), issuer, expiry and audience are checked.
4. The same token is forwarded to layer1, which accepts it because it also carries the layer1 audience and the same `username`/`groups` claims as API-key tokens.

The auth service must sign with RS256 and list `MCP_BASE_URL` + `MCPPATH` in `FLEXO_OAUTH_RESOURCES`, and the MCP client must be registered there (client id/secret, public client, or a Client ID Metadata Document). To also accept tokens from the auth service's API-key `/login`, add the layer1 audience to `JWT_AUDIENCE`.

```bash
docker run -p 8000:8000 \
  -e MMS_URL=https://example.org/layer1 \
  -e AUTH_ISSUER_URL=https://example.org/sso \
  -e MCP_BASE_URL=https://example.org \
  -e JWT_ISSUER=https://example.org/ \
  flexo-mms-layer1-mcp
```

### Passthrough

When `AUTH_ISSUER_URL` is unset the server performs no validation and forwards the `Authorization` header from incoming MCP requests to the MMS API as-is; layer1 still validates it.

## License

Apache 2.0
