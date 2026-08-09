---
name: KG-Ingest
description: 知识图谱入库管道——将任意文本素材（文章/视频字幕/对话记录）接入知识图谱。定义6步入库管道（接收→分割→分类→路由→提炼→聚合），统一管理共享层（标签/向量/索引），调遣Category Skill各司其职。(knowledge graph ingest pipeline/content type routing/segment-level classification)
---

# KG-Ingest — 知识图谱入库管道

## 描述

知识图谱入库管道——从素材到知识图谱的统一入口。核心职责：**收素材 → 拆小段 → 看每段是什么类型 → 发给对应处理员 → 统一上书架**。

**核心原则**：不分类文档，分类段落。一段访谈可以同时产出对话壳、论证命题、教学单元——Ingest 负责识别和路由，Category Skill 负责切割，共享层只由 Ingest 写入。

## 使用场景

- 用户提供素材要求"存入知识库"
- 用户需要将新内容接入已有的知识图谱体系
- 用户需要跨类别处理复杂素材（访谈中包含论证段、教学段）
- 用户说"把这个入库"或"处理这篇内容"

## 依赖声明

本 Skill 为知识图谱入库体系的**唯一入口**。9 个 Category Skill 作为内部子 Skill 封装在本目录下：

| # | 子 Skill | 目录 | 覆盖 |
|:--:|------|------|:--:|
| 1 | Proposition-KG | `proposition-kg/` | ①论证观点——切割原子命题，构建因果链 |
| 2 | Dialogue-Graph | `dialogue-graph/` | ③对话访谈——切割 Q&A 对 + 立场块 |
| 3 | Knowledge-Unit-Tree | `knowledge-unit-tree/` | ②教学教程——切割知识单元 + 前置依赖 DAG |
| 4 | Reference-Manual | `reference-manual/` | ⑤参考手册——切割条目 + 参数分组 |
| 5 | Event-Timeline | `event-timeline/` | ④事实事件——事件节点 + 时间线 |
| 6 | Narrative-Map | `narrative-map/` | ⑥叙事故事——情节节拍 + 情节地图 |
| 7 | Evolution-Tracker | `evolution-tracker/` | 演化追踪——同质化/对抗/少数派保护 |
| 8 | Insight-Weaver | `insight-weaver/` | 综述生成——主题驱动三层结构 |
| 9 | Query-Retriever | `query-retriever/` | 语义查询——双路召回 + RRF 融合 |

> 方法论文档：`docs/architecture.md` + `docs/pipeline.md` + `docs/category-system.md`
> 策略源对应：修改本 Skill 涉及架构/机制/阈值/目录结构变更时，需同步更新 `docs/` 下对应文档。

## 自由度声明

**低自由度**：6 步管道是确定性的（顺序固定，每步有完成标准），输出路径是固定的（联邦式目录结构），交互协议是固定的（Segment JSON ↔ 知识单元列表）。仅 Segment 切割准确率和分类标签允许 AI 灵活判断。

---

## 速查卡

