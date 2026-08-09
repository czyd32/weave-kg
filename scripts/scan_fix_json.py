"""
KG 命题 JSON 校验与修复工具。

问题根源：入库管道生成命题 JSON 时，若直接用 LLM 输出的原始文本落盘（未
经 json.dumps 转义），内容字段（subject/object/cause/original_text）内部
混入的英文双引号就不会被转义，导致 json.load 崩溃。典型报错：
    JSONDecodeError: Expecting ',' delimiter: line N column M

影响面（三处消费命题 JSON，坏文件均会中断）：
- query.py          富化阶段 json.load 失败 → 查询中断
- run_matching_pipeline.py  建索引 load_propositions → 向量构建中断
- run_evolution_tracker.py  演化追踪 load propositions → 中断

用法：
    # 仅扫描（默认）
    python scan_fix_json.py --dir knowledge-graph/kg-proposition --recursive
    # 扫描 + 修复
    python scan_fix_json.py --dir knowledge-graph/kg-proposition --recursive --fix
    # 从 backup 恢复被修复的文件
    python scan_fix_json.py --restore

修复策略：状态机检测字符串值内部的孤立英文双引号，成对替换为中文引号「」。
修复前自动备份原文件到 temp/fix_backup/<stem>.orig.json。
修复后必须能 json.load 通过才落盘；仍失败的保留原文件，标记需人工处理。
"""
import argparse
import json
import shutil
from pathlib import Path

# 备份根目录（gitignored，避免污染知识图谱结构）
_BACKUP_ROOT = Path("temp/fix_backup")

# 递归扫描时跳过的目录名
_EXCLUDE_DIR_NAMES = {"temp", "fix_backup", "_backup", "_backup_20260808",
                      "_ingest", "_shared", ".git", ".idea", "__pycache__",
                      "node_modules", "backup", "backups"}


# JSON 合法单字符转义
_VALID_ESCAPES = set('"\\/bfnrt')
# 字符串内裸控制字符 → 语义等价转义
_CTRL_ESCAPES = {"\n": "\\n", "\t": "\\t", "\r": "\\r", "\b": "\\b",
                 "\f": "\\f"}
# 结构终止引号后（跳过空白）允许紧跟的 JSON 结构字符
_STRUCT_CHARS = ",:}]"


def fix_json_text(text: str) -> tuple[str, int]:
    """修复常见 JSON 非法字符（状态机，字符串内/外分别处理）。

    处理 4 类问题：
    1. 字符串内部孤立的英文双引号 → 中文引号「」成对
    2. 字符串内部裸控制字符（<0x20，如真实换行/制表）→ 转义为 \\n/\\t/\\uXXXX
    3. 字符串内部非法转义（\\ 后跟非 JSON 转义字符）→ 转义 \\ 为 \\\\
    4. 结构层尾部逗号（,} 或 ,]）→ 删除

    返回 (修复后文本, 修复处数)。"""
    out = []
    n = len(text)
    i = 0
    in_string = False
    open_par = False
    fixed = 0
    while i < n:
        ch = text[i]
        if in_string:
            if ch == "\\":
                if i + 1 >= n:
                    out.append("\\\\")
                    fixed += 1
                    i += 1
                    continue
                nxt = text[i + 1]
                if nxt == "u":
                    hex_part = text[i + 2:i + 6]
                    if len(hex_part) == 4 and all(c in "0123456789abcdefABCDEF" for c in hex_part):
                        out.append(text[i:i + 6])
                        i += 6
                    else:
                        out.append("\\\\")
                        fixed += 1
                        i += 1
                    continue
                if nxt in _VALID_ESCAPES:
                    out.append(ch)
                    out.append(nxt)
                    i += 2
                    continue
                out.append("\\\\")
                fixed += 1
                i += 1
                continue
            if ch == '"':
                j = i + 1
                while j < n and text[j] in " \t\n\r":
                    j += 1
                if j >= n or text[j] in _STRUCT_CHARS:
                    out.append(ch)
                    in_string = False
                    open_par = False
                else:
                    out.append("\u201d" if open_par else "\u201c")
                    open_par = not open_par
                    fixed += 1
                i += 1
                continue
            if ord(ch) < 0x20:
                out.append(_CTRL_ESCAPES.get(ch, f"\\u{ord(ch):04x}"))
                fixed += 1
                i += 1
                continue
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\n\r":
                j += 1
            if j < n and text[j] in "}]":
                fixed += 1
                i += 1
                continue
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out), fixed


def _fix_quotes(text: str) -> tuple[str, int]:
    """兼容别名：仅修复孤立引号的旧接口，内部委托 fix_json_text。"""
    return fix_json_text(text)


def _collect_json_files(directory: str, recursive: bool) -> list[Path]:
    if not recursive:
        return sorted(Path(directory).glob("*.json"))
    root = Path(directory)
    files = []
    for p in sorted(root.rglob("*.json")):
        rel_dirs = p.relative_to(root).parts[:-1]
        if any(part in _EXCLUDE_DIR_NAMES for part in rel_dirs):
            continue
        files.append(p)
    return files


