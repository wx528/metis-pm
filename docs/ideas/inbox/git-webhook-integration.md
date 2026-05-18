# Idea: Git Webhook 自动关联

**来源**: OneDev, Gitea MCP Server 设计
**优先级**: 🔴 高（解决日常最大痛点）
**预计工期**: 1-2 周
**价值**: Agent 提交代码后自动同步 issue 状态，省去手动操作

---

## 问题

现在代码提交和项目管理完全割裂：
- Agent `git commit -m "fix login bug"` 后，issue #15 还是 open
- 需要手动去系统里标记完成
- 没有代码变更和项目进度的自动关联

## 方案

### 1. 新增 Webhook 接收端点

```python
# backend/main.py
@app.post("/webhook/git")
async def git_webhook(
    request: Request,
    x_hub_signature: str = Header(None),
    x_gitea_signature: str = Header(None)
):
    """
    接收 Git 平台推送事件
    支持：GitHub (x-hub-signature), Gitea (x-gitea-signature), Forgejo
    """
    payload = await request.body()
    event_type = request.headers.get("x-github-event") or request.headers.get("x-gitea-event")
    
    # 验证签名
    if not verify_signature(payload, x_hub_signature or x_gitea_signature):
        raise HTTPException(401, "Invalid signature")
    
    data = await request.json()
    
    if event_type == "push":
        await handle_push_event(data)
    elif event_type == "pull_request":
        await handle_pr_event(data)
    
    return {"status": "ok"}
```

### 2. Commit Message 解析

```python
import re

ISSUE_PATTERN = re.compile(r"(?:fix|fixes|close|closes|resolve|resolves)\s+#(\d+)", re.I)

async def handle_push_event(data: dict):
    commits = data.get("commits", [])
    for commit in commits:
        message = commit.get("message", "")
        issue_ids = ISSUE_PATTERN.findall(message)
        
        for issue_id in issue_ids:
            # 自动关闭 issue
            await close_issue(int(issue_id))
            # 添加活动日志
            await add_activity_log(
                entity_type="issue",
                entity_id=int(issue_id),
                action="closed_by_commit",
                details={
                    "commit_hash": commit["id"][:8],
                    "commit_message": message.split("\n")[0],
                    "author": commit["author"]["name"]
                }
            )
```

### 3. PR 关联 Plan

```python
async def handle_pr_event(data: dict):
    pr = data.get("pull_request", {})
    action = data.get("action")  # opened, closed, merged
    
    # 从 PR 标题/描述中提取 plan 引用
    plan_ids = extract_plan_references(pr.get("title", "") + pr.get("body", ""))
    
    if action == "opened" and plan_ids:
        # PR 创建时关联 plan
        for plan_id in plan_ids:
            await link_pr_to_plan(pr["number"], plan_id)
    
    if action == "merged":
        # PR 合并时更新 plan 状态
        for plan_id in plan_ids:
            await update_plan_status(plan_id, "completed")
```

### 4. 配置页面（前端）

新增 Settings → Git Integration 页面：
- 仓库 URL 输入
- Webhook Secret 设置
- 事件订阅选择（push / pull_request / issues）
- 自动关闭规则配置
- Webhook URL 展示（供复制到 Git 平台）

## 数据模型扩展

```python
# backend/src/models/__init__.py
class GitIntegration(Base):
    __tablename__ = "git_integrations"
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    repo_url = Column(String)
    platform = Column(String)  # github / gitea / forgejo
    webhook_secret = Column(String)  # 加密存储
    auto_close_issue = Column(Boolean, default=True)
    auto_link_pr = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class IssueCommitLink(Base):
    __tablename__ = "issue_commit_links"
    
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey("issues.id"))
    commit_hash = Column(String(40))
    commit_message = Column(Text)
    author = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 验收标准

- [ ] GitHub push webhook 接收正常
- [ ] Commit message 解析 `fix #123` 正确
- [ ] Issue 自动关闭并记录活动日志
- [ ] PR 创建自动关联 Plan
- [ ] 前端配置页面可用
- [ ] Webhook 签名验证通过

## 参考

- OneDev MCP Server: https://code.onedev.io/onedev/server
- Gitea Webhook Docs: https://docs.gitea.com/usage/webhooks
