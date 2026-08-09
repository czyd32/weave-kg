---
name: Insight-Weaver
description: 知识图谱综述生成——主题驱动，三层结构（Foundation→Development→Frontier），消费共识簇和命题，生成论证文章。(insight weaver/survey generation/knowledge-graph-to-text)
---

# Insight-Weaver — 综述生成

## 描述

知识图谱的"作者"。消费 Evolution-Tracker 产出的共识簇和讨论层，生成面向人类的综述文章。核心职责：**主题驱动 → 三层分类（F/D/F）→ 大纲生成 → 写作+归因 → 论证文章**。

**一句话定位**：Ingest 负责"写"知识单元，Evolution-Tracker 负责"审"知识关系，Insight-Weaver 负责"讲"知识故事。

## 使用场景

- 生成某个主题的综述文章："生成关于 Agent 范式的论证文章"
- 跨来源知识融合：书籍 + 视频 + 论文的命题碰撞
- 发现知识缺口：某个主题在 KG 中缺乏哪些维度的覆盖

## 依赖声明

- **Evolution-Tracker**（上游，数据源）：读取共识簇和讨论层
- **Query-Retriever**（上游，调用方）：调用检索相关命题
- **Proposition-KG**（上游，数据源）：读取原始命题

---

## 三层结构（F/D/F）

| 层级 | 名称 | 内容 | 来源 |
|:--:|------|------|------|
| F | Foundation（基础） | 共识命题、定义、基本概念 | 共识簇中高权重命题 |
| D | Development（发展） | 不同观点、争论、演化 | 讨论层 + 不同来源的命题 |
| F | Frontier（前沿） | 开放问题、少数派观点、趋势 | minority_signals + 新簇候选 |

---

## 工作流

```
1. 主题确定 → 用户指定或自动发现高频标签
2. 素材检索 → Query-Retriever 检索相关命题
3. 三层分类 → 按 F/D/F 归类
4. 大纲生成 → 三层结构 + 子主题
5. 写作+归因 → 每段标注 [p_xxx] 来源
6. 输出论证文章.md
```

---

## 输出示例

```markdown
# 关于直觉决策的局限性

## Foundation：什么是直觉决策

直觉是人类最古老的决策工具 [p_042]。卡尼曼将直觉定义为系统1思维的典型表现 [p_103]...

## Development：不同视角的争论

唯一讲述者从公关危机案例提供了实证支持，认为直觉在复杂决策中系统性失败 [p_201]。然而...

## Frontier：开放问题

少数派观点认为，直觉在特定领域（如急诊医学）仍不可替代 [p_305]...
```

> 详见：`docs/architecture.md` §L3 消费层