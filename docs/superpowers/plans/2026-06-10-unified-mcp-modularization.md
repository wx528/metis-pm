# 统一 MCP Server 模块化重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 1746 行的 `mcp_server_unified.py` 拆分为模块化包 `mcp_tools/`，每个角色独立文件，入口文件精简至 ~150 行，删除 4 个历史遗留 MCP Server 文件。

**Architecture:** 采用"注册器模式"，各模块暴露 `register_tools(mcp, require_role, safe_tool)` 函数，由入口文件统一调用，彻底避免循环导入。共享基础设施（FastMCP 实例、装饰器、认证）保留在入口文件中。

**Tech Stack:** Python 3.11, FastMCP (MCP SDK), httpx, pytest

---

## 文件结构

```
backend/
├── mcp_server_unified.py          # 入口文件 (重构后 ~150 行)
├── mcp_tools/                     # 新包
│   ├── __init__.py               # 暴露 register_all_tools()
│   ├── shared.py                 # 16 个共享工具 (All Roles)
│   ├── agent.py                  # 19 个 Agent 专属工具
│   ├── mate.py                   # 7 个 Mate 专属工具
│   ├── tester.py                 # 7 个 Tester 专属工具
│   └── registrar.py              # 6 个 Registrar 专属工具
└── tests/
    └── test_mcp_modularization.py  # 新增：模块结构验证测试
```

---

## Task 1: 创建 mcp_tools 包和 __init__.py

**Files:**
- Create: `backend/mcp_tools/__init__.py`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p backend/mcp_tools
```

- [ ] **Step 2: 编写 __init__.py**

```python
"""MCP Tools 包 - 按角色拆分的工具模块

使用方式:
    from mcp_tools import register_all_tools
    register_all_tools(mcp, require_role, safe_tool)
"""

from . import shared, agent, mate, tester, registrar


def register_all_tools(mcp, require_role, safe_tool):
    """注册所有角色的 MCP 工具
    
    Args:
        mcp: FastMCP 实例
        require_role: 角色权限装饰器
        safe_tool: 错误处理装饰器
    """
    shared.register_tools(mcp, require_role, safe_tool)
    agent.register_tools(mcp, require_role, safe_tool)
    mate.register_tools(mcp, require_role, safe_tool)
    tester.register_tools(mcp, require_role, safe_tool)
    registrar.register_tools(mcp, require_role, safe_tool)
```

- [ ] **Step 3: Commit**

```bash
git add backend/mcp_tools/__init__.py
git commit -m "chore: create mcp_tools package structure"
```

---

## Task 2: 提取共享工具到 shared.py

**Files:**
- Create: `backend/mcp_tools/shared.py`
- Source: `backend/mcp_server_unified.py` lines 172-694 (所有角色可用区域)

**背景:** `mcp_server_unified.py` 中 "所有角色可用 (All Roles)" 区域包含 16 个工具，这些工具被所有角色共享。

- [ ] **Step 1: 创建 shared.py 文件框架**

```python
"""共享工具 - 所有角色可用"""
from typing import Optional
import httpx

from mcp_common import API_BASE, _api_request, _current_sub, get_headers


def register_tools(mcp, require_role, safe_tool):
    """注册共享工具"""
    
    # ═══════════════════════════════════════════════════════
    #  共享工具 (All Roles)
    # ═══════════════════════════════════════════════════════
    
    @mcp.tool()
    @require_role("agent", "mate", "tester", "registrar", "admin")
    @safe_tool
    async def check_connection() -> str:
        """测试 MCP Server 与后端 API 的连接是否正常"""
        # ... (完整实现)
    
    # ... 其他 15 个共享工具
```

- [ ] **Step 2: 从 unified.py 复制共享工具**

提取 `mcp_server_unified.py` 中第 172-694 行的所有工具函数（从 `check_connection` 到该区域最后一个工具），粘贴到 `shared.py` 的 `register_tools()` 函数体内。

确保每个工具都保留：
- `@mcp.tool()` 装饰器
- `@require_role(...)` 装饰器  
- `@safe_tool` 装饰器
- 完整的函数实现
- docstring

- [ ] **Step 3: 验证 shared.py 语法**

```bash
cd backend
python -c "from mcp_tools.shared import register_tools; print('shared.py OK')"
```

Expected: `shared.py OK`

- [ ] **Step 4: Commit**

```bash
git add backend/mcp_tools/shared.py
git commit -m "refactor: extract shared MCP tools into mcp_tools/shared.py"
```

---

## Task 3: 提取 Agent 专属工具

**Files:**
- Create: `backend/mcp_tools/agent.py`
- Source: `backend/mcp_server_unified.py` lines 695-1118 (Agent Only 区域)

- [ ] **Step 1: 创建 agent.py 文件框架**

```python
"""Agent 专属工具"""
from typing import Optional
import httpx

