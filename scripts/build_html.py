#!/usr/bin/env python3
"""
把 resource/ 下的试题 MD 文件转换为带"一键展开/收起"按钮的 HTML 文件，
输出到 docs/ 目录，供 GitHub Pages 部署。

用法：
    python3 scripts/build_html.py
"""

import re
import shutil
from pathlib import Path

import markdown
from markdown.extensions import tables, fenced_code

# ──────────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
RESOURCE_DIR = ROOT / "resource"
DOCS_DIR = ROOT / "docs"
# ──────────────────────────────────────────────────────────────────────────────

# HTML 页面模板
PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: #f6f8fa;
    color: #24292e;
    line-height: 1.7;
  }}
  .toolbar {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: #24292e;
    padding: 10px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    box-shadow: 0 2px 6px rgba(0,0,0,.3);
  }}
  .toolbar a {{
    color: #8b949e;
    text-decoration: none;
    font-size: 14px;
    margin-right: 8px;
  }}
  .toolbar a:hover {{ color: #fff; }}
  .toolbar span {{ color: #8b949e; font-size: 13px; }}
  .btn {{
    padding: 5px 14px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: background .15s;
  }}
  .btn-expand {{ background: #2ea44f; color: #fff; }}
  .btn-expand:hover {{ background: #2c974b; }}
  .btn-collapse {{ background: #0969da; color: #fff; }}
  .btn-collapse:hover {{ background: #0860ca; }}
  .btn-quiz {{ background: #9a6700; color: #fff; display: none; }}
  .btn-quiz:hover {{ background: #7d5300; }}
  .content {{
    max-width: 860px;
    margin: 30px auto;
    background: #fff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 30px 40px;
  }}
  h1 {{ font-size: 1.6em; border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; margin-bottom: 20px; }}
  h2 {{ font-size: 1.25em; margin: 28px 0 12px; border-bottom: 1px solid #e1e4e8; padding-bottom: 6px; }}
  h3 {{ font-size: 1.05em; margin: 22px 0 8px; color: #0550ae; }}
  p {{ margin: 8px 0; }}
  ul, ol {{ padding-left: 24px; margin: 8px 0; }}
  li {{ margin: 4px 0; }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    font-size: 14px;
  }}
  th, td {{
    border: 1px solid #d0d7de;
    padding: 8px 12px;
    text-align: left;
  }}
  th {{ background: #f6f8fa; font-weight: 600; }}
  tr:nth-child(even) td {{ background: #f9fafb; }}
  blockquote {{
    border-left: 4px solid #d0d7de;
    margin: 10px 0;
    padding: 6px 16px;
    color: #57606a;
    background: #f6f8fa;
    border-radius: 0 4px 4px 0;
  }}
  code {{
    font-family: "SFMono-Regular", Consolas, monospace;
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 1px 5px;
    font-size: 85%;
  }}
  pre {{ background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px;
         padding: 14px; overflow-x: auto; margin: 12px 0; }}
  pre code {{ background: none; border: none; padding: 0; }}
  hr {{ border: none; border-top: 1px solid #e1e4e8; margin: 20px 0; }}
  details {{
    border: 1px solid #d0d7de;
    border-radius: 6px;
    margin: 10px 0 14px;
    background: #fff;
  }}
  details[open] {{ background: #f0fff4; border-color: #2ea44f; }}
  summary {{
    cursor: pointer;
    padding: 10px 14px;
    font-weight: 600;
    color: #0550ae;
    list-style: none;
    user-select: none;
    border-radius: 6px;
  }}
  summary::-webkit-details-marker {{ display: none; }}
  summary::before {{ content: "▶ "; font-size: 11px; }}
  details[open] summary::before {{ content: "▼ "; }}
  details[open] summary {{ border-bottom: 1px solid #d0d7de; border-radius: 6px 6px 0 0; }}
  .details-body {{ padding: 14px 18px; }}
  strong {{ color: #1a1a1a; }}

  /* ── 做题模式 ── */
  .qz-row {{
    display: none;
    align-items: center;
    gap: 6px 12px;
    flex-wrap: wrap;
    margin: 8px 0 10px;
    padding: 10px 14px;
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
  }}
  .quiz-mode .qz-row {{ display: flex; }}
  .qz-label {{ font-size: 13px; color: #57606a; white-space: nowrap; }}
  .qz-opt {{
    cursor: pointer;
    font-size: 14px;
    padding: 3px 10px;
    border-radius: 4px;
    user-select: none;
  }}
  .qz-opt:hover {{ background: #e1e4e8; }}
  .qz-opt input {{ margin-right: 3px; cursor: pointer; }}
  .qz-status {{ font-size: 13px; margin-left: 4px; }}
  .qz-ok {{ color: #2ea44f; font-weight: 600; }}
  .qz-err {{ color: #cf222e; font-weight: 600; }}
  .qz-none {{ color: #57606a; }}
  .qz-row.qz-correct {{ background: #f0fff4; border-color: #2ea44f; }}
  .qz-row.qz-wrong {{ background: #fff0f0; border-color: #cf222e; }}
  .quiz-mode .btn-expand,
  .quiz-mode .btn-collapse {{ opacity: .35; pointer-events: none; }}
  #qz-footer {{
    display: none;
    margin-top: 30px;
    padding: 18px 0 4px;
    border-top: 2px solid #e1e4e8;
    text-align: center;
  }}
  .quiz-mode #qz-footer {{ display: block; }}
  #qz-score {{
    display: inline-block;
    margin: 0 12px;
    font-size: 16px;
    font-weight: 700;
    color: #24292e;
    vertical-align: middle;
  }}
  .btn-submit {{ background: #cf222e; color: #fff; }}
  .btn-submit:hover {{ background: #a40e26; }}
  .btn-retry {{ background: #9a6700; color: #fff; }}
  .btn-retry:hover {{ background: #7d5300; }}
</style>
</head>
<body>
<div class="toolbar">
  <a href="{index_href}">⬅ 返回目录</a>
  <button class="btn btn-expand" onclick="toggleAll(true)">📖 展开全部答案</button>
  <button class="btn btn-collapse" onclick="toggleAll(false)">📕 收起全部答案</button>
  <button class="btn btn-quiz" id="btn-quiz" onclick="quizToggle()">📝 做题模式</button>
  <span id="status"></span>
</div>
<div class="content">
{body}
</div>
<script>
/* ── 展开 / 收起 ── */
function toggleAll(open) {{
  var details = document.querySelectorAll('details');
  details.forEach(function(d) {{ d.open = open; }});
  var s = document.getElementById('status');
  s.textContent = open
    ? ('已展开 ' + details.length + ' 个答案')
    : ('已收起 ' + details.length + ' 个答案');
  setTimeout(function() {{ s.textContent = ''; }}, 2000);
}}

/* ── 做题模式 ── */
(function () {{
  'use strict';
  var _qs = []; /* {{qNum, det, row, answer}} */

  function buildQuizUI() {{
    var allDetails = document.querySelectorAll('details');
    allDetails.forEach(function (det) {{
      var bodyEl = det.querySelector('.details-body');
      if (!bodyEl) return;
      var m = bodyEl.textContent.match(/答案[：:]\\s*([ABCD])/);
      if (!m) return;
      var answer = m[1];

      /* 从前面的 h3 读取题号 */
      var qNum = _qs.length + 1;
      var prev = det.previousElementSibling;
      while (prev) {{
        if (prev.tagName === 'H3') {{
          var nm = prev.textContent.match(/第\\s*(\\d+)\\s*题/);
          if (nm) qNum = parseInt(nm[1], 10);
          break;
        }}
        prev = prev.previousElementSibling;
      }}

      /* 构建选项行 */
      var row = document.createElement('div');
      row.className = 'qz-row';
      row.dataset.answer = answer;
      row.dataset.qnum = qNum;

      var lbl = document.createElement('span');
      lbl.className = 'qz-label';
      lbl.textContent = '我的答案：';
      row.appendChild(lbl);

      ['A', 'B', 'C', 'D'].forEach(function (opt) {{
        var label = document.createElement('label');
        label.className = 'qz-opt';
        var inp = document.createElement('input');
        inp.type = 'radio';
        inp.name = 'q' + qNum;
        inp.value = opt;
        label.appendChild(inp);
        label.appendChild(document.createTextNode('\u00a0' + opt));
        row.appendChild(label);
      }});

      var st = document.createElement('span');
      st.className = 'qz-status';
      row.appendChild(st);

      det.parentNode.insertBefore(row, det);
      _qs.push({{ qNum: qNum, det: det, row: row, answer: answer }});
    }});

    if (!_qs.length) return;

    /* 显示做题模式按钮 */
    document.getElementById('btn-quiz').style.display = 'inline-block';

    /* 页尾提交栏 */
    var footer = document.createElement('div');
    footer.id = 'qz-footer';
    footer.innerHTML =
      '<button class="btn btn-submit" id="btn-submit" onclick="quizSubmit()">✅ 提交答案</button>' +
      '<span id="qz-score"></span>' +
      '<button class="btn btn-retry" id="btn-retry" onclick="quizRetry()" style="display:none">🔄 重新作答</button>';
    document.querySelector('.content').appendChild(footer);
  }}

  window.quizToggle = function () {{
    var active = document.body.classList.toggle('quiz-mode');
    var btn = document.getElementById('btn-quiz');
    btn.textContent = active ? '📖 退出做题模式' : '📝 做题模式';
    if (active) {{
      /* 进入做题模式：收起所有答案 */
      document.querySelectorAll('details').forEach(function (d) {{ d.open = false; }});
      quizRetry();
    }}
  }};

  window.quizSubmit = function () {{
    var correct = 0, answered = 0;
    _qs.forEach(function (q) {{
      var sel = document.querySelector('input[name="q' + q.qNum + '"]:checked');
      var st = q.row.querySelector('.qz-status');
      q.row.classList.remove('qz-correct', 'qz-wrong');
      if (!sel) {{
        st.textContent = '⬜ 未作答';
        st.className = 'qz-status qz-none';
        return;
      }}
      answered++;
      if (sel.value === q.answer) {{
        correct++;
        st.textContent = '✅ 正确';
        st.className = 'qz-status qz-ok';
        q.row.classList.add('qz-correct');
      }} else {{
        st.textContent = '❌ 错误，正确答案：' + q.answer;
        st.className = 'qz-status qz-err';
        q.row.classList.add('qz-wrong');
        q.det.open = true; /* 展开解析 */
      }}
    }});
    var total = _qs.length;
    var pct = answered ? Math.round(correct / answered * 100) : 0;
    var scoreEl = document.getElementById('qz-score');
    scoreEl.textContent = answered === total
      ? ('得分：' + correct + ' / ' + total + '（正确率\u00a0' + pct + '%）')
      : ('得分：' + correct + ' / ' + answered + '\u00a0已答（共\u00a0' + total + '\u00a0题，正确率\u00a0' + pct + '%）');
    document.getElementById('btn-retry').style.display = '';
    document.getElementById('btn-submit').style.display = 'none';
    document.getElementById('qz-footer').scrollIntoView({{ behavior: 'smooth' }});
  }};

  window.quizRetry = function () {{
    _qs.forEach(function (q) {{
      q.row.querySelectorAll('input[type=radio]').forEach(function (r) {{ r.checked = false; }});
      var st = q.row.querySelector('.qz-status');
      st.textContent = '';
      st.className = 'qz-status';
      q.row.classList.remove('qz-correct', 'qz-wrong');
      q.det.open = false;
    }});
    var scoreEl = document.getElementById('qz-score');
    if (scoreEl) scoreEl.textContent = '';
    var retryBtn = document.getElementById('btn-retry');
    if (retryBtn) retryBtn.style.display = 'none';
    var submitBtn = document.getElementById('btn-submit');
    if (submitBtn) submitBtn.style.display = '';
  }};

  document.addEventListener('DOMContentLoaded', buildQuizUI);
}})();
</script>
</body>
</html>
"""

# 首页模板
INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>信息系统项目管理师 · 近五年真题练习</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: #f6f8fa;
    color: #24292e;
    line-height: 1.7;
  }}
  .hero {{
    background: linear-gradient(135deg, #0550ae 0%, #2ea44f 100%);
    color: #fff;
    text-align: center;
    padding: 50px 20px 40px;
  }}
  .hero h1 {{ font-size: 1.9em; margin-bottom: 8px; }}
  .hero p {{ opacity: .85; font-size: 15px; }}
  .container {{ max-width: 860px; margin: 30px auto; padding: 0 20px 40px; }}
  .year-group {{ margin-bottom: 28px; }}
  .year-group h2 {{
    font-size: 1.1em;
    color: #0550ae;
    border-bottom: 2px solid #0550ae;
    padding-bottom: 6px;
    margin-bottom: 12px;
  }}
  .card-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }}
  .card {{
    background: #fff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 16px 20px;
    text-decoration: none;
    color: #24292e;
    transition: border-color .2s, box-shadow .2s;
  }}
  .card:hover {{ border-color: #0550ae; box-shadow: 0 3px 10px rgba(0,0,0,.08); }}
  .card .type {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .5px;
    margin-bottom: 4px;
  }}
  .card .type.zh {{ color: #2ea44f; }}
  .card .type.al {{ color: #0550ae; }}
  .card .name {{ font-size: 15px; font-weight: 600; }}
  .tip {{
    background: #fff8c5;
    border: 1px solid #f0c800;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 24px;
    font-size: 14px;
    color: #633c00;
  }}
</style>
</head>
<body>
<div class="hero">
  <h1>📚 信息系统项目管理师 · 近五年真题</h1>
  <p>答案默认折叠 · 支持逐题展开 · 支持一键展开/收起全部</p>
</div>
<div class="container">
  <div class="tip">
    💡 <strong>使用方法：</strong>
    点击题目页面顶部工具栏的 <strong>「展开全部答案」</strong> / <strong>「收起全部答案」</strong> 按钮，
    或点击每道题下方的 <strong>「查看答案与解析」</strong> 逐题核对。
  </div>
{year_groups}
</div>
</body>
</html>
"""


# ──────────────────────────────────────────────────────────────────────────────
# MD → HTML 转换
# ──────────────────────────────────────────────────────────────────────────────

_MD_EXT = ["tables", "fenced_code", "nl2br", "sane_lists", "attr_list"]

# <details> 里的 Markdown 不会被标准 python-markdown 自动渲染，需要手动处理
_DETAILS_RE = re.compile(
    r"<details>(.*?)</details>", re.DOTALL
)


def md_to_html(text: str) -> str:
    """先把 <details> 块里的内容也转成 HTML，再整体转换。"""
    def convert_details_block(m: re.Match) -> str:
        inner = m.group(1)
        # 提取 summary 行
        sm = re.search(r"<summary>(.*?)</summary>", inner, re.DOTALL)
        summary_text = sm.group(1).strip() if sm else "查看答案"
        # 剩余内容（去掉 summary 标签）
        body_md = re.sub(r"<summary>.*?</summary>", "", inner, flags=re.DOTALL).strip()
        body_html = markdown.markdown(body_md, extensions=_MD_EXT)
        return (
            f"<details>\n"
            f"<summary>{summary_text}</summary>\n"
            f'<div class="details-body">\n{body_html}\n</div>\n'
            f"</details>"
        )

    # 先转换 <details> 内部
    text = _DETAILS_RE.sub(convert_details_block, text)
    # 再整体转换 Markdown（<details> 块已是 HTML，会被保留）
    html = markdown.markdown(text, extensions=_MD_EXT)
    return html


# ──────────────────────────────────────────────────────────────────────────────
# 文件结构扫描
# ──────────────────────────────────────────────────────────────────────────────

def get_exam_files():
    """返回按年份分组的考试文件列表。"""
    source_dirs = [
        RESOURCE_DIR / "近五年真题_文字版整理",
    ]
    groups: dict[str, list[dict]] = {}

    for base in source_dirs:
        if not base.exists():
            continue
        for md_file in sorted(base.rglob("*.md")):
            if md_file.name.startswith("00_"):
                continue
            # 提取年份：取相对路径第一层目录
            rel = md_file.relative_to(base)
            parts = rel.parts
            year = parts[0]  # e.g. "2023上"
            batch = "/".join(parts[1:-1])  # e.g. "主卷" or "第一批次"
            name = md_file.stem  # e.g. "综合知识" "案例分析"

            label = f"{year} {batch} · {name}" if batch else f"{year} · {name}"
            is_zhishi = "综合" in name

            groups.setdefault(year, []).append({
                "label": label,
                "name": name,
                "year": year,
                "batch": batch,
                "is_zhishi": is_zhishi,
                "source": md_file,
                # output path relative to docs/
                "out_rel": Path(year) / batch / f"{name}.html",
            })

    return groups


# ──────────────────────────────────────────────────────────────────────────────
# 构建
# ──────────────────────────────────────────────────────────────────────────────

def build():
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)

    groups = get_exam_files()
    year_groups_html = ""

    for year in sorted(groups.keys()):
        files = groups[year]
        cards_html = ""
        for f in files:
            out_path = DOCS_DIR / f["out_rel"]
            out_path.parent.mkdir(parents=True, exist_ok=True)

            # 转换 MD 到 HTML
            md_content = f["source"].read_text(encoding="utf-8")
            body_html = md_to_html(md_content)
            page_title = f["label"]
            # 计算返回首页的相对路径（out_rel 深度为 2：year/batch/name.html）
            depth = len(f["out_rel"].parts) - 1  # 目录层级数
            index_href = "../" * depth + "index.html"
            html = PAGE_TEMPLATE.format(title=page_title, body=body_html,
                                        index_href=index_href)
            out_path.write_text(html, encoding="utf-8")
            print(f"  📄 {out_path.relative_to(ROOT)}")

            type_cls = "zh" if f["is_zhishi"] else "al"
            type_name = "综合知识" if f["is_zhishi"] else "案例分析"
            href = str(f["out_rel"]).replace("\\", "/")
            cards_html += (
                f'<a class="card" href="{href}">'
                f'<div class="type {type_cls}">{type_name}</div>'
                f'<div class="name">{f["year"]} {f["batch"]}</div>'
                f"</a>\n"
            )

        year_groups_html += (
            f'<div class="year-group">'
            f'<h2>{year}</h2>'
            f'<div class="card-grid">{cards_html}</div>'
            f"</div>\n"
        )

    # 写 index.html
    index_html = INDEX_TEMPLATE.format(year_groups=year_groups_html)
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"\n  🏠 {(DOCS_DIR / 'index.html').relative_to(ROOT)}")
    print(f"\n✅ 构建完成，共 {sum(len(v) for v in groups.values())} 个页面。")


if __name__ == "__main__":
    build()
