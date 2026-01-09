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

BASE_DIR = Path("epg")
MERGED_XML = BASE_DIR / "merged.xml"
MERGED_GZ = BASE_DIR / "merged.xml.gz"

BASE_DIR.mkdir(exist_ok=True)

# ================== YARDIMCI ==================

def strip_ns(tag):
    return tag.split("}", 1)[-1]

def normalize_channel_id(cid):
    return cid.lower().replace(" ", "").replace("_", "").replace("-", "").split(".")[0]

def ensure_tr_timezone(t):
    """
    Saat DOKUNULMAZ
    Sadece timezone yoksa +0300 eklenir
    """
    if not t:
        return t
    if "+" in t or "-" in t[14:]:
        return t
    return f"{t[:14]} +0300"

def extract_date(t):
    try:
        return datetime.strptime(t[:8], "%Y%m%d").date()
    except:
        return None

# ================== DOWNLOAD ==================

async def fetch(session, name, url):
    async with session.get(url, timeout=40) as r:
        r.raise_for_status()
        return name, await r.read()

async def download_all():
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(
            *[fetch(session, n, u) for n, u in EPG_SOURCES.items()]
        )

# ================== MERGE ==================

def merge_epg():
    tv = ET.Element("tv", {"generator-info-name": "merged-epg-tr-final"})

    channel_map = {}
    programme_keys = set()

    today = datetime.now().date()
    past_limit = today - timedelta(days=PAST_DAYS)
    future_limit = today + timedelta(days=FUTURE_DAYS)

    for xml_file in BASE_DIR.glob("*.xml"):
        if xml_file.name.startswith("merged"):
            continue

        root = ET.fromstring(xml_file.read_bytes())

        for elem in root:
            tag = strip_ns(elem.tag)

            if tag == "channel":
                cid = elem.get("id")
                if not cid:
                    continue
                norm = normalize_channel_id(cid)
                if norm not in channel_map:
                    elem.set("id", norm)
                    channel_map[norm] = elem
                    tv.append(elem)

            elif tag == "programme":
                start_raw = elem.get("start")
                date = extract_date(start_raw)
                if not date or not (past_limit <= date <= future_limit):
                    continue

                cid = elem.get("channel")
                if not cid:
                    continue

                norm = normalize_channel_id(cid)

                # 🔥 TEK KRİTİK NOKTA
                elem.set("start", ensure_tr_timezone(elem.get("start")))
                if elem.get("stop"):
                    elem.set("stop", ensure_tr_timezone(elem.get("stop")))

                key = (
                    norm,
                    elem.get("start"),
                    elem.get("stop"),
                    elem.findtext(".//title", "")
                )
                if key in programme_keys:
                    continue

                programme_keys.add(key)
                elem.set("channel", norm)
                tv.append(elem)

    ET.ElementTree(tv).write(MERGED_XML, encoding="utf-8", xml_declaration=True)

def gzip_merged():
    with open(MERGED_XML, "rb") as f:
        with gzip.open(MERGED_GZ, "wb", compresslevel=9) as g:
            g.write(f.read())

# ================== MAIN ==================

async def main():
    results = await download_all()
    for name, data in results:
        (BASE_DIR / f"{name}.xml").write_bytes(data)

    merge_epg()
    gzip_merged()

if __name__ == "__main__":
    asyncio.run(main())
