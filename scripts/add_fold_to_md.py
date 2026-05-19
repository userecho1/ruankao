#!/usr/bin/env python3
"""
给近五年真题和题库的 MD 文件添加 <details> 折叠标签，
使每道题/每个问题的答案默认折叠，在 GitHub 上逐题展开查看。

用法：
    python3 scripts/add_fold_to_md.py
"""

import re
import sys
from pathlib import Path

RESOURCE_DIR = Path(__file__).parent.parent / "resource"

# 已处理标记，防止重复运行时重复折叠
FOLD_MARKER = "<details>"


def already_folded(content: str) -> bool:
    return FOLD_MARKER in content


# ──────────────────────────────────────────────────────────────────────────────
# 综合知识类文件（含 Q1/第N题 风格）
# 规则：找到以 **答案： 开头的行，把它到下一个 --- 之间的内容包进 <details>
# ──────────────────────────────────────────────────────────────────────────────

_ANSWER_START = re.compile(r"^\*\*答案[：:]")
_QUESTION_HEADING = re.compile(r"^### (第\d+题|Q\d)")
_SEPARATOR = re.compile(r"^---\s*$")


def process_zhishi(content: str) -> str:
    """处理综合知识风格文件：逐题折叠答案+解析。"""
    if already_folded(content):
        return content

    lines = content.split("\n")
    result: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if _ANSWER_START.match(line):
            # 收集答案块（到下一个 --- 或下一题标题为止）
            block: list[str] = []
            j = i
            while j < len(lines):
                if _SEPARATOR.match(lines[j]) or (
                    j > i and _QUESTION_HEADING.match(lines[j])
                ):
                    break
                block.append(lines[j])
                j += 1
            # 去掉块末尾的空行
            while block and block[-1].strip() == "":
                block.pop()

            result.append("<details>")
            result.append("<summary>查看答案与解析</summary>")
            result.append("")
            result.extend(block)
            result.append("")
            result.append("</details>")
            result.append("")
            i = j
        else:
            result.append(line)
            i += 1

    return "\n".join(result)


# ──────────────────────────────────────────────────────────────────────────────
# 案例分析类文件
# 规则：在 ### 问题N 标题下，把正文内容包进 <details>
# ──────────────────────────────────────────────────────────────────────────────

_PROBLEM_HEADING = re.compile(r"^### 问题\d+")
_SECTION_HEADING = re.compile(r"^## ")


def process_anli(content: str) -> str:
    """处理案例分析风格文件：每个 ### 问题N 的答案内容折叠。"""
    if already_folded(content):
        return content

    lines = content.split("\n")
    result: list[str] = []
    i = 0

    # 记录是否已进入答案区（文字版整理有 ## 参考答案与解析 分隔）
    in_answer_section = False

    while i < len(lines):
        line = lines[i]

        # 进入答案区判断（针对 文字版整理 文件）
        if re.match(r"^## 参考答案", line):
            in_answer_section = True
            result.append(line)
            i += 1
            continue

        # 近五年真题 案例分析_答案解析 文件直接从头就是答案，识别 ## 案例X 也算进入
        if re.match(r"^## 案例[一二三四五六七八九十]", line):
            in_answer_section = True
            result.append(line)
            i += 1
            continue

        # 在答案区内，遇到 ### 问题N 标题，折叠其内容
        if in_answer_section and _PROBLEM_HEADING.match(line):
            result.append(line)
            i += 1
            # 收集这个问题的答案内容
            block: list[str] = []
            while i < len(lines):
                cur = lines[i]
                if (
                    _SEPARATOR.match(cur)
                    or _PROBLEM_HEADING.match(cur)
                    or _SECTION_HEADING.match(cur)
                ):
                    break
                block.append(cur)
                i += 1
            # 去掉首尾空行
            while block and block[0].strip() == "":
                block.pop(0)
            while block and block[-1].strip() == "":
                block.pop()

            if block:
                result.append("")
                result.append("<details>")
                result.append("<summary>查看参考答案</summary>")
                result.append("")
                result.extend(block)
                result.append("")
                result.append("</details>")
                result.append("")
        else:
            result.append(line)
            i += 1

    return "\n".join(result)


# ──────────────────────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────────────────────

def process_file(path: Path) -> bool:
    """处理单个文件，返回是否有修改。"""
    original = path.read_text(encoding="utf-8")
    name = path.name.lower()

    if "综合知识" in path.name or "q1" in name or "q2" in name or "题库" in str(path):
        processed = process_zhishi(original)
    elif "案例分析" in path.name:
        processed = process_anli(original)
    else:
        return False

    if processed != original:
        path.write_text(processed, encoding="utf-8")
        print(f"  ✅ 已处理: {path.relative_to(RESOURCE_DIR.parent)}")
        return True
    else:
        print(f"  ⏭  跳过(已处理或无匹配): {path.relative_to(RESOURCE_DIR.parent)}")
        return False


def main():
    target_dirs = [
        RESOURCE_DIR / "近五年真题",
        RESOURCE_DIR / "近五年真题_文字版整理",
        RESOURCE_DIR / "题库",
    ]

    changed = 0
    for d in target_dirs:
        if not d.exists():
            continue
        for md_file in sorted(d.rglob("*.md")):
            if process_file(md_file):
                changed += 1

    print(f"\n共修改 {changed} 个文件。")


if __name__ == "__main__":
    main()
