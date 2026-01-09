import asyncio
import aiohttp
import hashlib
import gzip
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# ================== AYARLAR ==================

EPG_SOURCES = {
    "epg1": "https://streams.uzunmuhalefet.com/epg/tr.xml",
    "epg2": "https://belgeselsemo.com.tr/yayin-akisi2/xml/turkey3.xml",
    "epg3": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey1.xml",
    "epg4": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey2.xml",
    "epg5": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey3.xml",
    "epg6": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey4.xml",
}

MAX_DAYS = 3
TR_TZ = timezone(timedelta(hours=3))

CHANNEL_ALIASES = {
    "trt1hd": "trt1",
    "trt1": "trt1",
    "kanaldhd": "kanald",
}

BASE_DIR = Path("epg")
HASH_DIR = BASE_DIR / ".hash"
MERGED_XML = BASE_DIR / "merged.xml"
MERGED_GZ = BASE_DIR / "merged.xml.gz"

BASE_DIR.mkdir(exist_ok=True)
HASH_DIR.mkdir(exist_ok=True)

# ================== YARDIMCI ==================

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]

def normalize_channel_id(cid: str) -> str:
    cid = cid.lower()
    cid = cid.replace(" ", "").replace("_", "").replace("-", "")
    cid = cid.split(".")[0]
    return CHANNEL_ALIASES.get(cid, cid)

def parse_xmltv_time(t: str):
    if not t:
        return None
    try:
        return datetime.strptime(t[:14], "%Y%m%d%H%M%S").replace(tzinfo=TR_TZ)
    except Exception:
        return None

def find_text_ns(elem, tag):
    for c in elem:
        if strip_ns(c.tag) == tag:
            return (c.text or "").strip()
    return ""

# ================== DOWNLOAD ==================

async def fetch(session, name, url):
    try:
        async with session.get(url, timeout=30) as r:
            r.raise_for_status()
            return name, await r.read()
    except Exception as e:
        print(f"{name} hata: {e}")
        return name, None

async def download_all():
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(
            *[fetch(session, n, u) for n, u in EPG_SOURCES.items()]
        )

def save_if_changed(name, data):
    if not data:
        return False

    hash_file = HASH_DIR / f"{name}.hash"
    new_hash = sha256(data)
    old_hash = hash_file.read_text() if hash_file.exists() else ""

    if new_hash == old_hash:
        return False

    (BASE_DIR / f"{name}.xml").write_bytes(data)
    hash_file.write_text(new_hash)
    return True

# ================== MERGE ==================

def merge_and_dedupe():
    tv = ET.Element("tv", {
        "generator-info-name": "merged-epg",
        "source-info-name": "multiple",
        "source-data-url": "github.com/umitm0d/Liveinlive",
    })

    channel_map = {}
    programme_keys = set()

    now = datetime.now(TR_TZ)
    limit = now + timedelta(days=MAX_DAYS)

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
                start = parse_xmltv_time(elem.get("start"))
                if not start or not (now <= start <= limit):
                    continue

                cid = elem.get("channel")
                if not cid:
                    continue

                norm = normalize_channel_id(cid)
                title = find_text_ns(elem, "title")

                key = (norm, elem.get("start"), elem.get("stop"), title)
                if key in programme_keys:
                    continue

                programme_keys.add(key)
                elem.set("channel", norm)
                tv.append(elem)

    ET.ElementTree(tv).write(
        MERGED_XML,
        encoding="utf-8",
        xml_declaration=True
    )

def gzip_merged():
    with open(MERGED_XML, "rb") as f_in:
        with gzip.open(MERGED_GZ, "wb", compresslevel=9) as f_out:
            f_out.write(f_in.read())

# ================== MAIN ==================

async def main():
    changed = False
    results = await download_all()

    for name, data in results:
        if save_if_changed(name, data):
            changed = True
            print(f"{name} güncellendi")
        else:
            print(f"{name} değişmedi")

    if changed:
        merge_and_dedupe()
        gzip_merged()
        print("✅ merged.xml + merged.xml.gz hazır")
    else:
        print("ℹ️ Hiçbir değişiklik yok")

if __name__ == "__main__":
    asyncio.run(main())