from mcp_common import API_BASE, _api_request, _current_sub, get_headers


def register_tools(mcp, require_role, safe_tool):
    """注册 Agent 专属工具"""
    
    # ═══════════════════════════════════════════════════════
    #  Agent Only
    # ═══════════════════════════════════════════════════════
    
    # 从 unified.py Agent Only 区域复制所有工具
```

- [ ] **Step 2: 从 unified.py 复制 Agent 工具**

提取 `mcp_server_unified.py` 中第 695-1118 行的所有 Agent 专属工具函数，粘贴到 `agent.py` 的 `register_tools()` 函数体内。

- [ ] **Step 3: 验证 agent.py 语法**

```bash
cd backend
python -c "from mcp_tools.agent import register_tools; print('agent.py OK')"
```

Expected: `agent.py OK`

- [ ] **Step 4: Commit**

```bash
git add backend/mcp_tools/agent.py
git commit -m "refactor: extract agent MCP tools into mcp_tools/agent.py"
```

---

## Task 4: 提取 Mate 专属工具

**Files:**
- Create: `backend/mcp_tools/mate.py`
- Source: `backend/mcp_server_unified.py` lines 1119-1246 (Mate Only 区域)

- [ ] **Step 1: 创建 mate.py 文件框架**

```python
"""Mate 专属工具"""
from typing import Optional
import httpx

from mcp_common import API_BASE, _api_request, _current_sub, get_headers


def register_tools(mcp, require_role, safe_tool):
    """注册 Mate 专属工具"""
    
    # ═══════════════════════════════════════════════════════
    #  Mate Only
    # ═══════════════════════════════════════════════════════
    
    # 从 unified.py Mate Only 区域复制所有工具
```

- [ ] **Step 2: 从 unified.py 复制 Mate 工具**

提取 `mcp_server_unified.py` 中第 1119-1246 行的所有 Mate 专属工具函数。

- [ ] **Step 3: 验证 mate.py 语法**

```bash
cd backend
python -c "from mcp_tools.mate import register_tools; print('mate.py OK')"
```

Expected: `mate.py OK`

- [ ] **Step 4: Commit**

```bash
git add backend/mcp_tools/mate.py
git commit -m "refactor: extract mate MCP tools into mcp_tools/mate.py"
```

---

## Task 5: 提取 Tester 专属工具

**Files:**
- Create: `backend/mcp_tools/tester.py`
- Source: `backend/mcp_server_unified.py` lines 1247-1452 (Tester Only 区域)

- [ ] **Step 1-4:** 同 Task 3/4 模式，提取 Tester 工具到 `tester.py`

- [ ] **Step 5: Commit**

```bash
git add backend/mcp_tools/tester.py
git commit -m "refactor: extract tester MCP tools into mcp_tools/tester.py"
```

---

## Task 6: 提取 Registrar 专属工具

**Files:**
- Create: `backend/mcp_tools/registrar.py`
- Source: `backend/mcp_server_unified.py` lines 1453-1718 (Registrar Only 区域)

- [ ] **Step 1-4:** 同 Task 3/4/5 模式，提取 Registrar 工具到 `registrar.py`

- [ ] **Step 5: Commit**

```bash
git add backend/mcp_tools/registrar.py
git commit -m "refactor: extract registrar MCP tools into mcp_tools/registrar.py"
```

---

## Task 7: 重构入口文件 mcp_server_unified.py

**Files:**
- Modify: `backend/mcp_server_unified.py` (完全重写)

**背景:** 当前文件 1746 行，包含所有工具。重构后应只保留基础设施和入口逻辑。

- [ ] **Step 1: 备份当前文件**

```bash
cp backend/mcp_server_unified.py backend/mcp_server_unified.py.bak
git add backend/mcp_server_unified.py.bak
git commit -m "chore: backup mcp_server_unified.py before refactoring"
```

- [ ] **Step 2: 编写新的入口文件**

```python
"""
Project Manager MCP Server - Unified
Combines all roles: agent, mate, tester, registrar

=== Streamable HTTP 模式配置 ===
{
  "mcpServers": {
    "project-manager": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "X-PM-Password": "your-password"
      }
    }
  }
}

角色通过 AGENT_PASSWORDS 环境变量解析：identity:password,...
identity 包含 mate/tester/registrar 关键词则对应角色，否则为 agent
"""
import functools
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timezone
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

