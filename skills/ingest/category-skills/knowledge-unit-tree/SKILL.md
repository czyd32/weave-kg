---
name: Knowledge-Unit-Tree
description: 知识单元树——将教学教程切割为知识单元 + 前置依赖 DAG。由 KG-Ingest Route 调遣。(knowledge unit tree/prerequisite DAG/teaching content)
---

# Knowledge-Unit-Tree — 知识单元树

## 描述

将教学教程内容（课程、教程、教科书）切割为知识单元，构建前置依赖 DAG。

**切割规则**：以定义/操作/规则词为边界。

## 输出格式

```json
{
  "id": "unit_001",
  "title": "配置 Python 环境",
  "content": "首先安装 Python 3.10+...",
  "prerequisites": [],
  "dependents": ["unit_002", "unit_003"],
  "type": "setup"
}
```

> 详见：`docs/category-system.md` §② 教学教程