"""MCP Tools 包 - 按角色拆分的工具模块

使用方式:
    from mcp_tools import register_all_tools
    register_all_tools(mcp, require_role, safe_tool)
"""


def register_all_tools(mcp, require_role, safe_tool):
    """注册所有角色的 MCP 工具
    
    Args:
        mcp: FastMCP 实例
        require_role: 角色权限装饰器
        safe_tool: 错误处理装饰器
    """
    from . import shared, agent, mate, tester, registrar
    
    shared.register_tools(mcp, require_role, safe_tool)
    agent.register_tools(mcp, require_role, safe_tool)
    mate.register_tools(mcp, require_role, safe_tool)
    tester.register_tools(mcp, require_role, safe_tool)
    registrar.register_tools(mcp, require_role, safe_tool)
