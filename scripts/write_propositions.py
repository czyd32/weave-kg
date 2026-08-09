"""
LLM 命题提炼 → 落盘全自动闭环（根因防转义）。

背景：命题 JSON 由 Agent 直接写盘时，LLM 输出内容字段（subject/object/cause/
effect/original_text）内部混入的英文双引号未转义，导致 json.load 崩溃。本脚本
把「解析 LLM 输出 → 序列化 → 校验 → 落盘」收口为一处，用 json.dumps() 落盘，
从物理上保证生成的文件永远是合法 JSON——LLM 输出里的引号不再可能破坏文件。

使用方式（Agent 提炼结束后调用）：
    # 从文件读取 LLM 输出的命题 JSON
    python write_propositions.py --input props.json --output knowledge-graph/kg-proposition/propositions/BV1xx.json
    # 从 stdin 读取
    python write_propositions.py --input - --output <path>
    # 直接传字符串
    python write_propositions.py --data '{"source_id": "...", "propositions": [...]}' --output <path>

容错解析：先 json.loads；失败则用 scan_fix_json.fix_json_text 修复裸引号后重试。
落盘：json.dumps(ensure_ascii=False, indent=2)，随后 json.load 复验。
"""
import argparse
import json
import sys
from pathlib import Path

from scan_fix_json import fix_json_text

# 每个命题必需的字段（缺则报错，不自动补）
_REQUIRED_PROP_FIELDS = ["subject", "relation", "object"]


def read_input(args) -> str:
    """读取 LLM 输出的原始文本。优先级：--data > --input 文件/stdin。"""
    if args.data is not None:
        return args.data
    if args.input == "-":
        return sys.stdin.read()
    with open(args.input, encoding="utf-8") as f:
        return f.read()


def parse_propositions(text: str) -> dict:
    """容错解析：json.loads → 失败 → 全面修复非法字符 → 重试。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        fixed, nfix = fix_json_text(text)
        if nfix == 0:
            raise
        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            raise ValueError(f"容错解析后仍失败（修复 {nfix} 处非法字符无效）: {e}") from e


def fill_metadata(data: dict, source_id: str | None) -> dict:
    """补全顶层元数据与命题 id，保证输出结构完整。"""
    data = dict(data)
    sid = source_id or data.get("source_id")
    if not sid:
        raise ValueError("缺少 source_id：请在数据中提供或通过 --source-id 指定")

    props = data.get("propositions")
    if not isinstance(props, list) or not props:
        raise ValueError("propositions 必须是非空数组")

    # 校验必需字段
    for i, p in enumerate(props):
        if not isinstance(p, dict):
            raise ValueError(f"propositions[{i}] 不是对象")
        for field in _REQUIRED_PROP_FIELDS:
            if field not in p:
                raise ValueError(f"propositions[{i}] 缺少必需字段: {field}")

    # 补命题 id
    for i, p in enumerate(props, start=1):
        if not p.get("id"):
            p["id"] = f"{sid}_p{i:03d}"

    data["source_id"] = sid
    data["proposition_count"] = data.get("proposition_count", len(props))
    data["segments"] = data.get("segments", len({p.get("segment_id") for p in props}))
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM 命题提炼 → 合法 JSON 落盘")
    parser.add_argument("--data", help="LLM 输出的命题 JSON 字符串（优先级最高）")
    parser.add_argument("--input", help="LLM 输出文件路径，或 '-' 表示 stdin")
    parser.add_argument("--output", required=True, help="落盘路径（JSON 文件）")
    parser.add_argument("--source-id", help="强制 source_id（覆盖数据内的）")
    args = parser.parse_args()

    if args.data is None and args.input is None:
        parser.error("必须提供 --data 或 --input")

    text = read_input(args)
    if not text.strip():
        parser.error("输入为空")

    data = parse_propositions(text)
    data = fill_metadata(data, args.source_id)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 复验：落盘文件必须能 json.load
    with open(out, encoding="utf-8") as f:
        json.load(f)

    print(f"✓ 落盘成功: {out}")
    print(f"  source_id={data['source_id']}  命题数={len(data['propositions'])}  "
          f"segments={data['segments']}")
    print("  已通过 json.load 复验，文件为合法 JSON")


if __name__ == "__main__":
    main()