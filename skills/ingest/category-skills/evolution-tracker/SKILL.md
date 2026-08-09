---
name: Evolution-Tracker
description: 知识图谱演化追踪——检测同质化/对抗/翻转信号，更新共识簇，少数派保护。不入库管道，按需触发。(evolution tracker/contradiction adjudication/stance tracking/consensus cluster)
---

# Evolution-Tracker — 演化追踪

## 描述

知识图谱的免疫系统。不入库管道，被触发时才运行。核心职责：检测知识图谱中的矛盾、追踪立场演化、更新共识簇。

**与入库管道的区别**：入库管道（Ingest）负责"写"，Evolution-Tracker 负责"审"。两者独立运行，互不阻塞。

## 使用场景

- 发现矛盾观点："Agent 路线可行" vs "Agent 路线不可行"
- 手动触发审计："审计 kg-proposition 中关于 Agent 赛道的所有命题"
- 定期巡检：按时间/新增命题数自动触发全量健康检查
- 追踪立场变化：同一说话人在不同时间对同一主题的看法是否一致

## 依赖声明

- **KG-Ingest**（上游，数据源）：入库管道产出知识图谱数据
- **Proposition-KG**（上游，数据源）：读取 kg-proposition 的命题和共识簇数据
- **Insight-Weaver**（下游，消费方）：读取共识簇数据生成综述
- **Query-Retriever**（上游，触发方）：矛盾发现后建议触发

## 自由度声明

**中自由度**：检测算法是确定性的（同质化/对抗/翻转信号），裁决步骤需要人工交互（AI 不能替代），更新步骤是确定性的。

---

## 核心原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | 只追加不删除 | 历史版本通过 `evolution.changes` 数组追溯 |
| 2 | 不做自动裁决 | 标记冲突，人环内裁决 |
| 3 | 少数派保护 | 低权重高孤立度命题标记为 `minority_signal`，不删除 |

---

## 演化追踪流程

```
新命题入库
    │
    ▼
步骤 1：标签匹配 → BGE-M3 标签向量匹配
    │
步骤 2：SRO 精排 → 对同标签命题做 SRO 三元素向量相似度精排
    │
    ├── 高相似 → 步骤 4：共识簇更新
    └── 低相似 → 步骤 5：对抗检测 → 标记讨论层
    │
步骤 3：新簇检测 → 孤立命题标记为 minority_signal
```

---

## 共识簇结构

```json
{
  "cluster_id": "cc_001",
  "label": "认知偏误",
  "propositions": [
    {
      "id": "p_042",
      "source": "《思考快与慢》ch03",
      "claim": "锚定效应是系统性认知偏误",
      "weight": 0.9
    }
  ],
  "consensus_strength": 0.85,
  "minority_signals": []
}
```

---

## 少数派保护

| 信号 | 判定条件 | 处理 |
|------|---------|------|
| 低权重 | 标签权重 < 阈值 | 标记 `minority_signal`，保留不删除 |
| 高孤立度 | 与其他命题的向量相似度 < 阈值 | 标记 `minority_signal`，等待后续关联 |
| 翻转信号 | 同一来源的立场发生 180° 转变 | 标记 `stance_flip`，记录演变历史 |

---

## 触发方式

| 触发方式 | 场景 | 频率 |
|---------|------|------|
| 入库自动触发 | §5 Aggregate 末尾 | 每次入库 |
| 手动审计触发 | 用户质疑某个共识簇 | 按需 |
| 定期巡检 | 全量命题运行演化检测 | 建议每周/每月 |

## 相关脚本

| 脚本 | 用途 |
|------|------|
| `scripts/run_evolution_tracker.py` | 演化追踪主脚本 |
| `scripts/run_matching_pipeline.py` | 两层匹配管道 |

> 详见：`docs/evolution-tracking.md`（完整演化追踪设计）