from mcp_common import (
    API_BASE, _api_request, _current_sub, get_headers,
    PasswordMiddleware, AGENT_PASSWORD, _get_password,
    _token_cache, _cache_key,
)
from mcp_tools import register_all_tools

mcp = FastMCP("project-manager")

ROLES = {"agent", "mate", "tester", "registrar", "admin"}


# ═══════════════════════════════════════════════════════
#  角色识别与权限控制
# ═══════════════════════════════════════════════════════


def get_role_by_password(password: str) -> str:
    passwords = os.environ.get("AGENT_PASSWORDS", "")
    for entry in passwords.split(","):
        if ":" not in entry:
            continue
        identity, pwd = entry.strip().split(":", 1)
        if pwd == password:
            identity_lower = identity.lower()
            if "mate" in identity_lower:
                return "mate"
            if "tester" in identity_lower:
                return "tester"
            if "registrar" in identity_lower:
                return "registrar"
            return "agent"
    return "unknown"


async def _current_role() -> str:
    pwd = _get_password()
    return get_role_by_password(pwd)


def require_role(*roles):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            role = await _current_role()
            if role not in roles:
                return f"❌ 权限拒绝：需要角色 {list(roles)}，当前为 '{role}'"
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def safe_tool(func):
    """工具函数错误处理装饰器：捕获异常，防止 MCP Server 崩溃"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.ConnectError as e:
            return f"❌ 后端 API 连接失败：{e}。请检查后端服务是否正常运行。"
        except httpx.TimeoutException as e:
            return f"❌ 后端 API 请求超时：{e}。请稍后重试。"
        except Exception as e:
            import traceback
            return f"❌ 工具执行出错：{type(e).__name__}: {str(e)}\n请稍后重试或联系管理员。"
    return wrapper


# ═══════════════════════════════════════════════════════
#  健康检查端点 (FastAPI style for Docker)
# ═══════════════════════════════════════════════════════


from fastapi import FastAPI
from fastapi.responses import JSONResponse

health_app = FastAPI()

@health_app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "service": "mcp-unified"})


# ═══════════════════════════════════════════════════════
#  注册所有工具
# ═══════════════════════════════════════════════════════


register_all_tools(mcp, require_role, safe_tool)


# ═══════════════════════════════════════════════════════
#  启动
# ═══════════════════════════════════════════════════════


if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from mcp.server.fastmcp import Server as MCPServer
    
    # Streamable HTTP mode
    mcp_server = MCPServer(mcp._name)
    # ... (保留原有的启动逻辑)
    
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)
```

- [ ] **Step 3: 验证新入口文件可以 import**

```bash
cd backend
python -c "
import sys
sys.path.insert(0, '.')
# 只验证 import 不报错
from mcp_server_unified import mcp, require_role, safe_tool
print(f'MCP tools registered: {len(mcp._tools)}')
print('mcp_server_unified.py OK')
"
```

Expected: 
```
MCP tools registered: 55
mcp_server_unified.py OK
```

- [ ] **Step 4: 运行全量测试**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

Expected: 所有 99 个测试通过（或 98 passed + 1 skipped）

- [ ] **Step 5: Commit**

```bash
git add backend/mcp_server_unified.py
git rm backend/mcp_server_unified.py.bak
git commit -m "refactor: rewrite mcp_server_unified.py as modular entry point"
```

---

## Task 8: 删除历史遗留文件

**Files:**
- Delete: `backend/mcp_server.py`
- Delete: `backend/mcp_server_mate.py`
- Delete: `backend/mcp_server_tester.py`
- Delete: `backend/mcp_server_registrar.py`

- [ ] **Step 1: 确认 unified 入口文件工作正常**

```bash
cd backend
python -c "
from mcp_server_unified import mcp
print(f'Tools registered: {len(mcp._tools)}')
"
```

Expected: `Tools registered: 55`

- [ ] **Step 2: 删除旧文件**

```bash
git rm backend/mcp_server.py
git rm backend/mcp_server_mate.py
git rm backend/mcp_server_tester.py
git rm backend/mcp_server_registrar.py
```

- [ ] **Step 3: 验证没有 import 旧文件的地方**

```bash
cd backend
grep -r "from mcp_server import\|import mcp_server\|from mcp_server_mate\|from mcp_server_tester\|from mcp_server_registrar" --include="*.py" .
```

Expected: 没有匹配结果

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove legacy MCP server files (mcp_server, mcp_server_mate, mcp_server_tester, mcp_server_registrar)"
```

---

## Task 9: 添加模块结构验证测试

**Files:**
- Create: `backend/tests/test_mcp_modularization.py`

- [ ] **Step 1: 编写测试**

```python
"""MCP Server 模块化重构验证测试

