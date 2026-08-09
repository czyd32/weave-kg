# Weave KG 示例数据集

> 用于测试 Weave Knowledge Graph 查询管道和向量检索的完整知识图谱数据集。

## 数据集概况

| 指标 | 数值 |
|------|:--:|
| 内容类型 | 公关/舆论分析（B站视频 OCR 字幕） |
| 来源数量 | 304 个视频 |
| 命题数量 | 2,515 条 |
| 共识簇 | 62 个活跃簇 + 4 个归档簇 |
| 标签数量 | 1,519 个 |
| 向量维度 | 1024（BGE-M3） |
| FAISS 索引 | IndexFlatIP |

## 数据来源

所有内容来源于 B站博主 **"唯一讲述者"** 的公开视频，通过 OCR 提取字幕文本，经 AI Agent 管道处理生成。

标注格式：`BV号 | 博主名 | 视频标题 | 发布日期`

## 使用许可

- **研究/测试用途**：可自由用于学术研究、算法测试、性能基准
- **商业用途**：需自行获取原始内容版权方授权
- **原始版权**：视频原始版权归 B站博主"唯一讲述者"所有
- **衍生数据**：命题提取、标签标注、共识聚类等 AI 处理结果为本项目贡献

## 目录结构

```
real-kg-data/
├── README.md                           ← 本文件
├── _ingested.json                      ← 入库登记表
├── kg-proposition/
│   ├── _meta.json                      ← 命题知识图谱元数据
│   ├── propositions/                   ← 304 个命题文件（SRO 三元组）
│   └── consensus_clusters/             ← 共识簇 + 归档
├── tags/                               ← 1519 个标签索引
└── _shared/
    ├── _index.json                     ← 共享向量空间索引
    └── embeddings/
        ├── faiss.index                 ← FAISS 向量索引（10MB）
        └── id_map.json                 ← 向量→命题映射表
```

## 快速测试

```bash
# 查询示例
python scripts/query.py "什么是言权倒置" --kg-dir examples/real-kg-data

# 带重排序
python scripts/query.py "危机公关怎么做" --kg-dir examples/real-kg-data --rerank

# 查看性能日志
python scripts/query.py "品牌翻车" --kg-dir examples/real-kg-data --verbose
```