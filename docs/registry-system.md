# 清单机制（Registry System）

> Weave 的核心基础设施——三层清单确保多 Agent 并行处理时的状态一致性、去重和可追溯性。

---

## 一、为什么需要清单机制

Weave 的知识图谱入库是**多 Agent 并行**的——多个工蜂同时处理不同内容，聚合师负责合并。如果没有共享的状态追踪，会出现：

| 问题 | 后果 |
|------|------|
| 同一内容被重复处理 | 重复命题、浪费算力 |
| 处理中断后无法恢复 | 不知道哪些已完成、哪些待处理 |
| 成果丢失 | 命题写入了但索引未更新，查询不到 |
| 来源不可追溯 | 不知道某个命题来自哪个文件、哪个批次 |

清单机制是**多 Agent 协调的共享状态层**——不是数据库，而是轻量的 JSON 文件，每个 Agent 在关键节点读写。

---

## 二、三层清单架构

```
knowledge-graph/
├── _ingested.json              ← L1: 全局入库登记表（有哪些内容已入库）
├── kg-proposition/
│   └── _meta.json              ← L2: KG 元数据（这个 KG 的统计和来源）
├── kg-dialogue/
│   └── _meta.json
├── tags/
│   └── _index.json             ← L2: 标签索引（快速查找标签）
└── _shared/
    └── _index.json             ← L3: 跨 KG 全局索引（向量空间、KG 实例注册）
```

---

## 三、L1：`_ingested.json` — 全局入库登记表

### 定位

**一切入库操作的唯一真源**。任何内容进入知识图谱之前，必须先检查此文件是否已登记。

### Schema

