# Idea: Prompt-to-Structure 自然语言创建项目

**来源**: Plane.so AI "Structure work from a prompt"
**优先级**: 🟡 中（快速展示 AI 能力）
**预计工期**: 3-5 天
**价值**: 一句话生成完整项目结构，体现 AI-native 设计

---

## 问题

Agent 创建项目时需要逐个调用：
1. `create_project`
2. `create_milestone`
3. `create_issue`（多次）
4. `create_plan`
5. `create_plan_item`（多次）

步骤繁琐，Agent 需要理解项目结构才能正确创建。

## 方案

### 1. 新增 MCP Tool

```python
# backend/mcp_server.py

@register_tool("create_project_structure")
def create_project_structure(
    prompt: str,
    project_id: int = None,
    auto_approve: bool = False
) -> str:
    """
    根据自然语言描述自动创建项目结构。
    
    示例 prompt：
    - "做一个博客系统，需要用户认证、文章管理、评论功能"
    - "开发一个电商后台，包含商品管理、订单处理、支付集成"
    - "重构现有代码，添加单元测试和 CI/CD"
    
    Args:
        prompt: 项目需求描述
        project_id: 可选，指定现有项目；不指定则创建新项目
        auto_approve: 是否自动创建（false 则返回预览供确认）
    
    Returns:
        JSON 格式的创建结果摘要
    """
```

### 2. 解析引擎

```python
# backend/src/core/project_generator.py

import json
from typing import List, Dict

class ProjectStructure:
    project_name: str
    milestones: List[Dict]
    issues: List[Dict]
    plans: List[Dict]

async def generate_structure(prompt: str) -> ProjectStructure:
    """
    使用规则引擎 + LLM 解析 prompt，生成项目结构
    """
    
    # Phase 1: 规则引擎快速匹配常见模式
    structure = try_rule_based_parse(prompt)
    if structure:
        return structure
    
    # Phase 2: LLM 解析复杂需求
    llm_prompt = f"""
    分析以下项目需求，生成项目结构：
    
    需求：{prompt}
    
    请输出 JSON：
    {{
        "project_name": "项目名称",
        "milestones": [
            {{
                "name": "Phase 1 - 基础功能",
                "description": "...",
                "order": 1
            }}
        ],
        "issues": [
            {{
                "title": "Issue 标题",
                "description": "详细描述",
                "type": "feature",
                "priority": "P1",
                "milestone": "Phase 1 - 基础功能"
            }}
        ],
        "plans": [
            {{
                "title": "开发计划",
                "description": "...",
                "items": [
                    {{"content": "任务1", "order": 1}},
                    {{"content": "任务2", "order": 2}}
                ]
            }}
        ]
    }}
    
    规则：
    - P0: 阻塞性问题，必须立即解决
    - P1: 核心功能，当前阶段必须完成
    - P2: 重要功能，可延期
    - P3: 优化项，可选
    - 每个 milestone 包含 3-8 个 issue
    - 每个 plan 包含 5-10 个 checklist items
    """
    
    result = await llm.generate_json(llm_prompt)
    return parse_structure(result)
```

### 3. 规则引擎（快速路径）

```python
# 常见项目模板
TEMPLATES = {
    "blog": {
        "project_name": "博客系统",
        "milestones": [
            {"name": "Phase 1 - 基础功能", "order": 1},
            {"name": "Phase 2 - 高级功能", "order": 2}
        ],
        "issues": [
            {"title": "用户认证系统", "type": "feature", "priority": "P1", "milestone": "Phase 1"},
            {"title": "文章 CRUD", "type": "feature", "priority": "P1", "milestone": "Phase 1"},
            {"title": "评论功能", "type": "feature", "priority": "P2", "milestone": "Phase 1"},
            {"title": "标签管理", "type": "feature", "priority": "P2", "milestone": "Phase 2"},
            {"title": "文章搜索", "type": "feature", "priority": "P2", "milestone": "Phase 2"},
        ]
    },
    "ecommerce": {
        "project_name": "电商平台",
        "milestones": [
            {"name": "Phase 1 - 商品与订单", "order": 1},
            {"name": "Phase 2 - 支付与物流", "order": 2}
        ],
        "issues": [
            {"title": "商品管理系统", "type": "feature", "priority": "P1"},
            {"title": "购物车功能", "type": "feature", "priority": "P1"},
            {"title": "订单处理流程", "type": "feature", "priority": "P1"},
            {"title": "支付集成", "type": "feature", "priority": "P2"},
            {"title": "物流跟踪", "type": "feature", "priority": "P2"},
        ]
    }
}

def try_rule_based_parse(prompt: str) -> Optional[ProjectStructure]:
    prompt_lower = prompt.lower()
    for key, template in TEMPLATES.items():
        if key in prompt_lower:
            return template
    return None
```

### 4. 预览模式

```python
@register_tool("preview_project_structure")
def preview_project_structure(prompt: str) -> str:
    """
    预览将要创建的项目结构，不实际创建。
    返回结构化摘要供用户/Agent 确认。
    """
    structure = generate_structure(prompt)
    return json.dumps({
        "preview": True,
        "project_name": structure.project_name,
        "milestones_count": len(structure.milestones),
        "issues_count": len(structure.issues),
        "plans_count": len(structure.plans),
        "summary": generate_summary(structure)
    }, ensure_ascii=False, indent=2)
```

## 使用示例

### Agent 调用

```
User: "我要做一个博客系统，需要用户认证、文章管理、评论功能"

Agent: 
1. 调用 preview_project_structure("博客系统...")
2. 返回预览：
   {
     "preview": true,
     "project_name": "博客系统",
     "milestones_count": 2,
     "issues_count": 8,
     "plans_count": 1,
     "summary": "将创建：Phase 1（用户认证、文章CRUD、评论）+ Phase 2（标签、搜索、SEO）"
   }
3. 用户确认后调用 create_project_structure(..., auto_approve=True)
```

### 实际创建

```
→ 创建 Project: 博客系统
→ 创建 Milestone: Phase 1 - 基础功能 (order=1)
→ 创建 Milestone: Phase 2 - 高级功能 (order=2)
→ 创建 Issue: [P1] 用户认证系统 → 关联 Phase 1
→ 创建 Issue: [P1] 文章 CRUD → 关联 Phase 1
→ 创建 Issue: [P2] 评论功能 → 关联 Phase 1
→ 创建 Issue: [P2] 标签管理 → 关联 Phase 2
→ 创建 Issue: [P2] 文章搜索 → 关联 Phase 2
→ 创建 Plan: 博客系统开发计划
→ 创建 PlanItem: 设计数据库Schema (order=1)
→ 创建 PlanItem: 实现用户注册登录 (order=2)
→ ...
```

## 验收标准

- [ ] `create_project_structure` MCP tool 可用
- [ ] `preview_project_structure` 预览功能正常
- [ ] 规则引擎匹配常见项目类型（blog, ecommerce, admin, api）
- [ ] LLM 解析复杂/未知需求
- [ ] 创建的 milestone/issue/plan 关联正确
- [ ] 返回结果包含完整摘要

## 参考

- Plane.so AI: https://plane.so/ai
- Plane AI "Structure work from a prompt" 功能
