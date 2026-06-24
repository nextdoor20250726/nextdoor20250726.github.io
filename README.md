# 世界樂器百科

這是一個以 Django 建立的樂器百科網站骨架，包含多層級分類、Markdown 內容欄位、搜尋篩選、分頁列表、詳情頁與 Django Admin 後台。

## 安裝與啟動

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

首頁：`http://127.0.0.1:8000/`

後台：`http://127.0.0.1:8000/admin/`

## 預設資料

建立 Hornbostel-Sachs 大分類與 500 筆 Wikipedia/Wikidata 可追溯的樂器資料：

```bash
python manage.py seed_world_instruments --limit 500 --clear-seeded
```

若仍需本機 Django 後台，請自行建立管理員帳號：

```bash
python manage.py createsuperuser
```

## 靜態 Markdown 版本

若要部署到 GitHub Pages，請改用 Markdown 靜態站流程。資料維護位置：

```text
content/instruments/*.md
```

每個 Markdown 檔案使用 front matter 維護中文名稱、原文名稱、分類、國家/地區、年代、圖片、聆聽連結與來源：

```markdown
---
title: "手風琴"
original_name: "Accordion"
category: "管樂器"
country: "待考"
era: "傳統／年代待考"
source_url: "https://en.wikipedia.org/wiki/Accordion"
---
```

從目前 Django 資料庫重新匯出 Markdown：

```bash
python scripts/export_markdown_from_db.py
```

匯出流程會優先使用中文資料：

- Wikidata `zh-hant` / `zh` 標籤
- Wikidata 中文維基 sitelink
- 英文維基條目的中文跨語言連結
- 中文維基百科摘要作為介紹內容
- Wikidata `P495` 原產國與 `P571` 等年代欄位
- 中文/英文介紹文字中的國家與年代線索

API 回應會快取在 `work/cache/`，避免反覆查詢時被 Wikidata 或 Wikipedia 限速。

注意：靜態站會保留來源連結與摘要內容；若要大量引用維基百科全文，請確認頁面有完整 CC BY-SA 授權標示與來源歸屬。

只根據 Markdown 產生靜態網站：

```bash
python scripts/build_static_site.py
```

靜態網站輸出：

```text
outputs/world-instruments-static/
```

本機預覽：

```bash
cd outputs/world-instruments-static
python3 -m http.server 8001
```

GitHub Pages 部署時，只需要把 `outputs/world-instruments-static/` 的內容發布出去。Django 後台與 SQLite 資料庫可視為舊版匯入工具，不再是內容維護的必要條件。

## GitHub Pages 自動部署

專案已包含 GitHub Actions workflow：

```text
.github/workflows/deploy-github-pages.yml
```

建議部署方式：

1. 在 GitHub 建立一個新 repository。
2. 將此專案 push 到該 repository 的 `main` branch。
3. 到 GitHub repository 的 `Settings -> Pages`。
4. Source 選擇 `GitHub Actions`。
5. push 後 workflow 會自動執行，並部署 `outputs/world-instruments-static/`。

workflow 會自動偵測 GitHub Pages 路徑：

- 若 repository 是 `username.github.io`，網站使用根路徑 `/`。
- 若 repository 是一般 project site，例如 `world-musical-instrument`，網站使用 `/world-musical-instrument/`。

若要本機模擬 project site 路徑：

```bash
SITE_BASE_PATH=/world-musical-instrument python scripts/build_static_site.py
```
