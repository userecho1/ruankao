---
name: pdf-process
description: 从 PDF 文件中提取文字、表格、图像，并解析内容。适用于：读取PDF试题、分析PDF文档、提取PDF中的表格数据、将PDF页面转为图片。关键词：pdf、读取、提取、试题、表格、图像。
---

# PDF 处理技能

## 适用场景

- 读取 PDF 文件中的文字内容（如试题、文档、报告）
- 提取 PDF 中的表格数据
- 将 PDF 页面渲染为图片（用于查看图表、手写内容等）
- 解析图片内容后再进行文字分析

## 依赖库

使用 `pymupdf`（包名为 `pymupdf`，导入名为 `pymupdf` 或 `fitz`）。

### 环境准备（按优先级执行，满足即止）

**第一步：检查当前环境是否已有 pymupdf**

```powershell
python -c "import pymupdf; print(pymupdf.__version__)"
```

- 若输出版本号 → 直接使用，无需任何安装操作。
- 若报 `ModuleNotFoundError` → 进入第二步。

**第二步：尝试其他已有 Python 环境**

Windows 下可能存在多个 Python，先列出：

```powershell
where.exe python
```

逐个检查是否已有 pymupdf：

```powershell
<完整路径>\python.exe -c "import pymupdf; print(pymupdf.__version__)"
```

若某个环境已有 → 后续脚本改用该完整路径调用，无需安装。

**第三步：仅在当前项目内安装（不污染全局环境）**

若所有已有环境均无 pymupdf，在**项目目录内**创建虚拟环境安装：

```powershell
# 在项目根目录创建 .venv（只影响此目录）
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install pymupdf
```

安装后，后续所有 Python 操作均在 `.venv` 内执行。用完后 `deactivate` 退出。

> **原则**：优先复用已有环境，确实缺包时才安装，且安装范围限于项目 `.venv`，不执行全局 `pip install`。

---

## 方法一：提取文字

```python
import pymupdf

doc = pymupdf.open(r"path\to\file.pdf")
for i, page in enumerate(doc):
    print(f"=== 第{i+1}页 ===")
    print(page.get_text())
```

- `page.get_text()` 返回该页所有可选中的文字
- 适用于文字型 PDF（非扫描版）

---

## 方法二：提取表格

```python
import pymupdf

doc = pymupdf.open(r"path\to\file.pdf")
for i, page in enumerate(doc):
    tabs = page.find_tables()
    for j, tab in enumerate(tabs.tables):
        print(f"第{i+1}页 表格{j+1}:")
        for row in tab.extract():
            print(row)
```

- 若返回 0 个表格，说明 PDF 中表格是图形渲染的，需改用方法三（渲染为图片）查看

---

## 方法三：渲染为图片

当 PDF 包含图形化表格、图表或扫描内容时，将页面渲染为图片后使用 `view_image` 工具查看：

```python
import pymupdf

doc = pymupdf.open(r"path\to\file.pdf")
for i, page in enumerate(doc):
    mat = pymupdf.Matrix(2, 2)   # 2x 缩放，提高清晰度
    pix = page.get_pixmap(matrix=mat)
    out_path = rf"path\to\output\page_{i+1}.png"
    pix.save(out_path)
    print(f"Saved page {i+1} → {out_path}")
```

保存后用 `view_image` 工具查看图片，再手动录入图片中的表格数据。

---

## 决策流程

```
读取 PDF
  ├─ 先用方法一提取文字 → 检查内容是否完整
  │     └─ 完整 → 直接使用文字内容
  │     └─ 缺表格/图表 → 继续
  ├─ 用方法二提取表格 → 检查是否有表格
  │     └─ 有表格 → 使用表格数据
  │     └─ 返回0个表格（图形渲染）→ 继续
  └─ 用方法三渲染为图片 → view_image 查看 → 手动录入
```

---

## 实战示例（2024上半年案例分析真题）

```python
# 1. 提取文字（获取题目文本）
import pymupdf
doc = pymupdf.open(r'd:\ruankao\resource\近五年真题\2024上_案例分析_批一.pdf')
for i, page in enumerate(doc):
    print(f'=== 第{i+1}页 ===')
    print(page.get_text())

# 2. 表格提取失败（返回0个），改为渲染图片
for i, page in enumerate(doc):
    mat = pymupdf.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)
    pix.save(rf'd:\ruankao\resource\近五年真题\page_{i+1}.png')

# 3. 使用 view_image 查看 page_3.png、page_4.png 获取表格数据
```

结果：文字内容通过方法一获取，图形化表格通过渲染图片 + `view_image` 工具读取。
