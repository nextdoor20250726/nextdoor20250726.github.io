#!/usr/bin/env python
"""Replace get_theory_data() and build_theory_page() with dynamic content from content/musictheory/"""
import re

SCRIPT = "scripts/build_static_site.py"

with open(SCRIPT, "r", encoding="utf-8") as f:
    content = f.read()

# Find the range to replace
start = content.find("def get_theory_data():")
end = content.find("\ndef build_robots(")

print(f"Replacing from {start} to {end}")

new_code = r'''
def get_theory_data():
    """Read music theory content from content/musictheory/*.md files."""
    theory_dir = Path(__file__).resolve().parent.parent / "content" / "musictheory"
    stages = []
    for fpath in sorted(theory_dir.glob("*.md")):
        raw = fpath.read_text(encoding="utf-8")
        first_line = raw.strip().split("\n")[0]
        title = first_line.lstrip("#").strip().strip("*")
        stage_num = fpath.stem.replace("musictheory", "")
        stages.append({
            "id": fpath.stem,
            "num": stage_num,
            "title": title,
            "content": raw,
        })
    return stages


def build_theory_page():
    """Build the music theory page from content/musictheory/*.md files."""
    import bleach as _bl
    from bleach.sanitizer import ALLOWED_TAGS as _BT, ALLOWED_ATTRIBUTES as _BA

    page_dir_ = OUTPUT_DIR / "theory"
    page_dir_.mkdir(parents=True, exist_ok=True)

    theory_data = get_theory_data()
    allowed_tags = _BT.union({"p","pre","code","h1","h2","h3","h4","ul","ol","li","blockquote","strong","em","table","thead","tbody","tr","th","td","hr","br","img"})
    allowed_attrs = {**_BA, "a": ["href","title","target","rel"], "img": ["src","alt","title"]}

    # Generate card grid for index
    cards = []
    for stage in theory_data:
        cards.append(
            f'<a class="theory-card" href="{resolve_url(page_dir_ / "index.html", f"/theory/{stage["num"]}/")}">'
            f'<span class="card-label">{escape(stage["title"])}</span>'
            f'<span class="card-desc">第 {stage["num"]} 階段</span></a>'
        )

    # Generate detail pages for each stage
    for stage in theory_data:
        raw_body = stage["content"]
        body_html = markdown.markdown(raw_body, extensions=["extra", "tables", "fenced_code"], output_format="html5")
        body_html = strip_wiki_links(body_html)
        body_html = _bl.clean(body_html, tags=allowed_tags, attributes=allowed_attrs, protocols=["http","https","mailto"], strip=True)

        stage_dir = page_dir_ / stage["num"]
        stage_dir.mkdir(parents=True, exist_ok=True)

        # Previous/next navigation
        s_num = int(stage["num"])
        prev_link = ""
        next_link = ""
        if s_num > 1:
            prev_link = f'<a class="vocal-nav-link" href="{resolve_url(stage_dir / "index.html", f"/theory/{s_num-1}/")}">← 上一階段</a>'
        else:
            prev_link = '<span class="vocal-nav-link disabled">← 上一階段</span>'
        if s_num < len(theory_data):
            next_link = f'<a class="vocal-nav-link" href="{resolve_url(stage_dir / "index.html", f"/theory/{s_num+1}/")}">下一階段 →</a>'
        else:
            next_link = '<span class="vocal-nav-link disabled">下一階段 →</span>'

        detail_body = f"""<main class="page theory-page">
  <nav class="breadcrumb" style="margin-bottom:24px;">
    <a href="{resolve_url(stage_dir / "index.html", "/theory/")}">← 樂理基礎</a>
    <span>/</span>
    <span>{escape(stage["title"])}</span>
  </nav>
  <article class="markdown-body">{body_html}</article>
  <div class="vocal-nav-links">{prev_link}{next_link}</div>
  <a class="back-link" href="{resolve_url(stage_dir / "index.html", "/theory/")}">← 返回樂理基礎</a>
</main>"""
        write(stage_dir / "index.html", page(stage["title"], detail_body, stage_dir / "index.html"))

    extra_css = """
<style>
.theory-hero { padding:48px 0 28px; }
.theory-page { max-width:860px; }
.theory-nav { display:flex; flex-wrap:wrap; gap:10px; margin:28px 0 32px; padding-bottom:16px; border-bottom:2px solid var(--line); }
.theory-nav a { display:inline-flex; align-items:center; gap:6px; padding:8px 14px; border:1px solid var(--line); border-radius:8px; background:var(--surface); text-decoration:none; font-size:13px; font-weight:600; color:var(--ink2); transition:all .15s; }
.theory-nav a:hover { border-color:var(--accent); color:var(--accent); background:rgba(13,118,107,.04); }
.theory-card { display:flex; flex-direction:column; gap:6px; border:1px solid var(--line); border-radius:10px; padding:20px 22px; background:var(--surface); text-decoration:none; transition:border-color.15s,box-shadow.15s; }
.theory-card:hover { border-color:var(--accent); box-shadow:0 2px 8px rgba(0,0,0,.06); }
.theory-card .card-label { font-weight:700; font-size:16px; color:var(--ink); }
.theory-card .card-desc { color:var(--muted); font-size:13px; }
.theory-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:16px; margin-top:24px; }
</style>
"""

    body = f"""<main class="page theory-page">
  <section class="theory-hero">
    <p class="eyebrow">Music Theory</p>
    <h1>樂理基礎</h1>
    <p class="lead">從聽覺啟蒙到綜合應用，五大階段系統性學習音樂理論基礎知識。</p>
  </section>
  <div class="theory-grid">
    {"".join(cards)}
  </div>
</main>"""
    write(page_dir_ / "index.html", page("樂理基礎", body, page_dir_ / "index.html", extra_head=extra_css, meta_description="從聽覺啟蒙到綜合應用，五大階段系統性學習音樂理論基礎知識。"))
    print(f"  Built theory page with {len(theory_data)} stages")

    # Generate 5 stage detail pages
    print(f"  Generated {len(theory_data)} theory detail pages")
'''

# Update sitemap to include theory detail pages
old_sitemap = 'f"<url><loc>{base}/theory/</loc></url>"'
new_sitemap = 'f"<url><loc>{base}/theory/</loc></url>"'
for i in range(1, 6):
    new_sitemap += f',\n            f"<url><loc>{{base}}/theory/{i}/</loc></url>"'
content = content.replace(old_sitemap, new_sitemap, 1)

# Replace the old functions
content = content[:start] + new_code + content[end:]

with open(SCRIPT, "w", encoding="utf-8") as f:
    f.write(content)

print("Done! get_theory_data() and build_theory_page() replaced.")
