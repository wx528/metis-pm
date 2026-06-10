"""Tests for MCP Server modularization.

Verifies that the unified MCP server has been properly split into role-based modules.
"""
import ast
import inspect
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).parent.parent


class TestMCPModularization:
    """Test suite for MCP server modularization."""

    def test_entry_point_exists_and_is_small(self):
        """Entry point should exist and be under 150 lines."""
        entry_file = BACKEND_DIR / "mcp_server_unified.py"
        assert entry_file.exists(), "mcp_server_unified.py should exist"
        lines = entry_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 150, f"Entry point is {len(lines)} lines, should be <= 150"

    def test_legacy_files_deleted(self):
        """Legacy role-specific MCP server files should be deleted."""
        legacy_files = [
            "mcp_server.py",
            "mcp_server_mate.py",
            "mcp_server_tester.py",
            "mcp_server_registrar.py",
        ]
        for filename in legacy_files:
            filepath = BACKEND_DIR / filename
            assert not filepath.exists(), f"Legacy file {filename} should be deleted"

    def test_mcp_tools_package_exists(self):
        """mcp_tools package should exist with all modules."""
        tools_dir = BACKEND_DIR / "mcp_tools"
        assert tools_dir.exists(), "mcp_tools/ directory should exist"
        assert tools_dir.is_dir(), "mcp_tools should be a directory"

        expected_files = ["__init__.py", "shared.py", "agent.py", "mate.py", "tester.py", "registrar.py"]
        for filename in expected_files:
            filepath = tools_dir / filename
            assert filepath.exists(), f"mcp_tools/{filename} should exist"

    def test_all_modules_have_register_tools(self):
        """Each role module should have a register_tools function."""
        modules = ["shared", "agent", "mate", "tester", "registrar"]
        for module_name in modules:
            filepath = BACKEND_DIR / "mcp_tools" / f"{module_name}.py"
            content = filepath.read_text(encoding="utf-8")
            tree = ast.parse(content)

            func_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            assert "register_tools" in func_names, f"{module_name}.py should have register_tools function"

    def test_entry_point_imports_register_all_tools(self):
        """Entry point should import and call register_all_tools."""
        filepath = BACKEND_DIR / "mcp_server_unified.py"
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append(alias.name)

        assert "register_all_tools" in imports, "Entry point should import register_all_tools"

    def test_tool_count_by_role(self):
        """Verify expected tool counts in each role module."""
        # Count @mcp.tool() decorators in each file
        role_counts = {
            "shared.py": 18,   # All roles (added mark_handover_read + check_unread_handovers)
            "agent.py": 19,    # Agent only
            "mate.py": 7,      # Mate only
            "tester.py": 7,    # Tester only
            "registrar.py": 6, # Registrar only
        }

        for filename, expected_count in role_counts.items():
            filepath = BACKEND_DIR / "mcp_tools" / filename
            content = filepath.read_text(encoding="utf-8")
            # Count @mcp.tool() occurrences
            count = content.count("@mcp.tool()")
            assert count == expected_count, f"{filename} should have {expected_count} tools, found {count}"

    def test_total_tool_count(self):
        """Total tools across all modules should be 56."""
        total = 0
        for filename in ["shared.py", "agent.py", "mate.py", "tester.py", "registrar.py"]:
            filepath = BACKEND_DIR / "mcp_tools" / filename
            content = filepath.read_text(encoding="utf-8")
            total += content.count("@mcp.tool()")

        assert total == 57, f"Total tools should be 57, found {total}"

    def test_entry_point_has_decorators(self):
        """Entry point should define require_role and safe_tool decorators."""
        filepath = BACKEND_DIR / "mcp_server_unified.py"
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)

        func_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        assert "require_role" in func_names, "Entry point should define require_role"
        assert "safe_tool" in func_names, "Entry point should define safe_tool"
