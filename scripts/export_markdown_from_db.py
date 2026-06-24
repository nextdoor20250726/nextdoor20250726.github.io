#!/usr/bin/env python
from __future__ import annotations

import os
import re
import sys
import textwrap
import time
import json
import hashlib
from pathlib import Path
from urllib.parse import quote

import requests
from django.utils.text import slugify


BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content" / "instruments"
CACHE_DIR = BASE_DIR / "work" / "cache"
USER_AGENT = "WorldMusicalInstrumentEncyclopediaStaticExporter/0.1"
ENWIKI_API = "https://en.wikipedia.org/w/api.php"
ZHWIKI_API = "https://zh.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"


CATEGORY_MAP = {
    "弦鳴樂器": "弦樂器",
    "撥弦樂器": "弦樂器",
    "擦弦樂器": "弦樂器",
    "擊弦樂器": "弦樂器",
    "鍵盤弦鳴樂器": "鍵盤樂器",
    "膜鳴樂器": "打擊樂器",
    "敲擊膜鳴樂器": "打擊樂器",
    "體鳴樂器": "打擊樂器",
    "敲擊體鳴樂器": "打擊樂器",
    "摩擦體鳴樂器": "打擊樂器",
    "撥奏體鳴樂器": "打擊樂器",
    "氣鳴樂器": "管樂器",
    "邊棱吹奏樂器": "管樂器",
    "簧鳴樂器": "管樂器",
    "唇振氣鳴樂器": "管樂器",
    "自由氣鳴樂器": "管樂器",
    "電鳴樂器": "電子樂器",
}

COMMON_ZH_NAMES = {
    "accordion": "手風琴",
    "acoustic bass guitar": "原聲貝斯吉他",
    "acoustic guitar": "原聲吉他",
    "bagpipe": "風笛",
    "balalaika": "巴拉萊卡琴",
    "bandoneon": "班多鈕手風琴",
    "banjo": "班卓琴",
    "bass clarinet": "低音單簧管",
    "bass drum": "大鼓",
    "bass guitar": "貝斯吉他",
    "bassoon": "低音管",
    "bell": "鐘",
    "bongo": "邦哥鼓",
    "cello": "大提琴",
    "clarinet": "單簧管",
    "conga": "康加鼓",
    "cymbal": "鈸",
    "djembe": "金貝鼓",
    "double bass": "低音提琴",
    "drum": "鼓",
    "electric guitar": "電吉他",
    "flute": "長笛",
    "gong": "鑼",
    "guitar": "吉他",
    "harmonica": "口琴",
    "harp": "豎琴",
    "horn": "號角",
    "koto": "箏",
    "lute": "魯特琴",
    "mandolin": "曼陀林",
    "marimba": "馬林巴琴",
    "oboe": "雙簧管",
    "oud": "烏德琴",
    "piano": "鋼琴",
    "pipa": "琵琶",
    "saxophone": "薩氏管",
    "sitar": "西塔琴",
    "snare drum": "小鼓",
    "synthesizer": "合成器",
    "tabla": "塔布拉鼓",
    "taiko": "太鼓",
    "tambourine": "鈴鼓",
    "theremin": "特雷門",
    "timpani": "定音鼓",
    "trombone": "長號",
    "trumpet": "小號",
    "ukulele": "烏克麗麗",
    "viola": "中提琴",
    "violin": "小提琴",
    "xylophone": "木琴",
}

