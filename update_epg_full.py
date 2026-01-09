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
DEBUG_LOG = BASE_DIR / "debug.log"

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
    return (
        cid.lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .split(".")[0]
    )

def extract_date_yyyymmdd(t):
    """
    XMLTV start içinden SADECE GÜN alır
    Saat ve timezone'a ASLA dokunmaz
    """
    if not t or len(t) < 8:
        return None
    try:
        return datetime.strptime(t[:8], "%Y%m%d").date()
    except:
        return None

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

def merge_and_filter():
    tv = ET.Element("tv", {
        "generator-info-name": "merged-epg-tr-no-time-shift"
    })

    channel_map = {}
    programme_keys = set()

    today = datetime.now().date()
    past_limit = today - timedelta(days=PAST_DAYS)
    future_limit = today + timedelta(days=FUTURE_DAYS)

    total_prog = kept_prog = 0

    for xml_file in BASE_DIR.glob("*.xml"):
        if xml_file.name.startswith("merged"):
            continue

        log(f"\n📂 Kaynak: {xml_file.name}")
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
                    tv.append(elem)

            # ---------- PROGRAMME ----------
            elif tag == "programme":
                total_prog += 1

                start_raw = elem.get("start")
                prog_date = extract_date_yyyymmdd(start_raw)

                if not prog_date:
                    continue

                # 🔥 SADECE GÜN FİLTRESİ (SAATE DOKUNMA)
                if not (past_limit <= prog_date <= future_limit):
                    continue

                cid = elem.get("channel")
                if not cid:
                    continue

                norm = normalize_channel_id(cid)

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
                kept_prog += 1

    log(f"\n📊 PROGRAMME: {kept_prog}/{total_prog} eklendi")

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
            log(f"{name} kaydedildi")

    merge_and_filter()
    gzip_merged()

    log("\n✅ merged.xml + merged.xml.gz hazır (SAAT KAYMASI YOK)")

if __name__ == "__main__":
    asyncio.run(main())