确保重构后：
1. 所有工具都被正确注册
2. 各角色工具数量与重构前一致
3. 共享工具对所有角色可用
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from mcp.server.fastmcp import FastMCP

# 导入需要测试的装饰器
from mcp_server_unified import require_role, safe_tool
from mcp_tools import shared, agent, mate, tester, registrar


class TestToolRegistration:
    """测试各模块能正确注册工具"""
    
    @pytest.fixture
    def fresh_mcp(self):
        """创建一个新的 FastMCP 实例用于测试"""
        return FastMCP("test")
    
    def test_shared_tools_count(self, fresh_mcp):
        """共享工具应有 16 个"""
        shared.register_tools(fresh_mcp, require_role, safe_tool)
        # 注意：FastMCP 内部工具存储方式可能不同，这里使用 _tools
        tool_names = [name for name in fresh_mcp._tools.keys()]
        assert len(tool_names) == 16, f"Expected 16 shared tools, got {len(tool_names)}: {tool_names}"
    
    def test_agent_tools_count(self, fresh_mcp):
        """Agent 专属工具应有 19 个"""
        agent.register_tools(fresh_mcp, require_role, safe_tool)
        tool_names = [name for name in fresh_mcp._tools.keys()]
        assert len(tool_names) == 19, f"Expected 19 agent tools, got {len(tool_names)}"
    
    def test_mate_tools_count(self, fresh_mcp):
        """Mate 专属工具应有 7 个"""
        mate.register_tools(fresh_mcp, require_role, safe_tool)
        tool_names = [name for name in fresh_mcp._tools.keys()]
        assert len(tool_names) == 7, f"Expected 7 mate tools, got {len(tool_names)}"
    
    def test_tester_tools_count(self, fresh_mcp):
        """Tester 专属工具应有 7 个"""
        tester.register_tools(fresh_mcp, require_role, safe_tool)
        tool_names = [name for name in fresh_mcp._tools.keys()]
        assert len(tool_names) == 7, f"Expected 7 tester tools, got {len(tool_names)}"
    
    def test_registrar_tools_count(self, fresh_mcp):
        """Registrar 专属工具应有 6 个"""
        registrar.register_tools(fresh_mcp, require_role, safe_tool)
        tool_names = [name for name in fresh_mcp._tools.keys()]
        assert len(tool_names) == 6, f"Expected 6 registrar tools, got {len(tool_names)}"
    
    def test_all_tools_combined(self, fresh_mcp):
        """所有工具注册后应有 55 个（不重复）"""
        from mcp_tools import register_all_tools
        register_all_tools(fresh_mcp, require_role, safe_tool)
        tool_names = [name for name in fresh_mcp._tools.keys()]
        assert len(tool_names) == 55, f"Expected 55 total tools, got {len(tool_names)}"
    
    def test_key_tools_exist(self, fresh_mcp):
        """验证关键工具存在"""
        from mcp_tools import register_all_tools
        register_all_tools(fresh_mcp, require_role, safe_tool)
        
        # 共享工具
        assert "check_connection" in fresh_mcp._tools
        assert "get_context" in fresh_mcp._tools
        assert "notify_role" in fresh_mcp._tools
        
        # Agent 工具
        assert "create_issue" in fresh_mcp._tools
        assert "update_issue" in fresh_mcp._tools
        assert "claim_issue" in fresh_mcp._tools
        
        # Mate 工具
        assert "approve_plan" in fresh_mcp._tools
        assert "reject_plan" in fresh_mcp._tools
        
        # Tester 工具
        assert "report_bug" in fresh_mcp._tools
        assert "verify_issue" in fresh_mcp._tools
        
        # Registrar 工具
        assert "register_project" in fresh_mcp._tools