COUNTRY_HINTS = [
    ("中國", "中國"),
    ("China", "中國"),
    ("Chinese", "中國"),
    ("日本", "日本"),
    ("Japan", "日本"),
    ("Japanese", "日本"),
    ("韓國", "韓國"),
    ("Korea", "韓國"),
    ("Korean", "韓國"),
    ("印度", "印度"),
    ("India", "印度"),
    ("Indian", "印度"),
    ("印尼", "印尼"),
    ("印度尼西亞", "印尼"),
    ("Indonesia", "印尼"),
    ("Javanese", "印尼"),
    ("非洲", "非洲"),
    ("Africa", "非洲"),
    ("African", "非洲"),
    ("巴西", "巴西"),
    ("Brazil", "巴西"),
    ("古巴", "古巴"),
    ("Cuba", "古巴"),
    ("愛爾蘭", "愛爾蘭"),
    ("Irish", "愛爾蘭"),
    ("蘇格蘭", "蘇格蘭"),
    ("Scotland", "蘇格蘭"),
    ("Scottish", "蘇格蘭"),
    ("西班牙", "西班牙"),
    ("Spain", "西班牙"),
    ("Spanish", "西班牙"),
    ("義大利", "義大利"),
    ("意大利", "義大利"),
    ("Italy", "義大利"),
    ("Italian", "義大利"),
    ("法國", "法國"),
    ("France", "法國"),
    ("French", "法國"),
    ("德國", "德國"),
    ("Germany", "德國"),
    ("German", "德國"),
    ("土耳其", "土耳其"),
    ("Turkey", "土耳其"),
    ("Turkish", "土耳其"),
    ("伊朗", "伊朗"),
    ("Persia", "伊朗"),
    ("Persian", "伊朗"),
    ("美國", "美國"),
    ("United States", "美國"),
    ("American", "美國"),
    ("菲律賓", "菲律賓"),
    ("Philippine", "菲律賓"),
    ("Philippines", "菲律賓"),
]

COUNTRY_NORMALIZATION = {
    "中華人民共和國": "中國",
    "中华人民共和国": "中國",
    "印度尼西亞": "印尼",
    "印度尼西亚": "印尼",
    "美利堅合眾國": "美國",
    "美国": "美國",
}

NON_INSTRUMENT_TITLES = {
    "Acoustics",
    "Ancient Greece",
    "Benin",
    "Bow (music)",
    "Bridge (instrument)",
    "Cameroon",
    "Central Europe",
    "Inuit",
    "JSTOR (identifier)",
    "Keyboard instrument",
    "Korea",
    "Longitudinal wave",
    "Madagascar",
    "Melde's experiment",
    "Mersenne's laws",
    "Middle East",
    "Mongolia",
    "Musical keyboard",
    "Node (physics)",
    "Nut (string instrument)",
    "Overtone",
    "Piano wire",
    "Plectrum",
    "Tension ligature",
    "Tension loop",
}

NON_INSTRUMENT_PARTS = [
    "identifier",
    "region",
    "country",
    "physics",
    "law",
    "experiment",
]

ERA_HINTS = [
    (r"公元前|BCE|BC", "古代"),
    (r"\b1st century\b|1世紀|一世紀", "1 世紀"),
    (r"\b2nd century\b|2世紀|二世紀", "2 世紀"),
    (r"\b3rd century\b|3世紀|三世紀", "3 世紀"),
    (r"\b4th century\b|4世紀|四世紀", "4 世紀"),
    (r"\b5th century\b|5世紀|五世紀", "5 世紀"),
    (r"\b6th century\b|6世紀|六世紀", "6 世紀"),
    (r"\b7th century\b|7世紀|七世紀", "7 世紀"),
    (r"\b8th century\b|8世紀|八世紀", "8 世紀"),
    (r"\b9th century\b|9世紀|九世紀", "9 世紀"),
    (r"\b10th century\b|10世紀|十世紀", "10 世紀"),
    (r"\b11th century\b|11世紀|十一世紀", "11 世紀"),
    (r"\b12th century\b|12世紀|十二世紀", "12 世紀"),
    (r"\b13th century\b|13世紀|十三世紀", "13 世紀"),
    (r"\b14th century\b|14世紀|十四世紀", "14 世紀"),
    (r"\b15th century\b|15世紀|十五世紀", "15 世紀"),
    (r"\b16th century\b|16世紀|十六世紀", "16 世紀"),
    (r"\b17th century\b|17世紀|十七世紀", "17 世紀"),
    (r"\b18th century\b|18世紀|十八世紀", "18 世紀"),
    (r"\bancient\b|古代|Ancient", "古代"),
    (r"\bmedieval\b|Middle Ages|中世紀", "中世紀"),
    (r"\bRenaissance\b|文藝復興", "文藝復興"),
    (r"\bBaroque\b|巴洛克", "巴洛克"),
    (r"\bClassical period\b|古典時期", "古典時期"),
    (r"\b19th century\b|十九世紀", "19 世紀"),
    (r"\b20th century\b|二十世紀", "20 世紀"),
    (r"\b21st century\b|二十一世紀", "21 世紀"),
    (r"\belectronic\b|synthesizer|digital|電子", "現代"),
]

