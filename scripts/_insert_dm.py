#!/usr/bin/env python
"""Insert digitalmusic build function into build_vocal_extra.py"""
import re

with open('scripts/build_vocal_extra.py', 'r', encoding='utf-8') as f:
    content = f.read()

dm_func = '''
def build_digitalmusic_pages():
    """Build digitalmusic index + detail pages from content/digitalmusic/*.md."""
    print("Building digitalmusic pages...")
    dm_dir = CONTENT_DIR / "digitalmusic"
    out_dir = OUTPUT_DIR / "digitalmusic"
    out_dir.mkdir(parents=True, exist_ok=True)

    def parse_title(h1):
        import re as _re
        m = _re.search(r"第\s*(\d+)\s*堂[：:]\s*(.+)", h1)
        if m:
            return int(m.group(1)), m.group(2).strip()
        return None, None

    lessons = []
    for fpath in sorted(dm_dir.glob("*.md")):
        raw = fpath.read_text(encoding="utf-8")
        first = raw.strip().split("\\n")[0]
        num, title = parse_title(first)
        if num:
            has_content = len(raw.strip()) > 300
            level = "基礎篇" if num <= 15 else "進階篇"
            lessons.append({"num": num, "title": title, "level": level, "filepath": fpath, "raw": raw, "published": has_content})

    lessons.sort(key=lambda c: c["num"])
    pub_count = sum(1 for c in lessons if c["published"])
    total = len(lessons)
    lookup = {c["num"]: c for c in lessons}

    def lesson_range_html(start, end):
        items = []
        idx_path = out_dir / "index.html"
        for n in range(start, end + 1):
            if n in lookup:
                c = lookup[n]
                if c["published"]:
                    items.append(f"""<li class="chapter-item has-link">
              <a href="{resolve_url(idx_path, f'/digitalmusic/{n}/')}">
                <span class="ch-num done">{n}</span>
                <span class="ch-title">{escape(c["title"])}</span>
                <span class="ch-status ch-status-done">可閱讀</span>
              </a>
            </li>""")
                else:
                    items.append(f"""<li class="chapter-item">
                <span class="ch-num pending">{n}</span>
                <span class="ch-title">{escape(c["title"])}</span>
                <span class="ch-status ch-status-writing">即將上線</span>
            </li>""")
        return "\\n".join(items)

    bh = lesson_range_html(1, 15)
    ah = lesson_range_html(16, 30)

    idx_body = f"""<main>
  <section class="vocal-hero">
    <p class="eyebrow">Recording &amp; Mixing</p>
    <h1>錄音後製</h1>
    <p class="lead">從宅錄設備建置到專業混音母帶，系統化的錄音後製教學體系。無論你是剛起步的獨立音樂人、Podcast 創作者，還是想提升混音實力的工程師，都能在這裡找到適合的內容。</p>
  </section>
  <div class="vocal-page">
    <div class="vocal-tabs">
      <div class="vocal-tab-bar">
        <button class="vocal-tab-btn is-active" data-tab="beginner">基礎篇：宅錄建置與錄音混音基礎 ({pub_count}/{total})</button>
        <button class="vocal-tab-btn" data-tab="advanced">進階篇：音色雕塑、曲風實戰與母帶後期 ({pub_count}/{total})</button>
      </div>
      <div id="tab-beginner" class="vocal-tab-pane is-active">
        <section class="vocal-level">
          <div class="vocal-level-header"><h2>基礎篇：宅錄建置與錄音混音基礎</h2></div>
          <p class="vocal-level-desc">適合剛踏入錄音世界的新手，從設備選擇、聲學處理、DAW 設定到基礎混音概念，一步步建構你的宅錄工作室。</p>
          <div class="vocal-progress"><span>{pub_count}/{total} 堂已上線</span></div>
          <ol class="chapter-list">{bh}</ol>
        </section>
      </div>
      <div id="tab-advanced" class="vocal-tab-pane">
        <section class="vocal-level">
          <div class="vocal-level-header"><h2>進階篇：音色雕塑、曲風實戰與母帶後期</h2></div>
          <p class="vocal-level-desc">已具備基礎概念，想進一步掌握 EQ 雕塑、壓縮技巧、空間效果、曲風混音實戰與母帶後製的進階學習者。</p>
          <div class="vocal-progress"><span>{pub_count}/{total} 堂已上線</span></div>
          <ol class="chapter-list" start="16">{ah}</ol>
        </section>
      </div>
    </div>
  </div>
</main>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var tabs = document.querySelectorAll('.vocal-tab-btn');
  tabs.forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      tabs.forEach(function(b) {{ b.classList.remove('is-active'); }});
      document.querySelectorAll('.vocal-tab-pane').forEach(function(p) {{ p.classList.remove('is-active'); }});
      btn.classList.add('is-active');
      var pane = document.getElementById('tab-' + btn.dataset.tab);
      if (pane) pane.classList.add('is-active');
    }});
  }});
}});
</script>"""
    write(out_dir / "index.html", page("錄音後製", idx_body, out_dir / "index.html", meta_description="從宅錄設備建置到專業混音母帶，系統化的錄音後製教學。包含基礎篇15堂與進階篇15堂，適合獨立音樂人與混音工程師。"))

    for c in lessons:
        if not c["published"]:
            continue
        ch_dir = out_dir / str(c["num"])
        ch_dir.mkdir(parents=True, exist_ok=True)
        html_body = markdown_to_html(c["raw"])
        import bleach
        from bleach.sanitizer import ALLOWED_TAGS as BTAGS, ALLOWED_ATTRIBUTES as BATTRS
        allowed_tags = BTAGS.union({"p","pre","code","h1","h2","h3","h4","ul","ol","li","blockquote","strong","em","table","thead","tbody","tr","th","td","hr","br","img"})
        allowed_attrs = {**BATTRS, "a": ["href","title","target","rel"], "img": ["src","alt","title"]}
        html_body = bleach.clean(html_body, tags=allowed_tags, attributes=allowed_attrs, protocols=["http","https","mailto"], strip=True)

        prev_num = c["num"] - 1
        next_num = c["num"] + 1
        prev_link = f'<a class="vocal-nav-link" href="{resolve_url(ch_dir / "index.html", f"/digitalmusic/{prev_num}/")}">← 上一堂</a>' if prev_num in lookup else '<span class="vocal-nav-link disabled">← 上一堂</span>'
        next_link = f'<a class="vocal-nav-link" href="{resolve_url(ch_dir / "index.html", f"/digitalmusic/{next_num}/")}">下一堂 →</a>' if next_num in lookup else '<span class="vocal-nav-link disabled">下一堂 →</span>'

        detail_body = f"""<main>
  <div class="vocal-article">
    <div class="vocal-article-header">
      <div class="breadcrumb">
        <a href="{resolve_url(ch_dir / "index.html", "/digitalmusic/")}">← 錄音後製課程</a>
        <span class="sep">/</span>
        <span>{escape(c["title"])}</span>
      </div>
    </div>
    <article class="markdown-body vocal-content">{html_body}</article>
    <div class="vocal-nav">
      {prev_link}
      <a class="vocal-nav-link" href="{resolve_url(ch_dir / "index.html", "/digitalmusic/")}">回課程列表</a>
      {next_link}
    </div>
  </div>
</main>"""
        write(ch_dir / "index.html", page(escape(c["title"]), detail_body, ch_dir / "index.html", meta_description=escape(c["title"])))

    print(f"  Digitalmusic index + {pub_count} lesson pages written.")
'''

