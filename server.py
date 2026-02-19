import os
from typing import Optional
import httpx
from fastmcp import FastMCP, Context

mcp = FastMCP("MMS Flexo Layer 1 Service")

MMS_URL = os.getenv("MMS_URL", "")
READ_ONLY = os.getenv("READ_ONLY", "true").lower() == "true"
MCPPATH = os.getenv("MCPPATH", "/mcp")

def get_auth_header(ctx: Context) -> dict:
    """Extract Authorization header from request context."""
    headers = ctx.request_context.request.headers
    auth_header = headers.get("authorization") or headers.get("Authorization")
    if auth_header:
        return {"Authorization": auth_header}
    return {}

async def make_request(
    method: str,
    path: str,
    ctx: Context,
    body: Optional[str] = None,
    content_type: Optional[str] = None
) -> str:
    """Make HTTP request to MMS API."""
    if not MMS_URL:
        raise ValueError("MMS_URL environment variable is not set")
    
    url = f"{MMS_URL.rstrip('/')}{path}"
    headers = get_auth_header(ctx)
    
    if content_type:
        headers["Content-Type"] = content_type
    
    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(url, headers=headers)
        elif method == "PUT":
            response = await client.put(url, headers=headers, content=body or "")
        elif method == "PATCH":
            response = await client.patch(url, headers=headers, content=body or "")
        elif method == "POST":
            response = await client.post(url, headers=headers, content=body or "")
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.text

