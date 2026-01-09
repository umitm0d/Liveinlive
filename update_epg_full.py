import asyncio
import aiohttp
import gzip
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ================== AYARLAR ==================

EPG_SOURCES = {
    "epg1": "https://streams.uzunmuhalefet.com/epg/tr.xml",
    "epg2": "https://belgeselsemo.com.tr/yayin-akisi2/xml/turkey3.xml",
    "epg3": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey1.xml",
    "epg4": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey2.xml",
    "epg5": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey3.xml",
    "epg6": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey4.xml",
}

PAST_DAYS = 3
FUTURE_DAYS = 3

# Spor kanalı tespiti
SPORT_KEYWORDS = [
    "spor", "sport", "beinsport", "s sport", "ssport",
    "tivibuspor", "trtspor", "eurosport", "nba", "ufc"
]

BASE_DIR = Path("epg")
MERGED_XML = BASE_DIR / "merged.xml"
MERGED_GZ = BASE_DIR / "merged.xml.gz"
DEBUG_LOG = BASE_DIR / "debug.log"
NO_EPG_REPORT = BASE_DIR / "no_epg_channels.txt"

BASE_DIR.mkdir(exist_ok=True)

# ================== LOG ==================

def log(msg):
    print(msg)
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# ================== YARDIMCI ==================

def strip_ns(tag):
    return tag.split("}", 1)[-1]

def normalize_channel_id(cid):
    return cid.lower().replace(" ", "").replace("_", "").replace("-", "").split(".")[0]

def parse_naive(t):
    try:
        return datetime.strptime(t[:14], "%Y%m%d%H%M%S")
    except:
        return None

def add_tr_tz(t):
    if not t:
        return t
    if "+" in t or "-" in t[14:]:
        return t
    return t[:14] + " +0300"

def find_text_ns(elem, tag):
    for c in elem:
        if strip_ns(c.tag) == tag:
            return (c.text or "").strip()
    return ""

def is_sport_channel(name):
    n = name.lower()
    return any(k in n for k in SPORT_KEYWORDS)

# ================== DOWNLOAD ==================

async def fetch(session, name, url):
    try:
        async with session.get(url, timeout=40) as r:
            r.raise_for_status()
            return name, await r.read()
    except Exception as e:
        log(f"⛔ {name} indirilemedi: {e}")
        return name, None

async def download_all():
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(
            *[fetch(session, n, u) for n, u in EPG_SOURCES.items()]
        )

# ================== MERGE ==================

def merge_and_dedupe():
    tv = ET.Element("tv", {"generator-info-name": "merged-epg-tr-3-3-live"})

    channel_map = {}
    programme_keys = set()
    channel_programme_count = {}

    now = datetime.now()
    start_limit = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=PAST_DAYS)
    end_limit = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=FUTURE_DAYS + 1)

    total_prog = kept_prog = 0

    for xml_file in BASE_DIR.glob("*.xml"):
        if xml_file.name.startswith("merged"):
            continue

        root = ET.fromstring(xml_file.read_bytes())

        for elem in root:
            tag = strip_ns(elem.tag)

            # ---------- CHANNEL ----------
            if tag == "channel":
                cid = elem.get("id")
                if not cid:
                    continue

                norm = normalize_channel_id(cid)
                if norm not in channel_map:
                    elem.set("id", norm)
                    channel_map[norm] = elem
                    channel_programme_count[norm] = 0
                    tv.append(elem)

            # ---------- PROGRAMME ----------
            elif tag == "programme":
                total_prog += 1

                start_raw = elem.get("start")
                stop_raw = elem.get("stop") or start_raw

                start_dt = parse_naive(start_raw)
                stop_dt = parse_naive(stop_raw)

                if not start_dt or not stop_dt:
                    continue

                if stop_dt < start_limit or start_dt >= end_limit:
                    continue

                cid = elem.get("channel")
                if not cid:
                    continue

                norm = normalize_channel_id(cid)

                # 🔴 CANLI SPOR OVERRIDE
                title = find_text_ns(elem, "title")
                channel_name = find_text_ns(channel_map.get(norm), "display-name")

                if is_sport_channel(channel_name):
                    if start_dt <= now <= stop_dt:
                        title = "🔴 CANLI - " + title
                        for c in elem:
                            if strip_ns(c.tag) == "title":
                                c.text = title

                elem.set("start", add_tr_tz(start_raw))
                elem.set("stop", add_tr_tz(stop_raw))
                elem.set("channel", norm)

                key = (norm, elem.get("start"), elem.get("stop"), title)
                if key in programme_keys:
                    continue

                programme_keys.add(key)
                channel_programme_count[norm] += 1
                tv.append(elem)
                kept_prog += 1

    # ================== EPG'Sİ OLMAYAN KANALLAR ==================
    with open(NO_EPG_REPORT, "w", encoding="utf-8") as f:
        for cid, count in channel_programme_count.items():
            if count == 0:
                name = find_text_ns(channel_map[cid], "display-name")
                f.write(f"{cid} | {name}\n")

    log(f"\n📊 PROGRAMME: {kept_prog}/{total_prog}")
    log(f"📄 EPG'si olmayan kanal raporu yazıldı")

    ET.ElementTree(tv).write(
        MERGED_XML,
        encoding="utf-8",
        xml_declaration=True
    )

def gzip_merged():
    with open(MERGED_XML, "rb") as f:
        with gzip.open(MERGED_GZ, "wb", compresslevel=9) as g:
            g.write(f.read())

# ================== MAIN ==================

async def main():
    if DEBUG_LOG.exists():
        DEBUG_LOG.unlink()

    results = await download_all()
    for name, data in results:
        if data:
            (BASE_DIR / f"{name}.xml").write_bytes(data)

    merge_and_dedupe()
    gzip_merged()
    log("\n✅ merged.xml + merged.xml.gz hazır (CANLI + RAPOR)")

if __name__ == "__main__":
    asyncio.run(main())