# Insert before "def build_contact_page():"
content = content.replace(
    'def build_contact_page():',
    dm_func.strip() + '\n\n\ndef build_contact_page():'
)

# Add the call in main()
content = content.replace(
    '    build_contact_page()',
    '    build_contact_page()\n    build_digitalmusic_pages()'
)

# Add nav link in header
content = content.replace(
    '<a href="{resolve_url(page_path, \'/vocal/\')}">人聲與歌唱</a>',
    '<a href="{resolve_url(page_path, \'/vocal/\')}">人聲與歌唱</a>\n\t      <a href="{resolve_url(page_path, \'/digitalmusic/\')}">錄音後製</a>'
)

# Add footer nav link
old_footer = '<a href="{resolve_url(page_path, \'/vocal/\')}">人聲與歌唱</a>\n\t        <a href="{resolve_url(page_path, \'/theory/\')}">樂理基礎</a>'
new_footer = '<a href="{resolve_url(page_path, \'/vocal/\')}">人聲與歌唱</a>\n\t        <a href="{resolve_url(page_path, \'/digitalmusic/\')}">錄音後製</a>\n\t        <a href="{resolve_url(page_path, \'/theory/\')}">樂理基礎</a>'
content = content.replace(old_footer, new_footer)

# Add digitalmusic feature card to portal homepage
content = content.replace(
    '<a class="portal-card card-vocal"',
    '<a class="portal-card card-digitalmusic" href="{resolve_url(index_path, \'/digitalmusic/\')}">\n\t      <div class="card-icon">🎛</div>\n\t      <div class="card-label">錄音後製</div>\n\t      <div class="card-desc">從宅錄建置到專業混音母帶的系統化課程</div>\n\t    </a>\n\n\t    <a class="portal-card card-vocal"'
)

with open('scripts/build_vocal_extra.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('build_vocal_extra.py updated successfully!')