def register_tools():
    @mcp.tool()
    async def read_all_orgs(ctx: Context) -> str:
        """Read all organizations."""
        return await make_request("GET", "/orgs", ctx)

    @mcp.tool()
    async def read_org(org_id: str, ctx: Context) -> str:
        """Read a specific organization.
        
        Args:
            org_id: The organization ID
        """
        return await make_request("GET", f"/orgs/{org_id}", ctx)

    @mcp.tool()
    async def read_all_repos(org_id: str, ctx: Context) -> str:
        """Read all repositories in an organization.
        
        Args:
            org_id: The organization ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos", ctx)

    @mcp.tool()
    async def read_repo(org_id: str, repo_id: str, ctx: Context) -> str:
        """Read a specific repository.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos/{repo_id}", ctx)

    @mcp.tool()
    async def read_all_branches(org_id: str, repo_id: str, ctx: Context) -> str:
        """Read all branches in a repository.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos/{repo_id}/branches", ctx)

    @mcp.tool()
    async def read_branch(org_id: str, repo_id: str, branch_id: str, ctx: Context) -> str:
        """Read a specific branch.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            branch_id: The branch ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos/{repo_id}/branches/{branch_id}", ctx)

    @mcp.tool()
    async def read_model(org_id: str, repo_id: str, branch_id: str, ctx: Context) -> str:
        """Read the model at the HEAD of a branch.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            branch_id: The branch ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos/{repo_id}/branches/{branch_id}/graph", ctx)

    @mcp.tool()
    async def query_model(org_id: str, repo_id: str, branch_id: str, sparql_query: str, ctx: Context) -> str:
        """Query the model at the HEAD of a branch.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            branch_id: The branch ID
            sparql_query: SPARQL 1.1 query string
        """
        return await make_request("POST", f"/orgs/{org_id}/repos/{repo_id}/branches/{branch_id}/query", ctx, sparql_query, "application/sparql-query")

    @mcp.tool()
    async def read_all_locks(org_id: str, repo_id: str, ctx: Context) -> str:
        """Read all locks in a repository.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos/{repo_id}/locks", ctx)

    @mcp.tool()
    async def read_lock(org_id: str, repo_id: str, lock_id: str, ctx: Context) -> str:
        """Read a specific lock.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            lock_id: The lock ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos/{repo_id}/locks/{lock_id}", ctx)

    @mcp.tool()
    async def query_lock(org_id: str, repo_id: str, lock_id: str, sparql_query: str, ctx: Context) -> str:
        """Query the model under the commit pointed to by the given lock.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            lock_id: The lock ID
            sparql_query: SPARQL 1.1 query string
        """
        return await make_request("POST", f"/orgs/{org_id}/repos/{repo_id}/locks/{lock_id}/query", ctx, sparql_query, "application/sparql-query")

    @mcp.tool()
    async def query_diff(org_id: str, repo_id: str, sparql_query: str, ctx: Context) -> str:
        """Query the given diff.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            sparql_query: SPARQL 1.1 query string
        """
        return await make_request("POST", f"/orgs/{org_id}/repos/{repo_id}/diff/query", ctx, sparql_query, "application/sparql-query")

    @mcp.tool()
    async def query_repo(org_id: str, repo_id: str, sparql_query: str, ctx: Context) -> str:
        """Query the metadata graph for the given repository.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            sparql_query: SPARQL 1.1 query string
        """
        return await make_request("POST", f"/orgs/{org_id}/repos/{repo_id}/query", ctx, sparql_query, "application/sparql-query")

    @mcp.tool()
    async def read_all_scratches(org_id: str, repo_id: str, ctx: Context) -> str:
        """Read all scratches in a repository.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos/{repo_id}/scratches", ctx)
    
    @mcp.tool()
    async def read_scratch(org_id: str, repo_id: str, scratch_id: str, ctx: Context) -> str:
        """Read a specific scratch.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            scratch_id: The scratch ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos/{repo_id}/scratches/{scratch_id}", ctx)

    @mcp.tool()
    async def query_scratch(org_id: str, repo_id: str, scratch_id: str, sparql_query: str, ctx: Context) -> str:
        """Query the model under the given scratch.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            scratch_id: The scratch ID
            sparql_query: SPARQL 1.1 query string
        """
        return await make_request("POST", f"/orgs/{org_id}/repos/{repo_id}/scratches/{scratch_id}/query", ctx, sparql_query, "application/sparql-query")
    
    @mcp.tool()
    async def read_scratch_model(org_id: str, repo_id: str, scratch_id: str, ctx: Context) -> str:
        """Read the model at the scratch.
        
        Args:
            org_id: The organization ID
            repo_id: The repository ID
            scratch_id: The scratch ID
        """
        return await make_request("GET", f"/orgs/{org_id}/repos/{repo_id}/scratches/{scratch_id}/graph", ctx)

    if not READ_ONLY:
        @mcp.tool()
        async def create_org(org_id: str, body: str, ctx: Context) -> str:
            """Create an organization.
            
            Args:
                org_id: The organization ID
                body: RDF content in Turtle format
            """
            return await make_request("PUT", f"/orgs/{org_id}", ctx, body, "text/turtle")

        @mcp.tool()
        async def update_org(org_id: str, body: str, ctx: Context) -> str:
            """Update an organization.
            
            Args:
                org_id: The organization ID
                body: RDF content in Turtle format
            """
            return await make_request("PATCH", f"/orgs/{org_id}", ctx, body, "text/turtle")

        @mcp.tool()
        async def create_repo(org_id: str, repo_id: str, body: str, ctx: Context) -> str:
            """Create a repository.
            
            Args:
                org_id: The organization ID
                repo_id: The repository ID
                body: RDF content in Turtle format
            """
            return await make_request("PUT", f"/orgs/{org_id}/repos/{repo_id}", ctx, body, "text/turtle")

        @mcp.tool()
        async def update_repo(org_id: str, repo_id: str, body: str, ctx: Context) -> str:
            """Update a repository.
            
            Args:
                org_id: The organization ID
                repo_id: The repository ID
                body: RDF content in Turtle format
            """
            return await make_request("PATCH", f"/orgs/{org_id}/repos/{repo_id}", ctx, body, "text/turtle")

        @mcp.tool()
        async def create_branch(org_id: str, repo_id: str, branch_id: str, body: str, ctx: Context) -> str:
            """Create a branch.
            
            Args:
                org_id: The organization ID
                repo_id: The repository ID
                branch_id: The branch ID
                body: RDF content in Turtle format
            """
            return await make_request("PUT", f"/orgs/{org_id}/repos/{repo_id}/branches/{branch_id}", ctx, body, "text/turtle")

        @mcp.tool()
        async def update_branch(org_id: str, repo_id: str, branch_id: str, body: str, ctx: Context) -> str:
            """Update a branch.
            
            Args:
                org_id: The organization ID
                repo_id: The repository ID
                branch_id: The branch ID
                body: RDF content in Turtle format
            """
            return await make_request("PATCH", f"/orgs/{org_id}/repos/{repo_id}/branches/{branch_id}", ctx, body, "text/turtle")

        @mcp.tool()
        async def load_model(org_id: str, repo_id: str, branch_id: str, rdf_content: str, ctx: Context) -> str:
            """Replace the model at the HEAD of a branch by uploading an RDF file.
            
            Args:
                org_id: The organization ID
                repo_id: The repository ID
                branch_id: The branch ID
                rdf_content: RDF content to load in turtle format
            """
            return await make_request("PUT", f"/orgs/{org_id}/repos/{repo_id}/branches/{branch_id}/graph", ctx, rdf_content, "text/turtle")

        @mcp.tool()
        async def commit_model(org_id: str, repo_id: str, branch_id: str, sparql_update: str, ctx: Context) -> str:
            """Commit a change to the model by applying a SPARQL UPDATE.
            
            Args:
                org_id: The organization ID
                repo_id: The repository ID
                branch_id: The branch ID
                sparql_update: SPARQL 1.1 update string
            """
            return await make_request("POST", f"/orgs/{org_id}/repos/{repo_id}/branches/{branch_id}/update", ctx, sparql_update, "application/sparql-update")

        @mcp.tool()
        async def create_lock(org_id: str, repo_id: str, lock_id: str, sparql_update: str, ctx: Context) -> str:
            """Create a lock.
            
            Args:
                org_id: The organization ID
                repo_id: The repository ID
                lock_id: The lock ID
                sparql_update: SPARQL 1.1 update string
            """
            return await make_request("PUT", f"/orgs/{org_id}/repos/{repo_id}/locks/{lock_id}", ctx, sparql_update, "application/sparql-update")

        @mcp.tool()
        async def create_diff(org_id: str, repo_id: str, sparql_query: str, ctx: Context) -> str:
            """Create a diff between two commits.
            
            Args:
                org_id: The organization ID
                repo_id: The repository ID
                sparql_query: SPARQL 1.1 query string
            """
            return await make_request("POST", f"/orgs/{org_id}/repos/{repo_id}/diff", ctx, sparql_query, "application/sparql-query")

        @mcp.tool()
        async def create_collection(org_id: str, collection_id: str, body: str, ctx: Context) -> str:
            """Create a collection.
            
            Args:
                org_id: The organization ID
                collection_id: The collection ID
                body: RDF content in Turtle format
            """
            return await make_request("PUT", f"/orgs/{org_id}/collections/{collection_id}", ctx, body, "text/turtle")

        @mcp.tool()
        async def create_policy(policy_id: str, body: str, ctx: Context) -> str:
            """Create a policy.
            
            Args:
                policy_id: The policy ID
                body: RDF content in Turtle format
            """
            return await make_request("PUT", f"/policies/{policy_id}", ctx, body, "text/turtle")

        @mcp.tool()
        async def create_group(group_id: str, body: str, ctx: Context) -> str:
            """Create a group.
            
            Args:
                group_id: The group ID
                body: RDF content in Turtle format
            """
            return await make_request("PUT", f"/groups/{group_id}", ctx, body, "text/turtle")

register_tools()

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path=MCPPATH)