def scan_dir(directory: str, recursive: bool = False) -> tuple[list[Path], list[tuple[Path, str]]]:
    """返回 (ok_list, bad_list)。bad_list 元素为 (path, error_msg)。"""
    ok, bad = [], []
    for p in _collect_json_files(directory, recursive):
        try:
            with open(p, encoding="utf-8") as f:
                json.load(f)
            ok.append(p)
        except Exception as e:
            bad.append((p, str(e)))
    return ok, bad


def normalize_dir(directory: str, recursive: bool = False) -> None:
    """批量修复：扫描文件夹内所有 JSON，坏文件修复后直接覆盖原文件。"""
    files = _collect_json_files(directory, recursive)
    if not files:
        print(f"目录 {directory} 下无 JSON 文件")
        return
    _BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    changed, skipped = [], []
    for p in files:
        raw = p.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            fixed_text, nfix = fix_json_text(raw)
            if nfix == 0:
                skipped.append((p, "无法修复"))
                continue
            try:
                data = json.loads(fixed_text)
            except json.JSONDecodeError as e:
                skipped.append((p, str(e)))
                continue
        else:
            continue
        normalized = json.dumps(data, ensure_ascii=False, indent=2)
        backup = _BACKUP_ROOT / f"{p.stem}.orig.json"
        backup.write_text(raw, encoding="utf-8")
        p.write_text(normalized + "\n", encoding="utf-8")
        changed.append(p)

    print(f"批量修复: 目录 {directory}{' (递归)' if recursive else ''}")
    print(f"总文件: {len(files)}  已修复覆盖: {len(changed)}  跳过: {len(skipped)}")
    if skipped:
        print("跳过（需人工处理）：")
        for p, why in skipped:
            print(f"  - {p}  [{why}]")
    if changed:
        print("备份位置: temp/fix_backup/（可用 --restore 恢复）")


def _restore() -> int:
    """从 temp/fix_backup/ 恢复被修复的文件。返回恢复数。"""
    if not _BACKUP_ROOT.exists():
        print("无备份目录，无需恢复")
        return 0
    restored = 0
    for backup in sorted(_BACKUP_ROOT.glob("*.orig.json")):
        target = backup.with_name(backup.name.replace(".orig.json", ".json"))
        if not target.exists():
            print(f"  跳过（目标不存在）: {target}")
            continue
        shutil.copy(backup, target)
        restored += 1
        print(f"  恢复 {target}  ← {backup}")
    if restored:
        print(f"共恢复 {restored} 个文件")
    else:
        print("无匹配的历史备份")
    return restored


def main() -> None:
    parser = argparse.ArgumentParser(description="扫描/修复知识图谱坏 JSON")
    parser.add_argument("--dir", help="要扫描的目录（--restore 时忽略）")
    parser.add_argument("--recursive", action="store_true", help="递归扫描子目录")
    parser.add_argument("--fix", action="store_true", help="修复坏文件并原地覆盖")
    parser.add_argument("--normalize", action="store_true", help="批量规范化：文件夹内所有 JSON 统一重写并原地覆盖")
    parser.add_argument("--restore", action="store_true", help="从 temp/fix_backup/ 恢复历史备份")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.restore:
        _restore()
        return

    if not args.dir:
        parser.error("--dir 或 --restore 必选其一")

    if args.normalize:
        normalize_dir(args.dir, args.recursive)
        return

    ok, bad = scan_dir(args.dir, args.recursive)
    total = len(ok) + len(bad)
    print(f"扫描目录: {args.dir}{' (递归)' if args.recursive else ''}")
    print(f"总文件: {total}, 正常: {len(ok)}, 坏: {len(bad)}")

    if not bad:
        print("OK 未发现坏 JSON")
        return

    fixed_ok, fixed_fail = [], []
    for p, err in bad:
        print(f"\nBAD {p}:\n  原因: {err}")
        if not args.fix:
            continue
        with open(p, encoding="utf-8") as f:
            raw = f.read()
        fixed_text, nfix = _fix_quotes(raw)
        if nfix == 0:
            print("  SKIP 未检测到可修复的孤立引号，需人工处理")
            fixed_fail.append((p, "no_isolated_quote"))
            continue
        try:
            json.loads(fixed_text)
        except Exception as e2:
            print(f"  FAIL 修复后仍无法解析: {e2}（保留原文件，需人工处理）")
            fixed_fail.append((p, str(e2)))
            continue
        _BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        backup = _BACKUP_ROOT / f"{p.stem}.orig.json"
        with open(backup, "w", encoding="utf-8") as f:
            f.write(raw)
        with open(p, "w", encoding="utf-8") as f:
            f.write(fixed_text)
        fixed_ok.append(p)
        print(f"  FIX 修复 {nfix} 处孤立引号 → 中文引号「」（备份: {backup}）")

    print("\n===== 汇总 =====")
    print(f"可修复: {len(fixed_ok)}  需人工: {len(fixed_fail)}")
    if fixed_fail:
        print("需人工处理的文件：")
        for p, why in fixed_fail:
            print(f"  - {p}  [{why}]")
    if fixed_ok:
        print("请复核修复结果，并同步重建向量索引")


if __name__ == "__main__":
    main()