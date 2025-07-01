"""
API endpoints for MCP integration
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog

from ..ai.continue_integration.mcp_bridge import MCPBridge

logger = structlog.get_logger()

router = APIRouter(prefix="/mcp", tags=["mcp"])

class MCPResourceRequest(BaseModel):
    uri: str

class MCPToolRequest(BaseModel):
    tool: str
    parameters: Dict[str, Any]

class MCPServer:
    """MCP Server endpoints for DevOpsZealot"""
    
    def __init__(self, zealot_engine):
        self.bridge = MCPBridge(zealot_engine)
        
    async def handle_resource(self, uri: str) -> Dict[str, Any]:
        """Handle MCP resource request"""
        try:
            return await self.bridge.handle_resource_request(uri)
        except Exception as e:
            logger.error(f"Resource request failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def handle_tool(self, tool: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tool request"""
        try:
            return await self.bridge.handle_tool_request(tool, parameters)
        except Exception as e:
            logger.error(f"Tool request failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Global instance (will be initialized with engine)
mcp_server: Optional[MCPServer] = None

@router.get("/resource")
async def get_resource(uri: str):
    """Get MCP resource by URI"""
    if not mcp_server:
        raise HTTPException(status_code=503, detail="MCP server not initialized")
    
    return await mcp_server.handle_resource(uri)

@router.post("/tool")
async def execute_tool(request: MCPToolRequest):
    """Execute MCP tool"""
    if not mcp_server:
        raise HTTPException(status_code=503, detail="MCP server not initialized")
    
    return await mcp_server.handle_tool(request.tool, request.parameters)

@router.get("/config")
async def get_mcp_config():
    """Get MCP configuration for Continue.dev"""
    if not mcp_server:
        raise HTTPException(status_code=503, detail="MCP server not initialized")
    
    return mcp_server.bridge.export_mcp_config()

def init_mcp_server(zealot_engine):
    """Initialize MCP server with zealot engine"""
    global mcp_server
    mcp_server = MCPServer(zealot_engine)
    logger.info("MCP server initialized")
