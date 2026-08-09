---
name: Dialogue-Graph
description: 对话知识图谱——将对话访谈切割为 Q&A 对 + 立场块，构建说话人档案和立场演化。由 KG-Ingest Route 调遣。(dialogue graph/Q&A pairs/speaker stance tracking)
---

# Dialogue-Graph — 对话知识图谱

## 描述

将对话访谈（播客、访谈、辩论）切割为结构化 Q&A 对，追踪说话人立场变化。

**切割规则**：以问句/答句/立场转换为边界。

## 输出格式

```json
{
  "id": "ex_001",
  "question": "你怎么看大模型的开源和闭源之争？",
  "answer": "我认为开源是趋势，但闭源在特定场景仍有优势...",
  "speaker": "张三",
  "stance": "支持开源为主",
  "stance_confidence": 0.85
}
```

> 详见：`docs/category-system.md` §③ 对话访谈