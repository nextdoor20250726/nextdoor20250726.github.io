#!/usr/bin/env python3
"""Enrich instrument md files from Excel data + Claude + web search.

Stages:
1. Match Excel rows to md files, update sound_class/hs_class/family/playing_method
2. Apply group-level body_listening/soundscape for missing instruments
3. Fix country='待考' using Claude + intro text
4. Fill missing region_type using country logic

Resumable via work/enrich_cache.json
"""
import io
import json
import re
import sys
import time
from pathlib import Path
from collections import defaultdict

import anthropic
import openpyxl
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content" / "instruments"
CACHE_FILE = BASE_DIR / "work" / "enrich_cache.json"
EXCEL_PATH = r"c:\Users\timmychi\Downloads\隔壁家的世界聲音旅圖_完整企劃總表_序文規則更新版.xlsx"
MODEL = "claude-haiku-4-5"
RATE_LIMIT = 0.5
HEADERS = {"User-Agent": "WorldMusicalInstrumentsWiki/1.0 (educational non-commercial project)"}

_last_call = 0.0


# ─── HS group → (body_listening, soundscape, region_type hint) ─────────────
# Derived from existing complete instruments
GROUP_META = {
    "421 邊棱氣鳴／無簧笛類": {
        "body_listening": "氣息、胸腔、長音、空間",
        "soundscape": "一口氣走過山谷（竹管、陶管、長音與世界笛聲）",
    },
    "412/422 簧鳴與自由簧／單簧雙簧": {
        "body_listening": "口腔、舌頭、簧片震動、鼻音",
        "soundscape": "簧片裡的鼻音與歌聲（口簧、自由簧、單簧雙簧與風袋聲音）",
    },
    "423 唇振氣鳴／號角與銅管": {
        "body_listening": "嘴唇、遠方、召喚、空間方向",
        "soundscape": "吹向遠方的號角（天然號、宗教號角、山谷長號與銅管）",
    },
    "321/322 魯特琴類／撥弦": {
        "body_listening": "懷抱、手指、腳步、敘事",
        "soundscape": "旅人手中的撥弦故事（魯特琴、短頸長頸撥弦與民謠弦聲）",
    },
    "322 豎琴與里拉類": {
        "body_listening": "循環、河流感、開放弦、吟唱",
        "soundscape": "開放弦的天空與河流（豎琴、里拉、科拉與跨文化開放弦）",
    },
    "314/315/316 齊特琴／擊弦／鍵盤化弦鳴": {
        "body_listening": "手掌、弦面、推音、敲擊",
        "soundscape": "平放在大地上的弦（齊特琴、箏類、擊弦與鍵盤化弦鳴）",
    },
    "321.3 擦弦／輪弦／提琴家族": {
        "body_listening": "胸口、嗓音、拉長的情緒",
        "soundscape": "像人聲一樣哭與唱（擦弦、輪弦、鍵弓琴與提琴家族）",
    },
    "21 膜鳴鼓類": {
        "body_listening": "手掌、腳底、低音、舞步",
        "soundscape": "手掌、皮膜與舞步（手鼓、框鼓、杯鼓、語言鼓與鼓組）",
    },
    "11/12 定音體鳴／鑼鐘木琴石琴系統": {
        "body_listening": "材料、回聲、群體分工、音列",
        "soundscape": "木石金屬的回聲城市（木琴、石琴、編鐘、鑼群與甘美朗）",
    },
    "11 小型體鳴／搖奏刮奏敲奏": {
        "body_listening": "手腕、腳踝、短音、節奏對齊",
        "soundscape": "手裡搖動的節奏星塵（沙鈴、刮器、鈴串與身體小打擊）",
    },
    "12 體鳴／舌片琴／金屬共鳴": {
        "body_listening": "指尖、掌心、尾音、近身聆聽",
        "soundscape": "手邊發光的小宇宙（近身體鳴、舌片琴與手奏金屬共鳴）",
    },
    "412/31/52 鍵盤、自由簧、電鳴與機械介面": {
        "body_listening": "手指、機械距離、記憶、電聲",
        "soundscape": "按鍵、機械與現代耳朵（風箱鍵盤、鋼琴、合成器與取樣）",
    },
    "合奏編制，非單一 H-S 類目": {
        "body_listening": "身體、群體、互聽、分工",
        "soundscape": "眾聲相遇的廣場（合奏系統、地域編制與現代混合）",
    },
}

