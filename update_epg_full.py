import asyncio
import aiohttp
import gzip
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ================== AYARLAR ==================

EPG_SOURCES = {
    "epg1": "https://raw.githubusercontent.com/tecobaba/tecom3u/refs/heads/main/tr-guide.xml",
    "epg2": "https://raw.githubusercontent.com/umitm0d/Liveinlive/main/epg.xml",
    "epg3": "https://raw.githubusercontent.com/impresents/my-iptv-list/refs/heads/main/epg.xml",
    "epg4": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey2.xml",
    "epg5": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey3.xml",
    "epg6": "https://raw.githubusercontent.com/globetvapp/epg/refs/heads/main/Turkey/turkey4.xml",
}

# Alternatif URL'ler (GitHub'a erişim sorunu olursa kullanılacak)
ALTERNATIVE_SOURCES = {
    "epg3": [
        "https://raw.githubusercontent.com/KiNGTV2025/King-/main/epg/kabloepg.xml",  # refs/heads kısmı kaldırıldı
        "https://github.com/KiNGTV2025/King-/raw/main/epg/kabloepg.xml",  # GitHub raw alternatif format
    ]
}

PAST_DAYS = 2    # Geçmiş 2 gün
FUTURE_DAYS = 7  # Gelecek 7 gün (Haftalık olması için)
SAAT_FARKI = 0 
RETRY_COUNT = 3  # Başarısız olursa kaç kere tekrar denensin
TIMEOUT = 30     # Timeout süresi (saniye)

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

# ================== GELİŞTİRİLMİŞ DOWNLOAD ==================

async def fetch_with_retry(session, name, url, retries=RETRY_COUNT):
    """Bir URL'yi belirtilen sayıda tekrar dener."""
    for attempt in range(retries):
        print(f"İndiriliyor: {name} (Deneme {attempt + 1}/{retries})...")
        try:
            async with session.get(url, timeout=TIMEOUT) as r:
                if r.status == 200:
                    data = await r.read()
                    # Boş olup olmadığını kontrol et
                    if data and len(data) > 100:  # 100 byte'tan küçükse boş say
                        print(f"Tamamlandı: {name} ({len(data)} byte)")
                        return name, data, url
                    else:
                        print(f"Uyarı: {name} boş içerik ({len(data) if data else 0} byte)")
                else:
                    print(f"HATA {name}: HTTP {r.status}")
        except asyncio.TimeoutError:
            print(f"Timeout: {name} (deneme {attempt + 1})")
        except Exception as e:
            print(f"HATA {name}: {e}")
        
        # Son deneme değilse bekle ve tekrar dene
        if attempt < retries - 1:
            await asyncio.sleep(2)  # 2 saniye bekle
    
    return name, None, url

async def download_all():
    async with aiohttp.ClientSession(headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }) as session:
        tasks = []
        
        for name, url in EPG_SOURCES.items():
            # Eğer bu kaynak için alternatif URL'ler varsa
            if name in ALTERNATIVE_SOURCES:
                # Önce ana URL'yi dene
                tasks.append(fetch_with_retry(session, name, url))
                # Alternatifleri de ekle
                for alt_url in ALTERNATIVE_SOURCES[name]:
                    tasks.append(fetch_with_retry(session, f"{name}_alt", alt_url))
            else:
                tasks.append(fetch_with_retry(session, name, url))
        
        results = await asyncio.gather(*tasks)
        
        # İndirilenleri işle
        downloaded = {}
        for name, data, url in results:
            if data and name not in downloaded:  # İlk başarılı indirmeyi kullan
                downloaded[name] = data
                print(f"✓ {name.replace('_alt', '')} başarıyla indirildi")
        
        return [(name.replace('_alt', ''), data) for name, data in downloaded.items()]

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
            file_size = xml_file.stat().st_size
            print(f"İşleniyor: {xml_file.name} ({file_size} byte)")
            
            if file_size < 100:  # 100 byte'tan küçükse atla
                print(f"  Atlandı: Çok küçük dosya")
                continue
                
            tree = ET.parse(xml_file)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"XML Parse hatası {xml_file}: {e}")
            continue
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
                
                if not start_raw:
                    continue
                    
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
                unique_key = (norm, new_start, title_text[:50])  # Sadece ilk 50 karakter
                
                if unique_key in programme_keys:
                    continue

                programme_keys.add(unique_key)
                tv.append(elem)

    print(f"Toplam {len(channel_map)} kanal, {len(programme_keys)} program işlendi.")
    
    # XML Yaz
    tree = ET.ElementTree(tv)
    tree.write(MERGED_XML, encoding="utf-8", xml_declaration=True)
    print(f"XML kaydedildi: {MERGED_XML} ({MERGED_XML.stat().st_size} byte)")

def gzip_merged():
    print("GZIP sıkıştırma yapılıyor...")
    try:
        with open(MERGED_XML, "rb") as f:
            with gzip.open(MERGED_GZ, "wb", compresslevel=9) as g:
                g.write(f.read())
        print(f"GZ kaydedildi: {MERGED_GZ} ({MERGED_GZ.stat().st_size} byte)")
    except Exception as e:
        print(f"GZIP hatası: {e}")

# ================== DEBUG ==================

def check_downloaded_files():
    """İndirilen dosyaları kontrol et"""
    print("\n" + "="*50)
    print("İndirilen Dosya Kontrolü:")
    print("="*50)
    
    for xml_file in BASE_DIR.glob("*.xml"):
        if not xml_file.name.startswith("merged"):
            try:
                size = xml_file.stat().st_size
                with open(xml_file, 'rb') as f:
                    first_line = f.readline(100).decode('utf-8', errors='ignore')
                print(f"{xml_file.name}: {size} byte")
                print(f"  İlk satır: {first_line[:80]}")
            except Exception as e:
                print(f"{xml_file.name}: OKUNAMADI - {e}")

# ================== MAIN ==================

async def main():
    print("EPG Toplayıcı Başlıyor...")
    
    # Önceki dosyaları temizle (opsiyonel)
    for xml_file in BASE_DIR.glob("epg*.xml"):
        try:
            xml_file.unlink()
        except:
            pass
    
    results = await download_all()
    
    # Dosyaları diske yaz
    for name, data in results:
        if data:
            file_path = BASE_DIR / f"{name}.xml"
            file_path.write_bytes(data)
            print(f"✓ {name}.xml kaydedildi ({len(data)} byte)")
        else:
            print(f"✗ {name} indirilemedi")
    
    # İndirilen dosyaları kontrol et
    check_downloaded_files()
    
    # Birleştirme işlemi
    merge_epg()
    gzip_merged()
    
    print("\n" + "="*50)
    print("İşlem tamamlandı!")
    
    # Sonuçları göster
    if MERGED_XML.exists():
        size_mb = MERGED_XML.stat().st_size / (1024 * 1024)
        print(f"Oluşturulan EPG: {size_mb:.2f} MB")
    
    if MERGED_GZ.exists():
        size_mb = MERGED_GZ.stat().st_size / (1024 * 1024)
        print(f"Sıkıştırılmış EPG: {size_mb:.2f} MB")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nİşlem kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\nBeklenmeyen hata: {e}")
