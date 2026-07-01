#!/usr/bin/env python
"""Update build_static_site.py with digitalmusic nav link and sitemap entry."""
with open('scripts/build_static_site.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add nav link in header
content = content.replace(
    '<a href="{resolve_url(page_path, \'/vocal/\')}">人聲與歌唱</a>',
    '<a href="{resolve_url(page_path, \'/vocal/\')}">人聲與歌唱</a>\n\t      <a href="{resolve_url(page_path, \'/digitalmusic/\')}">錄音後製</a>'
)

# Add footer nav link
old_footer = '<a href="{resolve_url(page_path, \'/vocal/\')}">人聲與歌唱</a>\n\t        <a href="{resolve_url(page_path, \'/theory/\')}">樂理基礎</a>'
new_footer = '<a href="{resolve_url(page_path, \'/vocal/\')}">人聲與歌唱</a>\n\t        <a href="{resolve_url(page_path, \'/digitalmusic/\')}">錄音後製</a>\n\t        <a href="{resolve_url(page_path, \'/theory/\')}">樂理基礎</a>'
content = content.replace(old_footer, new_footer)

# Add /digitalmusic/ to sitemap static paths
content = content.replace(
    '"/vocal/", "/contact/"',
    '"/vocal/", "/digitalmusic/", "/contact/"'
)

with open('scripts/build_static_site.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('build_static_site.py updated successfully!')
