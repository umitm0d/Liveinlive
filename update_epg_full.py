import asyncio
import aiohttp
import gzip
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ================== AYARLAR ==================

EPG_SOURCES = {
    "epg1": "https://streams.uzunmuhalefet.com/epg/tr.xml",
    "epg2": "https://belgeselsemo.com.tr/yayin-akisi2/xml/turkey3.xml",
    "epg3": "https://raw.githubusercontent.com/KiNGTV2025/King-/refs/heads/main/epg/kabloepg.xml",
    "epg4": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey2.xml",
    "epg5": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey3.xml",
    "epg6": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey4.xml",
}

# Script'in başındaki ayarları şu şekilde güncelleyin:
PAST_DAYS = 2    # Geçmiş 2 gün
FUTURE_DAYS = 7  # Gelecek 7 gün (Haftalık olması için)


# Eğer yayınlar hala kayıksa burayı değiştir.
# Örn: Yayınlar 1 saat geriden geliyorsa +1, ileriden gidiyorsa -1 yap.
# Senin sorunun muhtemelen Timezone etiketi hatasıydı, o yüzden kodun mantığını değiştirdim, bunu 0'da bırak.
SAAT_FARKI = 0 

BASE_DIR = Path("epg")
MERGED_XML = BASE_DIR / "merged.xml"
MERGED_GZ = BASE_DIR / "merged.xml.gz"

BASE_DIR.mkdir(exist_ok=True)

# ================== YARDIMCI ==================

def strip_ns(tag):
    return tag.split("}", 1)[-1]

def normalize_channel_id(cid):
    if not cid: return "unknown"
    return cid.lower().replace(" ", "").replace("_", "").replace("-", "").split(".")[0]

def fix_time_string(t_str):
    """
    Gelen zaman damgasını parçalar, saat farkını uygular 
    ve zorla +0300 olarak etiketler.
    Format: YYYYMMDDHHMMSS +0300
    """
    if not t_str:
        return ""
    
    # Sadece sayıları al (ilk 14 hane: YYYYMMDDHHMMSS)
    digits = re.sub(r"[^0-9]", "", t_str)[:14]
    
    if len(digits) < 14:
        return t_str # Format bozuksa dokunma

    try:
        dt = datetime.strptime(digits, "%Y%m%d%H%M%S")
        
        # Eğer manuel saat ayarı yapıldıysa uygula
        if SAAT_FARKI != 0:
            dt = dt + timedelta(hours=SAAT_FARKI)
            
        # Timezone ne gelirse gelsin, biz onu TR saati (+0300) olarak işaretliyoruz.
        # Bu sayede oynatıcı "Bu zaten TR saati" diyip üzerine bir daha +3 eklemez.
        return f"{dt.strftime('%Y%m%d%H%M%S')} +0300"
    except Exception as e:
        print(f"Tarih hatası: {t_str} -> {e}")
        return t_str

def extract_date(t):
    try:
        clean_t = re.sub(r"[^0-9]", "", t)[:8]
        return datetime.strptime(clean_t, "%Y%m%d").date()
    except:
        return None

# ================== DOWNLOAD ==================

async def fetch(session, name, url):
    print(f"İndiriliyor: {name}...")
    try:
        async with session.get(url, timeout=60) as r:
            r.raise_for_status()
            data = await r.read()
            print(f"Tamamlandı: {name}")
            return name, data
    except Exception as e:
        print(f"HATA {name}: {e}")
        return name, None

async def download_all():
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(
            *[fetch(session, n, u) for n, u in EPG_SOURCES.items()]
        )

# ================== MERGE ==================

def merge_epg():
    print("Birleştirme işlemi başlıyor...")
    tv = ET.Element("tv", {"generator-info-name": "merged-epg-tr-final"})

    channel_map = {}
    programme_keys = set()

    today = datetime.now().date()
    past_limit = today - timedelta(days=PAST_DAYS)
    future_limit = today + timedelta(days=FUTURE_DAYS)

    # İndirilen XML dosyalarını oku
    for xml_file in BASE_DIR.glob("*.xml"):
        if xml_file.name.startswith("merged"):
            continue
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
        except Exception as e:
            print(f"XML Okuma hatası {xml_file}: {e}")
            continue

        for elem in root:
            tag = strip_ns(elem.tag)

            # --- KANALLAR ---
            if tag == "channel":
                cid = elem.get("id")
                norm = normalize_channel_id(cid)
                
                if norm not in channel_map:
                    # Yeni ID ata ve listeye ekle
                    elem.set("id", norm)
                    channel_map[norm] = elem
                    tv.append(elem)

            # --- PROGRAMLAR ---
            elif tag == "programme":
                start_raw = elem.get("start")
                stop_raw = elem.get("stop")
                
                # Tarih filtresi
                date_obj = extract_date(start_raw)
                if not date_obj or not (past_limit <= date_obj <= future_limit):
                    continue

                cid = elem.get("channel")
                norm = normalize_channel_id(cid)
                
                # Eğer kanal listemizde yoksa programı ekleme (isteğe bağlı)
                # if norm not in channel_map: continue

                # 🔥 SAAT DÜZELTME NOKTASI 🔥
                new_start = fix_time_string(start_raw)
                new_stop = fix_time_string(stop_raw) if stop_raw else ""

                elem.set("start", new_start)
                if new_stop:
                    elem.set("stop", new_stop)
                
                elem.set("channel", norm)

                # Mükerrer kayıt kontrolü (Aynı kanal, aynı saat, aynı başlık)
                title_text = elem.findtext(".//title", "") or ""
                unique_key = (norm, new_start, title_text)
                
                if unique_key in programme_keys:
                    continue

                programme_keys.add(unique_key)
                tv.append(elem)

    print(f"Toplam {len(programme_keys)} program işlendi.")
    
    # XML Yaz
    tree = ET.ElementTree(tv)
    tree.write(MERGED_XML, encoding="utf-8", xml_declaration=True)
    print(f"XML kaydedildi: {MERGED_XML}")

def gzip_merged():
    print("GZIP sıkıştırma yapılıyor...")
    with open(MERGED_XML, "rb") as f:
        with gzip.open(MERGED_GZ, "wb", compresslevel=9) as g:
            g.write(f.read())
    print(f"GZ kaydedildi: {MERGED_GZ}")

# ================== MAIN ==================

async def main():
    results = await download_all()
    
    # Dosyaları diske yaz
    for name, data in results:
        if data:
            (BASE_DIR / f"{name}.xml").write_bytes(data)

    merge_epg()
    gzip_merged()
    print("İşlem başarıyla tamamlandı.")

if __name__ == "__main__":
    asyncio.run(main())
