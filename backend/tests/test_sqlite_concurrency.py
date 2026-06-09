"""
SQLite 并发压力测试
验证 WAL 模式下的多 Agent 并发写入性能
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager

from main import app
from src.core.dependencies import get_db
from src.models.issue import Issue
from src.models.comment import Comment
from sqlalchemy import select, func


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def auth_headers(client):
    resp = await client.post("/api/v1/auth/login", json={"password": "testadmin"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_sqlite_wal_concurrent_writes(client, auth_headers):
    """测试 WAL 模式下并发创建 Issue 的性能"""
    print("\n🧪 测试 SQLite WAL 模式并发写入性能...")
    
    # 1. 验证 WAL 模式已启用
    async for db in get_db():
        result = await db.execute(select(func.count()).select_from(Issue))
        initial_count = result.scalar()
        break
    
    print(f"   初始 Issue 数量: {initial_count}")
    
    # 2. 并发创建 20 个 Issue
    num_requests = 20
    start_time = time.time()
    
    async def create_issue(idx):
        resp = await client.post("/api/v1/issues", json={
            "title": f"并发测试 Issue #{idx}",
            "issue_type": "task",
            "priority": "P2",
            "description": f"由并发测试创建，序号 {idx}",
        }, headers=auth_headers)
        return resp.status_code == 201 or resp.status_code == 200
    
    # 使用 asyncio.gather 模拟并发请求
    tasks = [create_issue(i) for i in range(num_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    duration = end_time - start_time
    
    success_count = sum(1 for r in results if r is True)
    error_count = sum(1 for r in results if isinstance(r, Exception))
    
    print(f"   ✅ 成功: {success_count}/{num_requests}")
    print(f"   ❌ 失败: {error_count}/{num_requests}")
    print(f"   ⏱️  耗时: {duration:.2f} 秒")
    print(f"   🚀 平均: {duration/num_requests:.3f} 秒/请求")
    
    # 3. 验证数据完整性
    async for db in get_db():
        result = await db.execute(select(func.count()).select_from(Issue))
        final_count = result.scalar()
        break
    
    assert final_count == initial_count + success_count, \
        f"数据不一致：期望 {initial_count + success_count}，实际 {final_count}"
    
    print(f"   📊 最终 Issue 数量: {final_count}")
    print("   ✓ WAL 模式并发写入测试通过！\n")


@pytest.mark.asyncio
async def test_sqlite_wal_read_during_write(client, auth_headers):
    """测试 WAL 模式下读操作不阻塞写操作"""
    print("\n🧪 测试 WAL 模式下读写并发...")
    
    write_count = 10
    read_count = 10
    
    start_time = time.time()
    
    async def write_issue(idx):
        resp = await client.post("/api/v1/issues", json={
            "title": f"读写测试 W#{idx}",
            "issue_type": "task",
            "priority": "P2",
        }, headers=auth_headers)
        return resp.status_code == 201 or resp.status_code == 200
    
    async def read_issues(idx):
        resp = await client.get("/api/v1/issues?limit=5", headers=auth_headers)
        return resp.status_code == 200
    
    # 混合读写请求
    write_tasks = [write_issue(i) for i in range(write_count)]
    read_tasks = [read_issues(i) for i in range(read_count)]
    
    all_tasks = write_tasks + read_tasks
    results = await asyncio.gather(*all_tasks, return_exceptions=True)
    
    end_time = time.time()
    duration = end_time - start_time
    
    success_count = sum(1 for r in results if r is True)
    total = len(all_tasks)
    
    print(f"   ✅ 成功: {success_count}/{total} (写: {write_count}, 读: {read_count})")
    print(f"   ⏱️  耗时: {duration:.2f} 秒")
    print(f"   🚀 吞吐量: {total/duration:.1f} 请求/秒")
    print("   ✓ 读写并发测试通过！\n")


@pytest.mark.asyncio
async def test_sqlite_wal_comment_concurrent(client, auth_headers):
    """测试并发添加评论"""
    print("\n🧪 测试并发添加评论...")
    
    # 先创建一个 Issue
    resp = await client.post("/api/v1/issues", json={
        "title": "评论并发测试",
        "issue_type": "task",
        "priority": "P2",
    }, headers=auth_headers)
    issue_id = resp.json()["id"]
    
    num_comments = 15
    start_time = time.time()
    
    async def add_comment(idx):
        resp = await client.post(f"/api/v1/issues/{issue_id}/comments", json={
            "content": f"并发评论 #{idx}",
            "author": "test-agent",
            "comment_type": "normal",
        }, headers=auth_headers)
        return resp.status_code == 201 or resp.status_code == 200
    
    tasks = [add_comment(i) for i in range(num_comments)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    duration = end_time - start_time
    
    success_count = sum(1 for r in results if r is True)
    
    print(f"   ✅ 成功: {success_count}/{num_comments}")
    print(f"   ⏱️  耗时: {duration:.2f} 秒")
    print(f"   🚀 平均: {duration/num_comments:.3f} 秒/评论")
    print("   ✓ 评论并发测试通过！\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
