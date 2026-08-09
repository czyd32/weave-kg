# 入库管道 (Ingest Pipeline)

> 6 步管道：从素材到知识图谱的完整流程。

---

## 管道总览

```
§0 接收 → §1 分割 → §2 分类 → §3 路由 → §4 提炼 → §5 聚合
```

| 步骤 | 名称 | 输入 | 输出 | 执行者 |
|:--:|------|------|------|------|
| §0 | 接收 | 素材文件路径 | 全文文本 + 元数据 | Ingest |
| §1 | 分割 | 全文文本 | Segment 列表（每段标注边界） | Ingest |
| §2 | 分类 | Segment 列表 | 每个 Segment 的内容类型标签 | Ingest |
| §3 | 路由 | 分类后的 Segment | 分发到对应 Category Skill | Ingest |
| §4 | 提炼 | 分类后的 Segment | 知识单元（命题/Q&A/事件等） | Category Skill |
| §5 | 聚合 | 知识单元列表 | 搬入正式目录 + 更新共享层 | Ingest |

---

## §0 接收 (Receive)

**输入**：素材文件路径（`.md`、`.txt`）

**操作**：
1. 读取文件内容
2. 解析元数据（来源、作者、日期、类型）
3. 生成 `source_id`（唯一标识）

**输出**：
```json
{
  "source_id": "article-2026-001",
  "title": "为什么我们总被直觉骗",
  "author": "唯一讲述者",
  "date": "2026-08-01",
  "type": "video_subtitle",
  "content": "全文文本..."
}
```

---

## §1 分割 (Segment)

**输入**：全文文本

**操作**：按语义边界切割为段落级 Segment。切割规则因素材类型而异：

| 素材类型 | 切割规则 |
|---------|---------|
| 视频字幕 | 按话题转换、说话人切换、时间间隔 |
| 文章 | 按段落、小标题 |
| 书籍 | 按章节自然边界 |
| 对话 | 按问答轮次 |

**输出**：
```json
[
  {
    "segment_id": "seg-001",
    "content": "直觉是人类最古老的决策工具...",
    "boundary_type": "topic_shift",
    "position": {"start": 0, "end": 3}
  },
  ...
]
```

---

## §2 分类 (Classify)

**输入**：Segment 列表

**操作**：对每个 Segment 判定内容类型。一个 Segment 可以有多个类型标签。

**6 种内容类型判定规则**：

| 类型 | 判定特征 | 路由目标 |
|------|---------|---------|
| ① 论证观点 | 出现因果词（因此/所以/导致）、比较词（然而/但是/相比）、定义句 | kg-proposition |
| ② 教学教程 | 出现定义词（是指/定义为）、操作词（首先/然后/步骤）、规则词（必须/应当/禁止） | kg-teaching |
| ③ 对话访谈 | 出现问句、答句、立场转换（我认为/你觉得/不同意） | kg-dialogue |
| ④ 事实事件 | 出现时间词、地点词、主体切换 | kg-events |
| ⑤ 参考手册 | 出现参数、配置项、API 名称、数值范围 | kg-reference |
| ⑥ 叙事故事 | 出现场景描述、冲突、视角转换 | kg-narrative |

**多类型示例**：
```
"2024年，ChatGPT的发布引发了AI行业的巨变。这一事件表明，大语言模型已从实验室走向商业化。"
→ ④ 事实事件（时间+事件） + ① 论证观点（因果判断）
→ 同时路由到 kg-events 和 kg-proposition
```

---

## §3 路由 (Route)

**输入**：分类后的 Segment 列表

**操作**：将每个 Segment 分发到对应的 Category Skill。一个 Segment 可以被多个 Category Skill 处理。

**路由规则**：
- 论证观点 → Proposition-Knowledge-Graph
- 教学教程 → Knowledge-Unit-Tree
- 对话访谈 → Dialogue-Graph
- 事实事件 → Event-Timeline
- 参考手册 → Reference-Manual
- 叙事故事 → Narrative-Map

---

## §4 提炼 (Refine)

**输入**：分类后的 Segment（由 Category Skill 处理）

**操作**：Category Skill 将 Segment 切割为原子知识单元。详见各 Category Skill 的 SKILL.md。

**输出示例（Proposition-Knowledge-Graph）**：
```json
{
  "id": "p_001",
  "segment_id": "seg-001",
  "source_id": "article-2026-001",
  "subject": "直觉",
  "relation": "是",
  "object": "人类最古老的决策工具",
  "original_text": "直觉是人类最古老的决策工具，它在进化过程中帮助我们快速应对威胁。",
  "concepts": ["直觉", "决策", "进化"],
  "confidence": 0.95
}
```

---

## §5 聚合 (Aggregate)

**输入**：所有 Category Skill 产出的知识单元

**操作**：
1. **搬入正式目录**：从 `.ingest/` 临时目录搬入 `knowledge-graph/` 正式目录
2. **写入标签**：提取关键词，写入 `tags/` 共享标签体系
3. **向量化**：对所有新命题运行 `embed_call.py`，写入 `_shared/embeddings/`
4. **更新索引**：更新 `_shared/_index.json` 跨 KG 全局索引
5. **触发演化追踪**：对所有新命题，运行 Evolution-Tracker 检测与已有命题的关系

---

## 临时目录

Ingest 过程中使用 `.ingest/` 临时目录存放中间产物：

```
.ingest/
├── {batch_id}/
│   ├── segments.json          ← §1 分割结果
│   ├── classification.json    ← §2 分类结果
│   ├── routing.json           ← §3 路由结果
│   ├── propositions/          ← §4 提炼结果（命题）
│   ├── exchanges/             ← §4 提炼结果（对话）
│   └── ...
└── _manifest/
    └── {batch_id}.json        ← 持久化日志
```

§5 聚合完成后，临时目录可清理。