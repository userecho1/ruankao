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
<title>信息系统项目管理师 · 备考复习</title>
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
  .hero .nav-tabs {{
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-top: 20px;
    flex-wrap: wrap;
  }}
  .hero .nav-tab {{
    background: rgba(255,255,255,.2);
    color: #fff;
    border: 1px solid rgba(255,255,255,.4);
    border-radius: 20px;
    padding: 6px 18px;
    text-decoration: none;
    font-size: 14px;
    font-weight: 600;
    transition: background .2s;
  }}
  .hero .nav-tab:hover, .hero .nav-tab.active {{ background: rgba(255,255,255,.35); }}
  .container {{ max-width: 860px; margin: 30px auto; padding: 0 20px 40px; }}
  .section-title {{
    font-size: 1.3em;
    font-weight: 700;
    color: #24292e;
    margin: 32px 0 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .section-title::after {{
    content: '';
    flex: 1;
    height: 2px;
    background: linear-gradient(90deg, #0550ae, transparent);
    margin-left: 10px;
  }}
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
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
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
    display: block;
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
  .card .type.lw {{ color: #9a3412; }}
  .card .type.wj {{ color: #6e40c9; }}
  .card .type.bg {{ color: #0969da; }}
  .card .name {{ font-size: 15px; font-weight: 600; }}
  .card .desc {{ font-size: 12px; color: #57606a; margin-top: 4px; }}
  .card.essay-card {{ border-left: 3px solid #9a3412; }}
  .card.essay-card:hover {{ border-color: #7c2d12; box-shadow: 0 3px 10px rgba(154,52,18,.15); }}
  .tip {{
    background: #fff8c5;
    border: 1px solid #f0c800;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 24px;
    font-size: 14px;
    color: #633c00;
  }}
  .tip.red {{
    background: #fff0f0;
    border-color: #ff8080;
    color: #7d1a1a;
  }}
  .badge {{
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 10px;
    margin-left: 6px;
    vertical-align: middle;
  }}
  .badge.hot {{ background: #ffecec; color: #cf222e; border: 1px solid #ffb3b3; }}
  .badge.warm {{ background: #fff8e0; color: #9a6700; border: 1px solid #ffd966; }}
</style>
</head>
<body>
<div class="hero">
  <h1>📚 信息系统项目管理师 · 备考复习</h1>
  <p>近五年真题 · 论文范文 · 个性化定制</p>
  <div class="nav-tabs">
    <a class="nav-tab active" href="#exam">📝 真题练习</a>
    <a class="nav-tab" href="#essays">✍️ 论文复习</a>
  </div>
</div>
<div class="container">
  <div class="tip red">
    🔥 <strong>2026考前押题：</strong>
    整合管理（概率最高）、成本管理、进度管理、风险管理 ——
    <a href="essays/index.html" style="color:#7d1a1a;font-weight:700;">点击进入论文复习 →</a>
  </div>

  <div id="essays" class="section-title">✍️ 论文复习</div>
{essay_cards}

  <div id="exam" class="section-title">📝 近五年真题练习</div>
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
# 论文页面模板
# ──────────────────────────────────────────────────────────────────────────────

ESSAY_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · 论文复习</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: #f6f8fa;
    color: #24292e;
    line-height: 1.9;
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
  .toolbar .sep {{ color: #444; font-size: 13px; }}
  .btn {{
    padding: 5px 14px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    transition: background .15s;
  }}
  .btn-print {{ background: #6e40c9; color: #fff; margin-left: auto; }}
  .btn-print:hover {{ background: #5a32a3; }}
  .layout {{
    max-width: 900px;
    margin: 30px auto;
    padding: 0 20px 60px;
    display: grid;
    grid-template-columns: 1fr 220px;
    gap: 24px;
    align-items: start;
  }}
  @media (max-width: 700px) {{
    .layout {{ grid-template-columns: 1fr; }}
    .sidebar {{ display: none; }}
  }}
  .content {{
    background: #fff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 36px 44px;
  }}
  @media print {{
    .toolbar, .sidebar {{ display: none !important; }}
    .layout {{ display: block; max-width: 100%; margin: 0; padding: 0; }}
    .content {{ border: none; padding: 20px; }}
  }}
  h1 {{ font-size: 1.55em; border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; margin-bottom: 20px; }}
  h2 {{ font-size: 1.18em; margin: 28px 0 12px; border-bottom: 1px solid #e1e4e8; padding-bottom: 6px; color: #0550ae; }}
  h3 {{ font-size: 1.02em; margin: 20px 0 8px; color: #0969da; }}
  h4 {{ font-size: .95em; margin: 16px 0 6px; color: #57606a; }}
  p {{ margin: 8px 0; }}
  ul, ol {{ padding-left: 24px; margin: 8px 0; }}
  li {{ margin: 5px 0; }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 14px 0;
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
    border-left: 4px solid #9a3412;
    margin: 12px 0;
    padding: 8px 16px;
    color: #57606a;
    background: #fff8f5;
    border-radius: 0 4px 4px 0;
    font-size: 14px;
  }}
  strong {{ color: #1a1a1a; }}
  .abstract-box {{
    background: #f0f9ff;
    border: 1px solid #b6d9f7;
    border-radius: 8px;
    padding: 18px 22px;
    margin: 16px 0 24px;
    font-size: 15px;
    line-height: 1.85;
  }}
  .abstract-label {{
    font-size: 12px;
    font-weight: 700;
    color: #0550ae;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }}
  hr {{ border: none; border-top: 1px solid #e1e4e8; margin: 20px 0; }}
  /* sidebar */
  .sidebar {{
    position: sticky;
    top: 60px;
  }}
  .sidebar-card {{
    background: #fff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 14px;
    font-size: 13px;
  }}
  .sidebar-card h4 {{
    font-size: 12px;
    font-weight: 700;
    color: #0550ae;
    text-transform: uppercase;
    letter-spacing: .5px;
    margin-bottom: 10px;
    color: #9a3412;
  }}
  .sidebar-card ul {{
    padding-left: 16px;
    color: #57606a;
  }}
  .sidebar-card li {{ margin: 5px 0; line-height: 1.5; }}
  .prob-bar {{
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 5px 0;
    font-size: 12px;
    color: #57606a;
  }}
  .prob-fill {{
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(90deg, #cf222e, #ff9800);
  }}
  .nav-btns {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }}
  .nav-btns a {{
    flex: 1;
    text-align: center;
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px 10px;
    text-decoration: none;
    color: #24292e;
    font-size: 13px;
    transition: border-color .2s;
  }}
  .nav-btns a:hover {{ border-color: #9a3412; color: #9a3412; }}
</style>
</head>
<body>
<div class="toolbar">
  <a href="../index.html">⬅ 返回首页</a>
  <span class="sep">|</span>
  <a href="index.html">📋 论文目录</a>
  {prev_next_html}
  <button class="btn btn-print" onclick="window.print()">🖨️ 打印/保存PDF</button>
</div>
<div class="layout">
  <div class="content">
{body}
  </div>
  <aside class="sidebar">
{sidebar_html}
  </aside>
</div>
</body>
</html>
"""

# 论文目录页模板
ESSAY_INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>论文复习 · 信息系统项目管理师</title>
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
    background: linear-gradient(135deg, #7c2d12 0%, #9a3412 50%, #c2410c 100%);
    color: #fff;
    text-align: center;
    padding: 50px 20px 40px;
  }}
  .hero h1 {{ font-size: 1.9em; margin-bottom: 8px; }}
  .hero p {{ opacity: .85; font-size: 15px; }}
  .hero a {{ color: rgba(255,255,255,.75); text-decoration: none; font-size: 14px; }}
  .hero a:hover {{ color: #fff; }}
  .container {{ max-width: 860px; margin: 30px auto; padding: 0 20px 50px; }}
  .tip {{
    background: #fff8e0;
    border: 1px solid #ffd966;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 28px;
    font-size: 14px;
    color: #633c00;
  }}
  .essay-list {{ display: flex; flex-direction: column; gap: 14px; margin-bottom: 32px; }}
  .essay-card {{
    background: #fff;
    border: 1px solid #d0d7de;
    border-left: 4px solid #9a3412;
    border-radius: 8px;
    padding: 18px 22px;
    text-decoration: none;
    color: #24292e;
    transition: box-shadow .2s, border-color .2s;
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }}
  .essay-card:hover {{ box-shadow: 0 4px 12px rgba(154,52,18,.15); border-left-color: #7c2d12; }}
  .essay-num {{
    font-size: 2em;
    font-weight: 900;
    color: #e0e0e0;
    line-height: 1;
    min-width: 40px;
    text-align: center;
  }}
  .essay-info {{ flex: 1; }}
  .essay-title {{ font-size: 1.15em; font-weight: 700; color: #9a3412; margin-bottom: 4px; }}
  .essay-desc {{ font-size: 13px; color: #57606a; line-height: 1.5; }}
  .prob-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
    font-size: 12px;
    color: #57606a;
  }}
  .prob-bar {{
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(90deg, #cf222e, #ff9800);
  }}
  .badge {{
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
  }}
  .badge.must {{ background: #ffd4d4; color: #b91c1c; border: 1px solid #fca5a5; }}
  .badge.good {{ background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }}
  .badge.ok {{ background: #e8f4fd; color: #1e40af; border: 1px solid #93c5fd; }}
  .section-title {{
    font-size: 1.1em;
    font-weight: 700;
    color: #24292e;
    border-bottom: 2px solid #9a3412;
    padding-bottom: 6px;
    margin-bottom: 14px;
  }}
  .tool-card {{
    background: #fff;
    border: 1px solid #d0d7de;
    border-left: 4px solid #6e40c9;
    border-radius: 8px;
    padding: 16px 20px;
    text-decoration: none;
    color: #24292e;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: box-shadow .2s;
  }}
  .tool-card:hover {{ box-shadow: 0 3px 8px rgba(0,0,0,.1); }}
  .tool-icon {{ font-size: 2em; }}
  .tool-title {{ font-size: 1em; font-weight: 700; color: #6e40c9; }}
  .tool-desc {{ font-size: 13px; color: #57606a; }}
</style>
</head>
<body>
<div class="hero">
  <h1>✍️ 论文复习 · 2026押题</h1>
  <p>敏捷项目背景 · 4篇高概率论文 · 个性化定制问卷</p>
  <p style="margin-top:10px"><a href="../index.html">⬅ 返回备考首页</a></p>
</div>
<div class="container">
  <div class="tip">
    📊 <strong>2026考前押题分析：</strong>
    基于近5年命题规律，整合管理（约60%+）是最高概率，其次是成本管理、进度管理（均约40-50%）。
    务必把整合管理背到能在40分钟内完整写出，成本管理的EVM数据要熟练运用。
  </div>

  <div class="section-title">📝 论文范文（按优先级排序）</div>
  <div class="essay-list">
{essay_items}
  </div>

  <div class="section-title" style="margin-top:32px">🛠️ 备考工具</div>
  <div style="display:flex;flex-direction:column;gap:12px;margin-bottom:16px">
    <a class="tool-card" href="问卷.html">
      <span class="tool-icon">📋</span>
      <div>
        <div class="tool-title">个性化定制问卷</div>
        <div class="tool-desc">填写你的实际项目经历，生成专属论文关键参数，让论文更有说服力</div>
      </div>
    </a>
    <a class="tool-card" href="敏捷项目背景.html" style="border-left-color:#0550ae">
      <span class="tool-icon">🏢</span>
      <div>
        <div class="tool-title">敏捷项目背景速查</div>
        <div class="tool-desc">万能项目背景参数表，写作时快速取用数据，4篇论文通用</div>
      </div>
    </a>
  </div>
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

def get_essay_files():
    """返回论文 MD 文件列表，按文件名排序。"""
    essay_dir = RESOURCE_DIR / "论文"
    if not essay_dir.exists():
        return []
    files = []
    for md_file in sorted(essay_dir.glob("*.md")):
        stem = md_file.stem  # e.g. "01_整合管理"
        m = re.match(r"(\d+)_(.+)", stem)
        if not m:
            continue
        num = int(m.group(1))
        name = m.group(2)
        files.append({
            "num": num,
            "name": name,
            "stem": stem,
            "source": md_file,
            "out_rel": Path("essays") / f"{name}.html",
        })
    return files


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

# 论文元数据：概率、标签、描述（用于侧边栏和目录）
ESSAY_META = {
    "整合管理": {
        "prob": 65,
        "badge": "must",
        "badge_text": "⭐⭐⭐ 必背",
        "desc": "2026年最高概率（约65%），整合管理是核心知识域，近年新版教材重点调整领域",
        "sidebar_tips": [
            "项目章程 → 获取正式授权",
            "项目管理计划 = 宏观Release计划",
            "整体变更控制：42项变更申请，批准28项",
            "知识管理：建立项目Wiki，86条经验教训",
            "项目收尾：完整验收+经验教训归档",
        ],
    },
    "成本管理": {
        "prob": 50,
        "badge": "must",
        "badge_text": "⭐⭐ 必背",
        "desc": "2022年考过，距今4年，再考概率高。EVM挣值管理是亮点，记住计算公式",
        "sidebar_tips": [
            "EV=410, AC=455, PV=440",
            "CV = EV-AC = -45万（超支）",
            "CPI = 0.902（低于预警0.9）",
            "SPI = 0.932（进度略滞后）",
            "EAC = BAC/CPI ≈ 754万",
            "最终实际成本661万，节约19万",
        ],
    },
    "进度管理": {
        "prob": 45,
        "badge": "must",
        "badge_text": "⭐⭐ 必背",
        "desc": "2023年考过，进度管理是案例分析常考点，敏捷的燃尽图/速度图有独特亮点",
        "sidebar_tips": [
            "双层计划：Release计划+Sprint计划",
            "PERT三点估算 → 技术不确定模块",
            "Sprint速度基准：40点/Sprint",
            "第8月SPI=0.87触发预警",
            "赶工：引入WMS厂商技术支持",
            "快速跟进：Release间并行推进",
        ],
    },
    "风险管理": {
        "prob": 35,
        "badge": "good",
        "badge_text": "⭐ 了解",
        "desc": "2023年考过，应对策略套路化（规避/减轻/转移/接受），练熟后写作较快",
        "sidebar_tips": [
            "识别43项风险，高风险7项",
            "四大风险：接口集成/人员/配合度/云平台",
            "应急储备34万，动用8万",
            "技术Spike（技术探针）是敏捷亮点",
            "每日站会阻碍清单 = 实时风险监控",
            "Sprint回顾 = 过程风险复盘",
        ],
    },
    "敏捷项目背景": {
        "prob": 0,
        "badge": "ok",
        "badge_text": "📋 背景",
        "desc": "万能项目背景速查表，4篇论文通用。背熟项目基本数据，写作时快速套用",
        "sidebar_tips": [],
    },
    "问卷": {
        "prob": 0,
        "badge": "ok",
        "badge_text": "📋 工具",
        "desc": "填写你的实际项目经历，生成专属摘要和写作提示",
        "sidebar_tips": [],
    },
}


def build_essay_sidebar(name: str) -> str:
    meta = ESSAY_META.get(name, {})
    tips = meta.get("sidebar_tips", [])
    prob = meta.get("prob", 0)
    parts = []

    if prob > 0:
        bar_w = min(prob, 100)
        parts.append(
            f'<div class="sidebar-card">'
            f'<h4>📊 2026命中概率</h4>'
            f'<div class="prob-bar">'
            f'  <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:#57606a">'
            f'    <div class="prob-fill" style="width:{bar_w}px;height:8px;border-radius:4px"></div>'
            f'    <span>{prob}%</span>'
            f'  </div>'
            f'</div>'
            f'</div>'
        )

    if tips:
        li_html = "".join(f"<li>{t}</li>" for t in tips)
        parts.append(
            f'<div class="sidebar-card">'
            f'<h4>📌 关键数据速查</h4>'
            f'<ul>{li_html}</ul>'
            f'</div>'
        )

    parts.append(
        f'<div class="sidebar-card">'
        f'<h4>🔗 快速导航</h4>'
        f'<div class="nav-btns">'
        f'<a href="问卷.html">📋 填写问卷</a>'
        f'<a href="敏捷项目背景.html">🏢 项目背景</a>'
        f'</div>'
        f'</div>'
    )

    return "\n".join(parts)


def build_questionnaire_html() -> str:
    """生成互动问卷页面 HTML。"""
    return """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>个性化定制问卷 · 论文复习</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: #f6f8fa;
    color: #24292e;
    line-height: 1.7;
  }
  .toolbar {
    background: #24292e;
    padding: 10px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .toolbar a { color: #8b949e; text-decoration: none; font-size: 14px; }
  .toolbar a:hover { color: #fff; }
  .hero {
    background: linear-gradient(135deg, #6e40c9 0%, #9a3412 100%);
    color: #fff;
    text-align: center;
    padding: 36px 20px 30px;
  }
  .hero h1 { font-size: 1.6em; margin-bottom: 6px; }
  .hero p { opacity: .85; font-size: 14px; }
  .container { max-width: 760px; margin: 28px auto; padding: 0 20px 60px; }
  .card { background: #fff; border: 1px solid #d0d7de; border-radius: 8px; padding: 24px 28px; margin-bottom: 20px; }
  .card h2 { font-size: 1.05em; color: #0550ae; margin-bottom: 16px; border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }
  label { display: block; font-size: 14px; font-weight: 600; color: #24292e; margin-bottom: 5px; margin-top: 14px; }
  label:first-of-type { margin-top: 0; }
  input[type=text], select, textarea {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    font-size: 14px;
    font-family: inherit;
    background: #f6f8fa;
    transition: border-color .15s;
  }
  input[type=text]:focus, select:focus, textarea:focus {
    outline: none;
    border-color: #0550ae;
    background: #fff;
  }
  textarea { resize: vertical; min-height: 70px; }
  .hint { font-size: 12px; color: #57606a; margin-top: 4px; }
  .btn-gen {
    display: block;
    width: 100%;
    padding: 12px;
    background: linear-gradient(90deg, #6e40c9, #9a3412);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
    margin-top: 10px;
    transition: opacity .2s;
  }
  .btn-gen:hover { opacity: .9; }
  .result { display: none; }
  .result.show { display: block; }
  .result-card {
    background: #f0f9ff;
    border: 1px solid #b6d9f7;
    border-left: 4px solid #0550ae;
    border-radius: 8px;
    padding: 18px 22px;
    margin-bottom: 16px;
  }
  .result-card h3 { font-size: 14px; font-weight: 700; color: #0550ae; margin-bottom: 10px; }
  .result-card .item { font-size: 13px; color: #24292e; margin: 6px 0; line-height: 1.5; }
  .result-card .item strong { color: #9a3412; }
  .copy-btn {
    float: right;
    font-size: 11px;
    padding: 2px 9px;
    border: 1px solid #b6d9f7;
    border-radius: 10px;
    background: #fff;
    cursor: pointer;
    color: #0550ae;
    transition: background .15s;
  }
  .copy-btn:hover { background: #dbeafe; }
  .section-label {
    font-size: 12px;
    font-weight: 700;
    color: #9a3412;
    text-transform: uppercase;
    letter-spacing: .5px;
    margin-bottom: 8px;
  }
  .abstract-preview {
    background: #fff8f5;
    border: 1px solid #fca5a5;
    border-radius: 6px;
    padding: 14px 16px;
    font-size: 13px;
    line-height: 1.85;
    color: #374151;
    white-space: pre-wrap;
  }
</style>
</head>
<body>
<div class="toolbar">
  <a href="../index.html">⬅ 返回首页</a>
  <span style="color:#444;font-size:13px">|</span>
  <a href="index.html">📋 论文目录</a>
</div>
<div class="hero">
  <h1>📋 个性化定制问卷</h1>
  <p>填写你的实际项目经历，生成专属论文关键参数</p>
</div>
<div class="container">
  <div class="card">
    <h2>🏢 你的项目基本信息</h2>
    <label for="pname">项目名称</label>
    <input type="text" id="pname" placeholder="例：XX公司供应链管理系统研发项目">
    <label for="pmethd">开发方式</label>
    <select id="pmethd">
      <option value="scrum">Scrum敏捷开发（2周Sprint）</option>
      <option value="kanban">看板（Kanban）敏捷</option>
      <option value="waterfall">传统瀑布式</option>
      <option value="hybrid">混合（敏捷+传统）</option>
    </select>
    <label for="pbudget">项目总预算（万元）</label>
    <input type="text" id="pbudget" placeholder="例：680">
    <label for="pduration">建设周期（月）</label>
    <input type="text" id="pduration" placeholder="例：14">
    <label for="pteam">团队规模（人）</label>
    <input type="text" id="pteam" placeholder="例：16">
    <label for="prole">你的角色</label>
    <input type="text" id="prole" placeholder="例：项目经理 / 系统分析师">
    <label for="pstart">项目时间段</label>
    <input type="text" id="pstart" placeholder="例：2023年4月至2024年5月">
    <label for="pgoal">项目目标（一句话）</label>
    <textarea id="pgoal" placeholder="例：整合ERP、CRM等系统，构建统一的数字化业务中台"></textarea>
    <label for="presult">项目结果（关键数据）</label>
    <textarea id="presult" placeholder="例：按期交付，系统上线首月故障率低于0.1%，甲方满意度4.8分"></textarea>
  </div>

  <div class="card">
    <h2>🎯 选择你要写的论文主题</h2>
    <label for="ptopic">论文主题</label>
    <select id="ptopic">
      <option value="整合管理">整合管理（最高概率）</option>
      <option value="成本管理">成本管理（含EVM）</option>
      <option value="进度管理">进度管理</option>
      <option value="风险管理">风险管理</option>
    </select>

    <label for="pchallenge">你在该管理领域遇到的主要挑战（1-3条）</label>
    <textarea id="pchallenge" placeholder="例：
1. 遗留系统接口文档缺失，技术集成复杂度高
2. 多部门协调难度大，需求变更频繁
3. 关键技术人员流失风险"></textarea>

    <label for="pmeasure">你采取的主要措施（1-3条）</label>
    <textarea id="pmeasure" placeholder="例：
1. 建立Sprint迭代管理机制，宏观Release计划+微观Sprint计划
2. 制定整体变更控制流程，批准28项变更，拒绝9项
3. 建立项目Wiki知识库，沉淀86条经验教训"></textarea>
  </div>

  <button class="btn-gen" onclick="generate()">✨ 生成我的论文关键参数</button>

  <div class="result" id="result">
    <div class="result-card" style="margin-top:20px">
      <h3>📋 项目信息速查表 <button class="copy-btn" onclick="copyText('info-table')">复制</button></h3>
      <div id="info-table"></div>
    </div>
    <div class="result-card">
      <h3>📝 摘要（约300字，可直接使用） <button class="copy-btn" onclick="copyText('abstract-text')">复制</button></h3>
      <div class="abstract-preview" id="abstract-text"></div>
    </div>
    <div class="result-card">
      <h3>💡 写作提示</h3>
      <div id="writing-tips"></div>
    </div>
  </div>
</div>
<script>
const TOPIC_DATA = {
  "整合管理": {
    challenges: "多系统整合技术复杂度高、需求变更频繁、多部门协调难度大",
    measures: "制定项目章程获取正式授权、建立宏观发布计划与Sprint双层计划体系、实施整体变更控制流程",
    sections: "整合管理计划制定、指导与管理项目执行、整体变更控制、监控项目工作、项目收尾",
    tips: [
      "必须提到：制定项目章程 → 获取正式授权（在政务/集团项目中尤其重要）",
      "核心亮点：整体变更控制流程（变更申请→影响评估→CCB审议→执行→记录）",
      "给出具体数字：共收到变更XX项，批准XX项，拒绝XX项",
      "提到知识管理：建立Wiki知识库，记录经验教训XX条",
      "结尾体现整合思维：'整合管理不是约束，是平衡灵活性与可控性'",
    ]
  },
  "成本管理": {
    challenges: "遗留系统集成复杂度难以准确估算、敏捷环境下成本基准易被侵蚀、成本超支风险",
    measures: "采用故事点+自下而上估算双轨法、运用EVM挣值管理监控成本绩效、严格执行变更成本评估",
    sections: "成本管理计划制定、成本估算（双轨法）、成本基准建立（S曲线）、挣值管理应用",
    tips: [
      "必须有EVM计算数据：EV、AC、PV、CV、CPI、SPI、EAC",
      "CPI要低于0.9（触发预警，说明你有监控机制）",
      "写出具体纠偏措施：优化技术方案/强化变更管控/调整资源/动用储备",
      "结尾：实际成本低于预算，体现成本绩效良好",
      "注意区分应急储备（应对已知风险）和管理储备（应对未知风险）",
    ]
  },
  "进度管理": {
    challenges: "遗留系统接口文档缺失导致工期不确定、甲方里程碑固定延期代价高、需求持续演进冲击进度基准",
    measures: "建立宏观Release计划+微观Sprint双层进度管理、使用燃尽图和速度图监控进度偏差、灵活运用赶工与快速跟进技术",
    sections: "进度管理计划制定、Release计划与Sprint计划建立、进度监控（燃尽图/速度图）、进度偏差纠正、进度压缩技术",
    tips: [
      "敏捷亮点：燃尽图（Burndown Chart）和速度图（Velocity Chart）",
      "给出触发预警的具体数据：第X个Sprint速度=XX，SPI=0.87",
      "写清楚纠偏措施：赶工（增加资源）+ 范围重新优先化 + 快速跟进",
      "提到PERT三点估算：处理技术不确定性高的活动",
      "体现甲方节点固定的背景，说明进度管理的必要性",
    ]
  },
  "风险管理": {
    challenges: "遗留系统技术风险/接口文档缺失、关键人员流失风险、多部门配合不确定性",
    measures: "建立完整风险识别机制（头脑风暴+检查单+每日站会）、定性定量分析优先级、制定四类应对策略",
    sections: "风险管理计划、风险识别（多方法）、定性与定量分析、风险应对规划（四策略）、风险监督",
    tips: [
      "识别出明确数量的风险：总共XX项，高风险X项",
      "四种应对策略：规避、减轻、转移、接受，每种策略对应一个具体风险案例",
      "定量分析要有数字：某风险概率35%，触发后损失约XX万元",
      "敏捷亮点：每日站会阻碍清单 = 实时风险监控，Sprint回顾 = 过程风险复盘",
      "说明应急储备使用情况：动用XX万，将影响控制在XX范围内",
    ]
  }
};

function generate() {
  const pname = document.getElementById('pname').value || 'XX集团数字化业务中台建设项目';
  const pmethd = document.getElementById('pmethd');
  const methdText = pmethd.options[pmethd.selectedIndex].text;
  const pbudget = document.getElementById('pbudget').value || '680';
  const pduration = document.getElementById('pduration').value || '14';
  const pteam = document.getElementById('pteam').value || '16';
  const prole = document.getElementById('prole').value || '项目经理';
  const pstart = document.getElementById('pstart').value || '2023年4月至2024年5月';
  const pgoal = document.getElementById('pgoal').value || '整合集团内部分散系统，构建统一的数字化业务中台';
  const presult = document.getElementById('presult').value || '按期交付，系统上线首月故障率低于0.1%，甲方满意度4.8分（满分5分）';

  const ptopic = document.getElementById('ptopic');
  const topic = ptopic.value;
  const pchallenge = document.getElementById('pchallenge').value;
  const pmeasure = document.getElementById('pmeasure').value;

  const td = TOPIC_DATA[topic];
  const challengeText = pchallenge.trim() || td.challenges;
  const measureText = pmeasure.trim() || td.measures;

  // 信息速查表
  const infoEl = document.getElementById('info-table');
  infoEl.innerHTML = [
    `<div class="item">📌 <strong>项目名称：</strong>${pname}</div>`,
    `<div class="item">🔧 <strong>开发方式：</strong>${methdText}</div>`,
    `<div class="item">💰 <strong>总预算：</strong>${pbudget}万元</div>`,
    `<div class="item">📅 <strong>建设周期：</strong>${pduration}个月（${pstart}）</div>`,
    `<div class="item">👥 <strong>团队规模：</strong>${pteam}人</div>`,
    `<div class="item">🎯 <strong>我的角色：</strong>${prole}</div>`,
    `<div class="item">🚀 <strong>项目目标：</strong>${pgoal}</div>`,
    `<div class="item">✅ <strong>项目结果：</strong>${presult}</div>`,
  ].join('');

  // 摘要
  const abstract = `本文以${pname}为例，结合本人担任${prole}的实践经验，论述了${topic}在信息化项目中的全过程应用。该项目旨在${pgoal}。项目总预算${pbudget}万元，建设周期${pduration}个月，项目团队共${pteam}人，采用${methdText}。

在项目实施过程中，本人面临${challengeText}等挑战。为此，本人采取了${measureText}等措施。通过科学的${topic}实践，${presult}。

本文将从${td.sections}等方面，对本项目${topic}的实践进行系统总结，期望对同类项目的管理工作有所借鉴。`;

  document.getElementById('abstract-text').textContent = abstract;

  // 写作提示
  const tipsEl = document.getElementById('writing-tips');
  tipsEl.innerHTML = td.tips.map(t => `<div class="item">✔️ ${t}</div>`).join('');

  document.getElementById('result').classList.add('show');
  document.getElementById('result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function copyText(id) {
  const el = document.getElementById(id);
  const text = el.innerText || el.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btns = el.parentNode.querySelectorAll('.copy-btn');
    btns.forEach(b => { b.textContent = '✅ 已复制'; setTimeout(() => { b.textContent = '复制'; }, 2000); });
  });
}
</script>
</body>
</html>"""


def build():
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)

    # ── 1. 构建论文页面 ─────────────────────────────────────────────────────────
    essay_files = get_essay_files()
    essays_dir = DOCS_DIR / "essays"
    essays_dir.mkdir(parents=True)

    essay_index_items = ""
    essay_cards_html = ""  # 用于主页

    for i, f in enumerate(essay_files):
        name = f["name"]
        out_path = DOCS_DIR / f["out_rel"]
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # 问卷页面单独生成，跳过 MD→HTML 转换
        if name == "问卷":
            continue

        md_content = f["source"].read_text(encoding="utf-8")
        body_html = md_to_html(md_content)

        # 上一篇 / 下一篇
        prev_next_parts = []
        if i > 0:
            prev = essay_files[i - 1]
            prev_next_parts.append(
                f'<span class="sep">|</span>'
                f'<a href="{prev["name"]}.html">◀ {prev["name"]}</a>'
            )
        if i < len(essay_files) - 1:
            nxt = essay_files[i + 1]
            prev_next_parts.append(
                f'<span class="sep">|</span>'
                f'<a href="{nxt["name"]}.html">{nxt["name"]} ▶</a>'
            )
        prev_next_html = " ".join(prev_next_parts)

        sidebar_html = build_essay_sidebar(name)
        html = ESSAY_PAGE_TEMPLATE.format(
            title=name,
            body=body_html,
            prev_next_html=prev_next_html,
            sidebar_html=sidebar_html,
        )
        out_path.write_text(html, encoding="utf-8")
        print(f"  ✍️  {out_path.relative_to(ROOT)}")

        # 构建论文目录条目
        meta = ESSAY_META.get(name, {})
        prob = meta.get("prob", 0)
        badge = meta.get("badge", "ok")
        badge_text = meta.get("badge_text", "")
        desc = meta.get("desc", "")
        bar_w = min(prob, 100)
        prob_html = ""
        if prob > 0:
            prob_html = (
                f'<div class="prob-row">'
                f'<span>命中概率</span>'
                f'<div class="prob-bar" style="width:{bar_w}px"></div>'
                f'<span>{prob}%</span>'
                f'</div>'
            )
        essay_index_items += (
            f'<a class="essay-card" href="{name}.html">'
            f'<div class="essay-num">{f["num"]:02d}</div>'
            f'<div class="essay-info">'
            f'<div class="essay-title">{name} <span class="badge {badge}">{badge_text}</span></div>'
            f'<div class="essay-desc">{desc}</div>'
            f'{prob_html}'
            f'</div>'
            f'</a>\n'
        )

        # 主页卡片（仅显示论文，不含背景）
        if prob > 0:
            essay_cards_html += (
                f'<a class="card essay-card" href="essays/{name}.html">'
                f'<div class="type lw">论文范文</div>'
                f'<div class="name">{name}</div>'
                f'<div class="desc">{desc[:40]}…</div>'
                f'</a>\n'
            )

    # 论文目录页
    essay_index_html = ESSAY_INDEX_TEMPLATE.format(essay_items=essay_index_items)
    (essays_dir / "index.html").write_text(essay_index_html, encoding="utf-8")
    print(f"  📋 {(essays_dir / 'index.html').relative_to(ROOT)}")

    # 问卷页
    (essays_dir / "问卷.html").write_text(build_questionnaire_html(), encoding="utf-8")
    print(f"  📋 {(essays_dir / '问卷.html').relative_to(ROOT)}")

    # ── 2. 构建真题页面 ──────────────────────────────────────────────────────────
    groups = get_exam_files()
    year_groups_html = ""

    for year in sorted(groups.keys()):
        files = groups[year]
        cards_html = ""
        for f in files:
            out_path = DOCS_DIR / f["out_rel"]
            out_path.parent.mkdir(parents=True, exist_ok=True)

            md_content = f["source"].read_text(encoding="utf-8")
            body_html = md_to_html(md_content)
            page_title = f["label"]
            depth = len(f["out_rel"].parts) - 1
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

    # ── 3. 写主页 index.html ─────────────────────────────────────────────────────
    essay_section_html = f'<div class="card-grid">{essay_cards_html}</div>\n'
    index_html = INDEX_TEMPLATE.format(
        year_groups=year_groups_html,
        essay_cards=essay_section_html,
    )
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"\n  🏠 {(DOCS_DIR / 'index.html').relative_to(ROOT)}")
    total = sum(len(v) for v in groups.values()) + len(essay_files) + 2
    print(f"\n✅ 构建完成，共 {total} 个页面。")


if __name__ == "__main__":
    build()