CHINESE_NUMERAL_CENTURIES = {
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
    "十一": "11",
    "十二": "12",
    "十三": "13",
    "十四": "14",
    "十五": "15",
    "十六": "16",
    "十七": "17",
    "十八": "18",
    "十九": "19",
    "二十": "20",
    "二十一": "21",
}


def setup_django():
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "world_instruments.settings")
    import django

    django.setup()


def chunks(values, size):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def wiki_url(site, title):
    return f"https://{site}.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='()_,%')}"


def request_json(session, url, params, timeout=30):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha1(json.dumps([url, params], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    cache_path = CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    response = None
    for attempt in range(10):
        response = session.get(url, params=params, timeout=timeout)
        if response.status_code != 429:
            response.raise_for_status()
            data = response.json()
            cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data
        time.sleep(3 * (attempt + 1))
    response.raise_for_status()


def fetch_wikidata_enrichment(instruments):
    qids = [item.wikidata_id for item in instruments if item.wikidata_id and item.wikidata_id.startswith("Q")]
    enrichment = {}
    country_qids = set()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    for batch in chunks(qids, 50):
        data = request_json(
            session,
            WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "labels|sitelinks|claims",
                "languages": "zh-hant|zh|en",
                "sitefilter": "zhwiki",
                "format": "json",
            },
        )
        entities = data.get("entities", {})
        for qid, entity in entities.items():
            lang_labels = entity.get("labels", {})
            claims = entity.get("claims", {})
            country_id = first_entity_claim(claims, ["P495"])
            inception = first_time_claim(claims, ["P571", "P580", "P575"])
            if country_id:
                country_qids.add(country_id)
            zhwiki_title = entity.get("sitelinks", {}).get("zhwiki", {}).get("title", "")
            enrichment[qid] = {
                "zh_label": lang_labels.get("zh-hant", {}).get("value") or lang_labels.get("zh", {}).get("value") or "",
                "zhwiki_title": zhwiki_title,
                "country_qid": country_id,
                "inception": inception,
            }
        time.sleep(0.2)

    country_labels = fetch_wikidata_labels(country_qids)
    for data in enrichment.values():
        data["country"] = country_labels.get(data.get("country_qid", ""), "")
    return enrichment


def fetch_wikidata_labels(qids):
    if not qids:
        return {}
    labels = {}
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    for batch in chunks(sorted(qids), 50):
        data = request_json(
            session,
            WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "labels",
                "languages": "zh-hant|zh|en",
                "format": "json",
            },
        )
        for qid, entity in data.get("entities", {}).items():
            lang_labels = entity.get("labels", {})
            labels[qid] = (
                lang_labels.get("zh-hant", {}).get("value")
                or lang_labels.get("zh", {}).get("value")
                or lang_labels.get("en", {}).get("value")
                or ""
            )
        time.sleep(0.2)
    return labels


def first_entity_claim(claims, property_ids):
    for property_id in property_ids:
        for claim in claims.get(property_id, []):
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            entity_id = value.get("id")
            if entity_id:
                return entity_id
    return ""


def first_time_claim(claims, property_ids):
    for property_id in property_ids:
        for claim in claims.get(property_id, []):
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            time_value = value.get("time", "")
            if time_value:
                return time_value
    return ""


def fetch_enwiki_langlinks(instruments):
    titles = []
    title_by_name = {}
    for instrument in instruments:
        if instrument.wikidata_id and instrument.wikidata_id.startswith("Q"):
            continue
        title = instrument.source_url.rstrip("/").rsplit("/", 1)[-1].replace("_", " ") if instrument.source_url else instrument.name
        titles.append(title)
        title_by_name[instrument.name] = title

    result = {}
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    for batch in chunks(titles, 50):
        data = request_json(
            session,
            ENWIKI_API,
            params={
                "action": "query",
                "titles": "|".join(batch),
                "prop": "langlinks",
                "lllang": "zh",
                "redirects": 1,
                "format": "json",
            },
        )
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            en_title = page.get("title", "")
            langlinks = page.get("langlinks", [])
            if langlinks:
                result[en_title] = langlinks[0].get("*", "")
        time.sleep(0.2)

    by_instrument_name = {}
    for instrument_name, en_title in title_by_name.items():
        if en_title in result:
            by_instrument_name[instrument_name] = result[en_title]
    return by_instrument_name