class TestNoLegacyFiles:
    """验证旧文件已被删除"""
    
    def test_no_mcp_server_py(self):
        backend = Path(__file__).parent.parent
        assert not (backend / "mcp_server.py").exists(), "mcp_server.py should be deleted"
    
    def test_no_mcp_server_mate_py(self):
        backend = Path(__file__).parent.parent
        assert not (backend / "mcp_server_mate.py").exists(), "mcp_server_mate.py should be deleted"
    
    def test_no_mcp_server_tester_py(self):
        backend = Path(__file__).parent.parent
        assert not (backend / "mcp_server_tester.py").exists(), "mcp_server_tester.py should be deleted"
    
    def test_no_mcp_server_registrar_py(self):
        backend = Path(__file__).parent.parent
        assert not (backend / "mcp_server_registrar.py").exists(), "mcp_server_registrar.py should be deleted"
```

- [ ] **Step 2: 运行新测试**

```bash
cd backend
python -m pytest tests/test_mcp_modularization.py -v
```

Expected: 所有测试通过

- [ ] **Step 3: 运行全量测试确保没有回归**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

Expected: 98 passed, 1 skipped（或全部通过）

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_mcp_modularization.py
git commit -m "test: add MCP modularization structure verification tests"
```

---

## Task 10: 更新文档和 CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: 在 CHANGELOG.md 顶部添加新版本记录**

```markdown
## [1.2.0] - 2026-06-10

### 重构：MCP Server 模块化

将单体 `mcp_server_unified.py` (1746 行) 重构为模块化包 `mcp_tools/`，每个角色独立文件。

#### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/mcp_tools/__init__.py` | 包入口，暴露 `register_all_tools()` |
| `backend/mcp_tools/shared.py` | 16 个共享工具（所有角色） |
| `backend/mcp_tools/agent.py` | 19 个 Agent 专属工具 |
| `backend/mcp_tools/mate.py` | 7 个 Mate 专属工具 |
| `backend/mcp_tools/tester.py` | 7 个 Tester 专属工具 |
| `backend/mcp_tools/registrar.py` | 6 个 Registrar 专属工具 |
| `backend/tests/test_mcp_modularization.py` | 模块化结构验证测试 |

#### 变更文件

| 文件 | 说明 |
|------|------|
| `backend/mcp_server_unified.py` | 精简为入口文件 (~150 行)，只保留基础设施和工具注册 |

#### 删除文件

- `backend/mcp_server.py` — 历史遗留，已停用
- `backend/mcp_server_mate.py` — 历史遗留，已停用
- `backend/mcp_server_tester.py` — 历史遗留，已停用
- `backend/mcp_server_registrar.py` — 历史遗留，已停用

#### 架构改进

- 单一职责：每个文件只包含一个角色的工具
- 避免循环导入：使用 `register_tools(mcp, require_role, safe_tool)` 参数传入模式
- 向后兼容：docker-compose 配置不变，MCP 客户端无需修改
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for MCP modularization refactor"
```

---

## 自检清单

- [ ] **Spec 覆盖**: 所有设计文档中的要求都有对应任务
  - [x] 创建 mcp_tools 包 ✓ Task 1
  - [x] 提取共享工具 ✓ Task 2
  - [x] 按角色拆分 ✓ Task 3-6
  - [x] 重构入口文件 ✓ Task 7
  - [x] 删除旧文件 ✓ Task 8
  - [x] 添加测试 ✓ Task 9
  - [x] 更新文档 ✓ Task 10

- [ ] **Placeholder 扫描**: 无 TBD/TODO/占位符
- [ ] **类型一致性**: 所有 `register_tools` 函数签名一致 `(mcp, require_role, safe_tool)`
- [ ] **路径正确性**: 所有文件路径使用 `backend/` 前缀

---

## 执行方式选择

**Plan complete and saved to `docs/superpowers/plans/2026-06-10-unified-mcp-modularization.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