```json
{
  "ingested": [
    {
      "source_id": "唯一来源标识",
      "title": "内容标题",
      "author": "作者/来源名",
      "date": "2024-01-15",
      "propositions": 12,
      "ingested_at": "2026-08-08",
      "batch": "20260808_batch_01",
      "cleaned_file": "社科/唯一讲述者/2024-01-15-xxx·清洗版.md",
      "kg_type": "kg-proposition"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| `source_id` | string | ✅ | 唯一标识。B 站用 BV 号，书籍用 ISBN，文章用 URL 哈希 |
| `title` | string | ✅ | 内容标题 |
| `author` | string | ✅ | 作者/来源 |
| `date` | string | ✅ | 内容发布日期 |
| `propositions` | int | ✅ | 提取的命题数 |
| `ingested_at` | string | ✅ | 入库日期 |
| `batch` | string | ✅ | 批次 ID，格式 `YYYYMMDD_batch_NN` |
| `cleaned_file` | string | ✅ | 清洗版文件路径（相对于知识图谱根目录） |
| `kg_type` | string | ✅ | 路由到的 KG 类型：`kg-proposition` / `kg-dialogue` / 等 |

### 约束

| # | 铁律 | 违反后果 |
|---|------|---------|
| 1 | `source_id` 必须唯一，禁止重复登记 | 同一内容被多次处理，命题重复 |
| 2 | 入库前必须检查此文件，已登记则跳过 | 浪费算力 |
| 3 | 入库完成后必须立即写入，不能延迟 | 中断后无法恢复状态 |
| 4 | 写入后必须执行一致性审计（`cleaned_file` 存在性、`kg_type` 目录存在性） | 数据不一致 |

### 使用场景

| 阶段 | 操作 | Agent |
|------|------|-------|
| 补缺模式 | 扫描待处理内容 → 排除已在 `_ingested.json` 中的 | 工蜂 |
| 入库前 | 检查 `source_id` 是否已存在 → 存在则跳过 | 工蜂 |
| 入库后 | 追加新条目 → 写入 `_ingested.json` | 聚合师 |

---

## 四、L2：`_meta.json` — KG 元数据

### 定位

每个 KG 实例的**自描述文件**。记录该 KG 的类型、统计、来源列表。

### Schema

```json
{
  "updated": "2026-08-05",
  "description": "命题知识图谱——论证观点与因果链",
  "total_propositions": 2515,
  "batch": "2026-08-05-ingest",
  "sources": [
    "BV1rYZZYUEJT",
    "BV1PzXHY3EQg"
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `updated` | string | 最后更新日期 |
| `description` | string | KG 类型描述 |
| `total_propositions` / `total_exchanges` | int | 该 KG 的知识单元总数 |
| `batch` | string | 最后处理批次 |
| `sources` | array | 该 KG 包含的所有来源 ID |

### 约束

- 每次 Ingest 管道执行后必须更新 `total_*` 和 `sources`
- 多个 KG 实例的 `sources` 不应重叠（同一内容只路由到一个 KG）

---

## 五、L3：`_shared/_index.json` — 跨 KG 全局索引

### 定位

**跨 KG 的共享状态层**。记录向量空间、嵌入模型、所有 KG 实例的注册信息。

### Schema

```json
{
  "kg_type": "shared",
  "description": "跨 KG 实例的统一嵌入索引",
  "created": "2026-08-08",
  "last_updated": "2026-08-09",

  "embedding_model": {
    "name": "BGE-M3",
    "model_id": "BAAI/bge-m3",
    "provider": "SiliconFlow",
    "endpoint": "https://api.siliconflow.cn/v1/embeddings",
    "dimensions": 1024
  },

  "vector_index": {
    "file": "embeddings/faiss.index",
    "id_map": "embeddings/id_map.json",
    "total_vectors": 2515,
    "index_type": "IndexFlatIP"
  },

  "instances": {
    "kg-proposition": {
      "path": "../kg-proposition/",
      "type": "proposition",
      "description": "论证观点—命题知识图谱",
      "propositions": 2515
    },
    "kg-dialogue": {
      "path": "../kg-dialogue/",
      "type": "dialogue",
      "description": "对话知识图谱—QA对与讨论流",
      "exchanges": 11
    }
  }
}
```

### 约束

| # | 铁律 |
|---|------|
| 1 | 新增 KG 实例时必须在此注册 |
| 2 | 向量化后必须更新 `total_vectors` |
| 3 | 嵌入模型或端点变更时必须更新 `embedding_model` |

---

## 六、清单与管道的交互

### 写入端（Ingest 管道）

```
Ingest §5 Aggregate 完成后：
  1. 更新 _ingested.json（追加新条目）
  2. 更新 KG 的 _meta.json（更新 total_* 和 sources）
  3. 向量化新命题 → 更新 _shared/_index.json（更新 total_vectors）
```

### 读取端（补缺模式 / 查询）

```
补缺模式：
  扫描待处理内容 → 读取 _ingested.json → 排除已入库 → 生成差集

查询：
  Query-Retriever → 读取 _shared/_index.json → 获取向量索引路径
                  → 读取各 KG 的 _meta.json → 获取 KG 列表
```

---

## 七、维护规范

### 新增 KG 实例

1. 创建 KG 目录（如 `kg-proposition/`）
2. 创建 `_meta.json`（填写 description、初始 total）
3. 在 `_shared/_index.json` 的 `instances` 中注册

### 批量入库后

1. 更新 `_ingested.json`（追加所有新条目）
2. 更新对应 KG 的 `_meta.json`（更新 total 和 sources）
3. 执行向量化 → 更新 `_shared/_index.json` 的 `total_vectors`

### 一致性审计

定期执行以下检查：

| 检查项 | 方法 |
|--------|------|
| `_ingested.json` 中所有 `cleaned_file` 存在 | 遍历验证文件路径 |
| `_ingested.json` 中无重复 `source_id` | 按 `source_id` 去重检查 |
| 各 KG 的 `_meta.json` 中 `total_*` 与实际文件数一致 | 统计目录下命题文件数对比 |
| `_shared/_index.json` 中 `total_vectors` 与 `faiss.index` 一致 | 读取 FAISS 索引的 `ntotal` 对比 |

---

## 八、设计原则

| 原则 | 说明 |
|------|------|
| **轻量优先** | 不是数据库，是 JSON 文件。不需要额外依赖，Git 可追踪 |
| **单一真源** | 每个状态只有一个权威来源。`_ingested.json` 是入库状态的唯一真源 |
| **先读后写** | 所有 Agent 在关键操作前必须读取清单，操作后必须立即写入 |
| **可审计** | 所有清单文件纳入 Git 版本控制，任何变更可追溯 |
| **幂等** | 重复检查同一 `source_id` 应返回相同结果，不产生副作用 |