def fetch_zh_extracts(zh_titles):
    extracts = {}
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    for batch in chunks([title for title in zh_titles if title], 50):
        data = request_json(
            session,
            ZHWIKI_API,
            params={
                "action": "query",
                "titles": "|".join(batch),
                "prop": "extracts|pageimages",
                "exintro": 1,
                "explaintext": 1,
                "redirects": 1,
                "pithumbsize": 900,
                "format": "json",
                "variant": "zh-hant",
            },
        )
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            title = page.get("title", "")
            extract = (page.get("extract") or "").strip()
            thumbnail = page.get("thumbnail", {}).get("source", "")
            if title and extract:
                extracts[title] = {"extract": extract, "image": thumbnail}
        time.sleep(0.2)
    return extracts


def translate_name(name, qid, wikidata_data, enwiki_langlinks):
    if qid in wikidata_data:
        zh_label = wikidata_data[qid].get("zh_label")
        zhwiki_title = wikidata_data[qid].get("zhwiki_title")
        if zhwiki_title:
            return zhwiki_title
        if zh_label:
            return zh_label
    if name in enwiki_langlinks:
        return enwiki_langlinks[name]
    key = name.lower().strip()
    if key in COMMON_ZH_NAMES:
        return COMMON_ZH_NAMES[key]
    for english, zh in sorted(COMMON_ZH_NAMES.items(), key=lambda item: len(item[0]), reverse=True):
        if english in key:
            return name.replace(english.title(), zh).replace(english, zh)
    return f"{name}（暫譯）"


def map_category(instrument):
    text = f"{instrument.name} {instrument.introduction_md} {instrument.timbre_description}".lower()
    if any(term in text for term in ["piano", "keyboard", "organ", "celesta", "harpsichord", "clavichord"]):
        return "鍵盤樂器"
    if any(term in text for term in ["electronic", "synthesizer", "digital", "theremin"]):
        return "電子樂器"
    category = instrument.category
    names = []
    while category:
        names.append(category.name)
        category = category.parent
    for name in names:
        if name in CATEGORY_MAP:
            return CATEGORY_MAP[name]
    if any(term in text for term in ["drum", "gong", "bell", "xylophone", "marimba", "percussion"]):
        return "打擊樂器"
    if any(term in text for term in ["flute", "horn", "trumpet", "clarinet", "oboe", "saxophone", "pipe"]):
        return "管樂器"
    if any(term in text for term in ["guitar", "violin", "string", "harp", "lute", "zither"]):
        return "弦樂器"
    if any(term in text for term in ["electronic", "synthesizer", "digital"]):
        return "電子樂器"
    return "其他"


def infer_country(text, wikidata_data=None):
    if wikidata_data and wikidata_data.get("country"):
        country = wikidata_data["country"]
        return COUNTRY_NORMALIZATION.get(country, country)
    candidates = []
    for hint, country in COUNTRY_HINTS:
        position = text.lower().find(hint.lower())
        if position >= 0:
            candidates.append((position, country))
    if candidates:
        return sorted(candidates, key=lambda item: item[0])[0][1]
    return "待考"


def is_exportable_instrument(instrument):
    name = instrument.name.strip()
    lowered = name.lower()
    if name in NON_INSTRUMENT_TITLES:
        return False
    if any(part in lowered for part in NON_INSTRUMENT_PARTS):
        return False
    return True


def infer_era(text, wikidata_data=None):
    if wikidata_data and wikidata_data.get("inception"):
        era = era_from_wikidata_time(wikidata_data["inception"])
        if era:
            return era
    century = re.search(r"([一二三四五六七八九十]{1,3}|\d{1,2})世紀", text)
    if century:
        value = CHINESE_NUMERAL_CENTURIES.get(century.group(1), century.group(1))
        return f"{value} 世紀"
    for pattern, era in ERA_HINTS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return era
    return "傳統／年代待考"


