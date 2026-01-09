import asyncio
import aiohttp
import gzip
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import re

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

# Türkiye saati (UTC+3)
TR_TIMEZONE = timezone(timedelta(hours=3))

# ================== YARDIMCI ==================

def strip_ns(tag):
    return tag.split("}", 1)[-1]

def normalize_channel_id(cid):
    return cid.lower().replace(" ", "").replace("_", "").replace("-", "").split(".")[0]

def parse_epg_time(time_str):
    """EPG zaman formatını parse eder ve Türkiye saatine dönüştürür"""
    if not time_str:
        return None
    
    # Zaman formatını kontrol et (YYYYMMDDHHMMSS ±HHMM)
    pattern = r'(\d{14})\s*([+-]\d{4})'
    match = re.match(pattern, time_str)
    
    if match:
        timestamp, tz_offset = match.groups()
        # Zaman damgasını datetime'a çevir
        dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
        
        # Timezone offset'ini hesapla
        tz_hours = int(tz_offset[:3])
        tz_minutes = int(tz_offset[0] + tz_offset[3:])
        tz_delta = timedelta(hours=tz_hours, minutes=tz_minutes)
        
        # UTC zamanına çevir
        utc_dt = dt - tz_delta
        
        # Türkiye saatine (UTC+3) çevir
        tr_dt = utc_dt + timedelta(hours=3)
        
        return tr_dt.strftime("%Y%m%d%H%M%S") + " +0300"
    else:
        # Timezone bilgisi yoksa, Türkiye saati olarak kabul et
        if len(time_str) >= 14:
            timestamp = time_str[:14]
            dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
            return dt.strftime("%Y%m%d%H%M%S") + " +0300"
    
    return time_str

def ensure_tr_timezone(t):
    """
    Saati Türkiye zaman dilimine (UTC+3) dönüştürür
    """
    if not t:
        return t
    
    # Zaten +0300 varsa dokunma
    if "+0300" in t:
        return t
    
    return parse_epg_time(t)

def extract_date(t):
    try:
        # Zamanı parse et ve tarih kısmını al
        if not t:
            return None
        
        if len(t) >= 8:
            return datetime.strptime(t[:8], "%Y%m%d").date()
        return None
    except:
        return None

def time_without_offset(t):
    """Sadece zaman damgasını al (timezone olmadan)"""
    if not t:
        return t
    parts = t.split()
    return parts[0] if parts else t

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
    tv = ET.Element("tv", {
        "generator-info-name": "merged-epg-tr-final",
        "generator-info-url": "",
        "source-data-url": "multiple-sources"
    })

    channel_map = {}
    programme_keys = set()

    today = datetime.now().date()
    past_limit = today - timedelta(days=PAST_DAYS)
    future_limit = today + timedelta(days=FUTURE_DAYS)

    for xml_file in BASE_DIR.glob("*.xml"):
        if xml_file.name.startswith("merged"):
            continue

        print(f"Processing: {xml_file.name}")
        
        try:
            root = ET.fromstring(xml_file.read_bytes())
        except Exception as e:
            print(f"Error parsing {xml_file.name}: {e}")
            continue

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

                # Zamanları Türkiye saatine dönüştür
                start_time = ensure_tr_timezone(start_raw)
                stop_time = ensure_tr_timezone(elem.get("stop"))
                
                if not start_time:
                    continue
                    
                elem.set("start", start_time)
                if stop_time:
                    elem.set("stop", stop_time)

                # Tekil program kontrolü (timezone olmadan)
                key = (
                    norm,
                    time_without_offset(start_time),
                    time_without_offset(stop_time) if stop_time else "",
                    elem.findtext(".//title", ""),
                    elem.findtext(".//sub-title", "")
                )
                
                if key in programme_keys:
                    continue

                programme_keys.add(key)
                elem.set("channel", norm)
                tv.append(elem)

    # Channel sayısını kontrol et
    print(f"Total channels: {len(channel_map)}")
    print(f"Total programmes: {len(programme_keys)}")
    
    ET.ElementTree(tv).write(MERGED_XML, encoding="utf-8", xml_declaration=True)
    print(f"Merged EPG saved to: {MERGED_XML}")

def gzip_merged():
    with open(MERGED_XML, "rb") as f:
        with gzip.open(MERGED_GZ, "wb", compresslevel=9) as g:
            g.write(f.read())
    print(f"Compressed EPG saved to: {MERGED_GZ}")

# ================== DEBUG ==================

def debug_channel(channel_name="showtv"):
    """Belirli bir kanalın programlarını kontrol et"""
    if MERGED_XML.exists():
        tree = ET.parse(MERGED_XML)
        root = tree.getroot()
        
        channel_pattern = channel_name.lower().replace(" ", "")
        
        print(f"\n=== DEBUG for channels containing '{channel_pattern}' ===")
        
        programmes_found = 0
        for prog in root.findall(".//programme"):
            chan = prog.get("channel", "").lower()
            if channel_pattern in chan:
                title = prog.findtext(".//title", "No Title")
                start = prog.get("start", "")
                stop = prog.get("stop", "")
                
                # Saati okunabilir formata çevir
                try:
                    start_dt = datetime.strptime(start[:14], "%Y%m%d%H%M%S")
                    start_str = start_dt.strftime("%d.%m.%Y %H:%M")
                    programmes_found += 1
                    
                    if programmes_found <= 10:  # İlk 10 programı göster
                        print(f"{start_str} - {title}")
                except:
                    pass
        
        print(f"Total programmes found: {programmes_found}")
        print("=" * 50)

# ================== MAIN ==================

async def main():
    print("Downloading EPG sources...")
    results = await download_all()
    
    for name, data in results:
        (BASE_DIR / f"{name}.xml").write_bytes(data)
        print(f"Downloaded: {name} ({len(data)} bytes)")

    print("\nMerging EPG data...")
    merge_epg()
    
    print("\nCompressing merged EPG...")
    gzip_merged()
    
    # Debug: Show TV programlarını kontrol et
    debug_channel("show")
    debug_channel("star")
    debug_channel("atv")

if __name__ == "__main__":
    asyncio.run(main())