# sound_class → hs_class top-level label
SOUND_CLASS_TO_HS = {
    "氣鳴": "Aerophone／氣鳴樂器",
    "弦鳴": "Chordophone／弦鳴樂器",
    "體鳴": "Idiophone／體鳴樂器",
    "膜鳴": "Membranophone／膜鳴樂器",
    "鍵盤／電鳴／機械混合": "Electrophone／電鳴樂器；Chordophone／弦鳴樂器",
    "合奏系統／編制": "",
}


def has_chinese(text):
    return bool(re.search(r"[一-鿿]", text))


def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def rate_wait():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)
    _last_call = time.time()


def parse_meta(text):
    meta = {}
    m = re.match(r"---\n(.*?)---", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta


def get_intro_snippet(text):
    m = re.search(r"## 介紹\s*\n\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
    return m.group(1).strip()[:300] if m else ""


def set_field(text, field, value):
    """Set a frontmatter field value. Add after 'era:' if field doesn't exist."""
    value = str(value).strip()
    # If field exists, replace it
    if re.search(rf"^{field}:\s*", text, re.MULTILINE):
        return re.sub(
            rf"^{field}:.*$",
            f"{field}: {value}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    # Otherwise insert after 'era:' line (or before first '##')
    if re.search(r"^era:\s*", text, re.MULTILINE):
        return re.sub(
            r"^(era:.+)$",
            rf"\1\n{field}: {value}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    # Fallback: insert before first '---' end
    return re.sub(r"(---\n## )", f"{field}: {value}\n\\1", text, count=1)


def load_excel():
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb["11_全樂器資料庫"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    # Index by lowercase original_name
    index = {}
    for r in rows:
        orig = str(r[2] or "").strip()
        if orig:
            index[orig.lower()] = {
                "zh_name": str(r[1] or "").strip(),
                "original_name": orig,
                "sound_class": str(r[3] or "").strip(),
                "hs_group": str(r[4] or "").strip(),
                "family": str(r[5] or "").strip(),
                "playing_method": str(r[6] or "").strip(),
                "country_raw": str(r[7] or "").strip(),
            }
    return index


def clean_country(raw):
    """Remove qualifiers from Excel country field."""
    if not raw or raw in ("需查證", "None"):
        return None
    raw = re.sub(r"（初稿，需查證）|（高度需查證）|（初稿，.*?）|\(.*?\)", "", raw).strip()
    raw = re.sub(r"相關脈絡|脈絡", "", raw).strip()
    raw = re.sub(r"／$|,$", "", raw).strip()
    if raw in ("需查證", ""):
        return None
    return raw


def ask_claude_country(client, title, orig, intro):
    prompt = (
        f"樂器名稱：{title}（{orig}）\n"
        f"簡介：{intro[:250]}\n\n"
        "請用簡短的繁體中文說明這個樂器的主要起源地區或國家（不超過30字）。"
        "格式範例：「日本」「印度／南亞」「非洲西部」「中東／地中海地區」「全球」。"
        "只輸出地區名稱，不要加說明。"
    )
    rate_wait()
    msg = client.messages.create(
        model=MODEL, max_tokens=64,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def infer_region_type(country):
    """Infer region_type from country string."""
    if not country:
        return "跨文化／多地"
    c = country
    # Count number of regions mentioned
    separators = len(re.findall(r"[／/、]", c))
    if "全球" in c:
        return "跨文化／多地"
    if separators >= 2:
        return "跨文化／多地"
    if separators == 1:
        return "地區／文化圈"
    return "單一地區／文化圈"


def ask_claude_group(client, title, orig, sound_class, intro):
    """Ask Claude which Excel HS group this instrument belongs to."""
    groups = list(GROUP_META.keys())
    groups_str = "\n".join(f"- {g}" for g in groups)
    prompt = (
        f"樂器：{title}（{orig}）\n發聲大類：{sound_class}\n簡介：{intro[:200]}\n\n"
        f"請從以下13個分類群組中選出最合適的一個（只輸出群組名稱，不要其他文字）：\n{groups_str}"
    )
    rate_wait()
    msg = client.messages.create(
        model=MODEL, max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    result = msg.content[0].text.strip()
    # Find closest match
    for g in groups:
        if result in g or g in result:
            return g
    return None


def main():
    client = anthropic.Anthropic()
    excel_index = load_excel()
    cache = load_cache()
    files = sorted(CONTENT_DIR.glob("*.md"))
    print(f"Found {len(files)} md files, {len(excel_index)} Excel rows")

    stage1 = stage2 = stage3 = stage4 = 0

    for i, path in enumerate(files, 1):
        slug = path.stem
        text = path.read_text(encoding="utf-8")
        meta = parse_meta(text)
        changed = False

        title = meta.get("title", slug)
        orig = meta.get("original_name", "")
        intro = get_intro_snippet(text)

        # ── Stage 1: Update from Excel ──────────────────────────────────────
        excel_row = excel_index.get(orig.lower())
        if excel_row:
            hs_group = excel_row["hs_group"]
            sc = excel_row["sound_class"]
            fam = excel_row["family"]
            pm = excel_row["playing_method"]

            # sound_class
            if sc and meta.get("sound_class", "") != sc:
                text = set_field(text, "sound_class", sc)
                changed = True

            # hs_class: use hs_group directly (more specific than top-level)
            if hs_group and meta.get("hs_class", "") != hs_group:
                text = set_field(text, "hs_class", hs_group)
                changed = True

            # family
            if fam and meta.get("family", "") != fam:
                text = set_field(text, "family", fam)
                changed = True

            # playing_method
            if pm and meta.get("playing_method", "") != pm:
                text = set_field(text, "playing_method", pm)
                changed = True

            # country from Excel (only if current is "待考")
            country_raw = excel_row.get("country_raw", "")
            cleaned = clean_country(country_raw)
            if cleaned and meta.get("country", "待考") == "待考":
                text = set_field(text, "country", cleaned)
                meta = parse_meta(text)
                changed = True

            if changed:
                stage1 += 1

        # ── Stage 2: body_listening / soundscape from group mapping ─────────
        bl_missing = not meta.get("body_listening")
        sc_missing = not meta.get("soundscape")
        if bl_missing or sc_missing:
            hs_group = None
            if excel_row:
                hs_group = excel_row["hs_group"]
            elif f"{slug}_group" in cache:
                hs_group = cache[f"{slug}_group"]
            else:
                # Ask Claude to determine group
                sc = meta.get("sound_class", "")
                hs_group = ask_claude_group(client, title, orig, sc, intro)
                cache[f"{slug}_group"] = hs_group
                save_cache(cache)

            if hs_group and hs_group in GROUP_META:
                gm = GROUP_META[hs_group]
                if bl_missing and gm.get("body_listening"):
                    text = set_field(text, "body_listening", gm["body_listening"])
                    changed = True
                if sc_missing and gm.get("soundscape"):
                    text = set_field(text, "soundscape", gm["soundscape"])
                    changed = True
                if changed:
                    stage2 += 1

        # Re-parse meta after changes
        meta = parse_meta(text)

        # ── Stage 3: Fix country='待考' ───────────────────────────────────
        if meta.get("country", "待考") == "待考":
            cache_key = f"{slug}_country"
            if cache_key in cache:
                country_result = cache[cache_key]
            else:
                country_result = ask_claude_country(client, title, orig, intro)
                cache[cache_key] = country_result
                save_cache(cache)

            if country_result and has_chinese(country_result):
                text = set_field(text, "country", country_result)
                changed = True
                stage3 += 1

        # Re-parse meta after changes
        meta = parse_meta(text)

        # ── Stage 4: Fill missing region_type ────────────────────────────
        if not meta.get("region_type"):
            country = meta.get("country", "")
            rt = infer_region_type(country)
            text = set_field(text, "region_type", rt)
            changed = True
            stage4 += 1

        if changed:
            path.write_text(text, encoding="utf-8")

        if i % 50 == 0:
            print(f"  [{i}/{len(files)}] stage1={stage1} stage2={stage2} stage3={stage3} stage4={stage4}")

    save_cache(cache)
    print(f"\nDone.")
    print(f"  Excel updates:          {stage1}")
    print(f"  Group BL/SC filled:     {stage2}")
    print(f"  Country 待考 resolved:  {stage3}")
    print(f"  Region_type filled:     {stage4}")


if __name__ == "__main__":
    main()