def era_from_wikidata_time(time_value):
    match = re.match(r"([+-]\d{1,})", time_value)
    if not match:
        return ""
    year = int(match.group(1))
    if year <= 0:
        return "古代"
    if year <= 500:
        return "古代"
    if year <= 1500:
        return "中世紀"
    if year >= 1901:
        century = ((year - 1) // 100) + 1
        return f"{century} 世紀"
    century = ((year - 1) // 100) + 1
    return f"{century} 世紀"


def yaml_quote(value):
    escaped = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def clean_markdown(md_text):
    lines = []
    for line in (md_text or "").splitlines():
        if line.strip().startswith("- Wikidata：") or line.strip().startswith("- Wikipedia："):
            continue
        lines.append(line.rstrip())
    return textwrap.dedent("\n".join(lines)).strip()


def build_intro(instrument, zh_title, zh_extract):
    if zh_extract:
        source = wiki_url("zh", zh_title)
        return "\n\n".join(
            [
                f"# {zh_title}",
                zh_extract,
                "## 可查證來源",
                f"- 中文維基百科：{source}",
                f"- 原始來源：{instrument.source_url or source}",
            ]
        )
    return clean_markdown(instrument.introduction_md)


def unique_slug(value, used):
    base = slugify(value, allow_unicode=False) or slugify(re.sub(r"[^\w]+", "-", value)) or "instrument"
    slug = base
    suffix = 2
    while slug in used:
        slug = f"{base}-{suffix}"
        suffix += 1
    used.add(slug)
    return slug


def main():
    setup_django()
    from instruments.models import Instrument

    instruments = [
        instrument
        for instrument in Instrument.objects.select_related("category", "category__parent").order_by("name")
        if is_exportable_instrument(instrument)
    ]
    wikidata_enrichment = fetch_wikidata_enrichment(instruments)
    enwiki_langlinks = fetch_enwiki_langlinks(instruments)
    zh_titles = []
    for instrument in instruments:
        data = wikidata_enrichment.get(instrument.wikidata_id or "", {})
        if data.get("zhwiki_title"):
            zh_titles.append(data["zhwiki_title"])
        elif instrument.name in enwiki_langlinks:
            zh_titles.append(enwiki_langlinks[instrument.name])
    zh_extracts = fetch_zh_extracts(sorted(set(zh_titles)))
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    for old_file in CONTENT_DIR.glob("*.md"):
        old_file.unlink()

    used_slugs = set()
    for instrument in instruments:
        item_wikidata = wikidata_enrichment.get(instrument.wikidata_id or "", {})
        zh_title = item_wikidata.get("zhwiki_title") or enwiki_langlinks.get(instrument.name, "")
        zh_name = translate_name(instrument.name, instrument.wikidata_id or "", wikidata_enrichment, enwiki_langlinks)
        zh_extract_data = zh_extracts.get(zh_title, {})
        full_text = " ".join(
            [
                zh_name,
                zh_extract_data.get("extract", ""),
                instrument.name,
                instrument.introduction_md,
                instrument.history_md,
                instrument.timbre_description,
            ]
        )
        category = map_category(instrument)
        country = infer_country(full_text, item_wikidata)
        era = infer_era(full_text, item_wikidata)
        slug = unique_slug(instrument.name, used_slugs)
        intro = build_intro(instrument, zh_title or zh_name, zh_extract_data.get("extract", ""))
        history = clean_markdown(instrument.history_md)
        image = instrument.exploded_view_image or zh_extract_data.get("image", "")
        source_url = wiki_url("zh", zh_title) if zh_title else instrument.source_url
        body = "\n\n".join(
            [
                "## 介紹",
                intro,
                "## 歷史背景",
                history,
                "## 音色描述",
                textwrap.dedent(instrument.timbre_description or "待管理員補充。").strip(),
            ]
        ).strip()
        frontmatter = "\n".join(
            [
                "---",
                f"title: {yaml_quote(zh_name)}",
                f"original_name: {yaml_quote(instrument.name)}",
                f"category: {yaml_quote(category)}",
                f"country: {yaml_quote(country)}",
                f"era: {yaml_quote(era)}",
                f"image: {yaml_quote(image)}",
                f"listen_link: {yaml_quote(instrument.listen_link)}",
                f"source_url: {yaml_quote(source_url)}",
                f"wikidata_id: {yaml_quote(instrument.wikidata_id)}",
                "---",
                "",
            ]
        )
        (CONTENT_DIR / f"{slug}.md").write_text(frontmatter + body + "\n", encoding="utf-8")

    print(f"Exported {len(instruments)} markdown files to {CONTENT_DIR}")


if __name__ == "__main__":
    main()