| 我想… | 去这里 |
|--------|-------|
| 了解完整管道 | [§1 工作流总览](#1-工作流总览) |
| 了解怎么切 Segment | [§2 Segment（分割）](#2-§1-segment分割) |
| 了解怎么分类 | [§3 Classify（分类）](#3-§2-classify分类) |
| 了解怎么调遣 Category Skill | [§4 Route（路由）](#4-§3-route路由) |
| 了解怎么提炼 | [§5 Refine（提炼）](#5-§4-refine提炼) |
| 了解怎么聚合 | [§6 Aggregate（聚合）](#6-§5-aggregate聚合) |
| 看输出格式 | [§7 输出格式](#7-输出格式) |
| 检查质量 | [§8 反模式](#8-反模式) + [§9 质量检查清单](#9-质量检查清单) |

---

## 1. 工作流总览

```
输入：一篇素材（文章/视频字幕/对话记录）
  │
  ├── §0 Receive（接收）
  │     确定 source_id，创建 .ingest/ 临时目录
  │
  ├── §1 Segment（分割）
  │     按主题边界 + 说话人切换切分段落
  │     → 输出 N 个 Segment
  │
  ├── §2 Classify（分类）
  │     每个 Segment 判定类型：①论证 ②教学 ③对话 ④事件 ⑤参考 ⑥叙事
  │     → 输出：每个 Segment 的 type 标签
  │
  ├── §3 Route（路由）
  │     按 type 调遣 Category Skill 处理
  │     type=① → Proposition-KG
  │     type=② → Knowledge-Unit-Tree
  │     type=③ → Dialogue-Graph
  │     → 输出：知识单元写入 .ingest/{batch_id}/{category}/
  │
  ├── §4 Refine（提炼）
  │     过滤低价值知识单元（保留：概念/反常识/方法论/有论据观点；丢弃：人物背景/纯感受/空泛建议）
  │
  └── §5 Aggregate（聚合）
        → 合并各 Category Skill 的 _tags.json
        → 搬入正式目录（kg-proposition/、kg-dialogue/ 等）
        → 写入共享层（tags/、_shared/、_index.md）
        → 删除 .ingest/ 临时目录
```

---

## 2. §0 Receive（接收）

### 确定 source_id（三级降级规则）

| 优先级 | 条件 | 格式 | 示例 |
|:--:|------|------|------|
| 1 | 有平台唯一 ID（B站BV号、YouTube视频ID等） | `{平台ID}` | `BV1qx7s6VEod` |
| 2 | 有发布日期+作者，无平台唯一ID | `{YYYYMMDD}_{作者}` | `20260627_author_name` |
| 3 | 无来源信息 | `r{5位随机码}` | `r8k2m9` |

### 创建临时目录

```
batch_id = {日期}_{source_id}
创建 knowledge-graph/.ingest/{batch_id}/
  ├── dialogue/
  ├── propositions/
  ├── teaching/
  ├── events/
  └── narrative/
```

> **碰撞检查**：创建前必须检查 `.ingest/{batch_id}/` 是否已存在。若存在，说明已处理过，跳过不重复处理。

---

## 3. §1 Segment（分割）

按以下边界切分：

| 边界类型 | 检测信号 | 示例 |
|---------|---------|------|
| 主题切换 | 话题从 A 转向 B | "好的，那我们聊一聊下一个话题..." |
| 说话人切换 | 对话中发言者变化 | "A：... → B：..." |
| 内容类型突变 | 从对话转入独白、从讲解转入举例 | 问答 → 长篇论述 |

**嵌套深度限制**：≤ 2 层。L1 = 主题级分割，L2 = 子主题分割。

### Segment 输出格式

```json
[
  {
    "segment_id": "seg_001",
    "text": "完整段落文本...",
    "speaker": "说话人",
    "time_range": "02:00-15:00",
    "source_id": "article_001"
  }
]
```

---

## 4. §2 Classify（分类）

每个 Segment 判定类型：

| type | 名称 | 判定关键词 | Category Skill |
|:--:|------|---------|------|
| ① | 论证观点 | 因果链、转折、反驳、论证 | Proposition-KG |
| ② | 教学教程 | 定义、操作步骤、规则约束 | Knowledge-Unit-Tree |
| ③ | 对话访谈 | 问答、追问、立场转换 | Dialogue-Graph |
| ④ | 事实事件 | 时间标记、地点变化、事件序列 | Event-Timeline |
| ⑤ | 参考手册 | 条目边界、参数分组 | Reference-Manual |
| ⑥ | 叙事故事 | 场景切换、冲突升级、视角转换 | Narrative-Map |

---

## 5. §3 Route（路由）

```
type=① → Proposition-KG
type=② → Knowledge-Unit-Tree
type=③ → Dialogue-Graph
type=④ → Event-Timeline
type=⑤ → Reference-Manual
type=⑥ → Narrative-Map
```

**交互协议**：

| 方向 | 格式 | 内容 |
|------|------|------|
| Ingest → Category Skill | Segment JSON | `{ segment_id, text, type, speaker?, source_id, batch_id }` |
| Category Skill → Ingest | 知识单元列表 | 写入 `.ingest/{batch_id}/{category}/` |

**Category Skill 只写自己的子目录，不碰共享层（tags/、_shared/）和其他 Category 的子目录。**

---

## 6. §4 Refine（提炼）

**保留**：概念定义、反常识、方法论、有论据的观点、有步骤的建议
**合并**：同一叙事碎片、因果链过度拆分、概念解释冗余
**丢弃**：人物背景介绍、纯感受/情绪、空泛建议、无独立知识增量的案例

---

## 7. §5 Aggregate（聚合）

```
1. 合并标签 → 读取所有 _tags.json，去重合并
2. 搬入正式目录 → 从 .ingest/ 搬到 knowledge-graph/kg-*/
3. 两层匹配（BGE-M3）→ 标签层粗筛 + SRO层精排，更新共识簇
4. 写入共享层 → 更新 tags/_index.json、向量化、更新 _shared/
5. 清理临时目录 → 删除 .ingest/{batch_id}/
6. 触发 Evolution-Tracker → 新簇检测 + 对抗检测
```

---

## 8. 输出格式（联邦式目录结构）

```
knowledge-graph/
├── .ingest/                    ← 临时目录（处理中）
├── kg-proposition/             ← ①论证观点
│   ├── propositions/
│   ├── consensus_clusters/
│   └── discussion_layer/
├── kg-dialogue/                ← ③对话访谈
├── kg-teaching/                ← ②教学教程
├── kg-events/                  ← ④事实事件
├── kg-reference/               ← ⑤参考手册
├── kg-narrative/               ← ⑥叙事故事
├── tags/                       ← 共享标签层（只有 Ingest 能写）
├── _shared/                    ← 共享向量空间（只有 Ingest 能写）
│   └── embeddings/
└── _ingested.json              ← 已入库文件清单
```

---

## 9. 反模式

| # | 反模式 | 修正方向 |
|---|--------|---------|
| 1 | 跳过 Segment 直接送全文 | 必须先走 §1 Segment + §2 Classify |
| 2 | Category Skill 直接写共享层 | 处理员只写 .ingest/，共享层由 §5 统一写 |
| 3 | 用文档类型判断代替 Segment 分类 | 必须逐 Segment 分类，不能整篇打标签 |
| 4 | 跳过 Refine 直接聚合 | 必须走 §4 Refine 筛选 |
| 5 | 临时目录不清理 | §5 Aggregate 完成后必须删除 |
| 6 | 聚合时跳过标签合并 | 必须合并去重 |

---

## 10. 质量检查清单

| # | 自检问句 |
|---|---------|
| 1 | 是否创建了 .ingest/{batch_id}/ 临时目录？ |
| 2 | 每个 Segment 是否都有 type 标签？ |
| 3 | 是否有 type 在 ①-⑥ 范围外？ |
| 4 | 每个实现了的 type 的 Segment 是否都送入了对应的 Category Skill？ |
| 5 | 是否执行了 Refine（保留/合并/丢弃）？ |
| 6 | 标签是否合并去重？ |
| 7 | 知识单元是否搬入了正式目录？ |
| 8 | .ingest/{batch_id}/ 是否已删除？ |

---

## 项目初始化

首次使用本 Skill 时，检查 `knowledge-graph/` 目录是否存在。缺失时按 §8 输出格式创建目录结构。

> 详见：`docs/pipeline.md`（完整管道详解）、`docs/architecture.md`（架构设计）、`docs/category-system.md`（6 类内容切割详解）