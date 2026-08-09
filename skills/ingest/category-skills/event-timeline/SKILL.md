---
name: Event-Timeline
description: 事件时间线知识图谱——将事实事件切割为事件节点 + 时间线。由 KG-Ingest Route 调遣。(event timeline/factual events/temporal ordering)
---

# Event-Timeline — 事件时间线

## 描述

将事实事件（新闻、历史、传记）切割为事件节点，构建时间线。

**切割规则**：以时间/地点/主体切换为边界。

## 输出格式

```json
{
  "id": "evt_001",
  "timestamp": "2024-03-15",
  "location": "硅谷",
  "subject": "OpenAI",
  "action": "发布",
  "object": "GPT-5",
  "description": "OpenAI 在硅谷发布了 GPT-5 模型"
}
```

> 详见：`docs/category-system.md` §④ 事实事件