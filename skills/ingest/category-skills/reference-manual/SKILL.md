---
name: Reference-Manual
description: 参考手册知识图谱——将参考手册/API文档切割为条目 + 参数分组 + 层级索引。由 KG-Ingest Route 调遣。(reference manual/API documentation/parameter grouping)
---

# Reference-Manual — 参考手册知识图谱

## 描述

将参考手册、API 文档等内容切割为结构化条目。

**切割规则**：以条目/参数分组为边界。

## 输出格式

```json
{
  "id": "ref_001",
  "name": "max_tokens",
  "type": "integer",
  "default": 4096,
  "range": [1, 128000],
  "description": "生成文本的最大 token 数",
  "category": "API 参数"
}
```

> 详见：`docs/category-system.md` §⑤ 参考手册