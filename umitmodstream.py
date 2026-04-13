import requests
import re
import os
import urllib3
import warnings
import concurrent.futures

# --- AYARLAR ---
warnings.filterwarnings('ignore')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

# DOSYAYA YAZILACAK BAŞLIK (Senin orijinal başlığın)
M3U8_HEADER = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=5500000,AVERAGE-BANDWIDTH=8976000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",FRAME-RATE=25"""

OUTPUT_FOLDER = "umitmodstream"
BASE_PATTERN = "https://mahsunsports{}.xyz"

# KANAL LİSTESİ
CHANNELS = [
    "androstreamlivebiraz1", "androstreamlivebs1", "androstreamlivebs2", "androstreamlivebs3",
    "androstreamlivebs4", "androstreamlivebs5", "androstreamlivebsm1", "androstreamlivebsm2",
    "androstreamlivess1", "androstreamlivess2", "androstreamlivessplus1", "androstreamliveidm", "androstreamlivecbcs", "androstreamlivessplus2", "androstreamlivets", "androstreamlivets1",
    "androstreamlivets2", "androstreamlivets3", "androstreamlivets4", "androstreamlivesm1",
    "androstreamlivesm2", "androstreamlivees1", "androstreamlivees2", "androstreamlivetb",
    "androstreamlivetb1", "androstreamlivetb2", "androstreamlivetb3", "androstreamlivetb4",
    "androstreamlivetb5", "androstreamlivetb6", "androstreamlivetb7", "androstreamlivetb8",
    "androstreamliveexn", "androstreamliveexn1", "androstreamliveexn2", "androstreamliveexn3",
    "androstreamliveexn4", "androstreamliveexn5", "androstreamliveexn6", "androstreamliveexn7",
    "androstreamliveexn8"
]

def check_domain(index):
    """12-99 arası domainleri hızlıca test eder."""
    url = BASE_PATTERN.format(index)
    try:
        response = requests.get(url, headers=HEADERS, timeout=5, verify=False)
        if response.status_code == 200:
            return url
    except:
        return None
    return None

def main():
    # Klasör yoksa oluştur
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    print("🔍 Andro Panel aktif domaini aranıyor (12-99 arası)...")
    
    # 1. Aktif Domaini Bul
    active_site = None
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(check_domain, i) for i in range(12, 100)]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                active_site = result
                executor.shutdown(wait=False, cancel_futures=True)
                break

    if not active_site:
        print("❌ 12 ile 99 arasında aktif site bulunamadı.")
        return

    print(f"✅ Güncel domain bulundu: {active_site}")
    
    # 2. Event sayfasından sunucuları (baseurls) çek
    event_url = f"{active_site}/event.html?id=androstreamlivebs1"
    print("⚙️ Sunucu listesi çekiliyor...")
    
    try:
        r2 = requests.get(event_url, headers=HEADERS, verify=False, timeout=10)
        h2_text = r2.text
    except Exception as e:
        print(f"❌ Event sayfası alınamadı. Hata: {e}")
        return
        
    baseurl_match = re.search(r'baseurls\s*=\s*\[(.*?)\]', h2_text, re.DOTALL | re.IGNORECASE)
    if not baseurl_match: 
        print("❌ baseurls dizisi event sayfasında bulunamadı.")
        return
        
    urls_text = baseurl_match.group(1).replace('"', '').replace("'", "").replace("\n", "").replace("\r", "")
    servers = list(set([url.strip() for url in urls_text.split(',') if url.strip().startswith("http")]))
    
    if not servers:
        print("❌ Aktif sunucu URL'si ayıklanamadı.")
        return

    # 3. Çekilen sunuculardan çalışanını test et
    print("⚡ Çalışan sunucu test ediliyor...")
    active_server = None
    test_id = "androstreamlivebs1"
    
    for server in servers:
        server = server.rstrip('/')
        test_url = f"{server}/{test_id}.m3u8" if "checklist" in server else f"{server}/checklist/{test_id}.m3u8"
        test_url = test_url.replace("checklist//", "checklist/")
        try:
            # Referer vererek test ediyoruz
            temp_response = requests.get(test_url, headers={'Referer': active_site + "/"}, verify=False, timeout=5)
            if temp_response.status_code == 200: 
                active_server = server
                break
        except: 
            continue

    if not active_server:
        print("❌ Çalışan alt sunucu (m3u8 kaynağı) bulunamadı.")
        return

    print(f"🎯 Aktif yayın sunucusu: {active_server}")
    print(f"📂 Dosyalar '{OUTPUT_FOLDER}' klasörüne yazılıyor...\n")

    # 4. Kanalları umitmodstream klasörüne kaydet
    count = 0
    for cid in CHANNELS:
        # Link yapısını kur (checklist yolunu ayarla)
        furl = f"{active_server}/{cid}.m3u8" if "checklist" in active_server else f"{active_server}/checklist/{cid}.m3u8"
        furl = furl.replace("checklist//", "checklist/")
        
        # Dosya içeriği (İstersen sonradan #EXTVLCOPT:http-referrer eklenebilir ama şu an orijinal formatında)
        file_content = f"{M3U8_HEADER}\n{furl}"
        
        file_path = os.path.join(OUTPUT_FOLDER, f"{cid}.m3u8")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        count += 1

    print(f"🏁 İşlem Tamamlandı! Toplam {count} adet .m3u8 dosyası güncellendi.")

if __name__ == "__main__":
    main()
