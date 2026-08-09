---
name: Narrative-Map
description: 叙事地图知识图谱——将叙事故事切割为情节节拍 + 情节地图。由 KG-Ingest Route 调遣。(narrative map/plot beats/story structure)
---

# Narrative-Map — 叙事地图

## 描述

将叙事故事（案例分析、故事叙述）切割为情节节拍，构建情节地图。

**切割规则**：以场景/冲突/视角转换为边界。

## 输出格式

```json
{
  "id": "beat_001",
  "type": "setup",
  "description": "主角发现系统中的异常数据",
  "characters": ["张三"],
  "location": "数据中心",
  "tension_level": 3
}
```

> 详见：`docs/category-system.md` §⑥ 叙事故事