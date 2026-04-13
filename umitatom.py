import requests
import re
import os
import urllib3
import warnings

# --- YAPILANDIRMA VE SSL UYARILARINI GİZLEME ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

START_URL = "https://url24.link/AtomSporTV"
OUTPUT_FOLDER = "atom"
GREEN = "\033[92m"
RESET = "\033[0m"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    'Referer': 'https://url24.link/'
}

# --- SABİT M3U8 BAŞLIĞI ---
M3U8_HEADER = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=5500000,AVERAGE-BANDWIDTH=8976000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",FRAME-RATE=25"""

def get_base_domain():
    base_domain = "https://www.atomsportv480.top"
    try:
        r = requests.get(START_URL, headers=HEADERS, allow_redirects=False, timeout=10, verify=False)
        if 'location' in r.headers:
            loc = r.headers['location']
            r2 = requests.get(loc, headers=HEADERS, allow_redirects=False, timeout=10, verify=False)
            if 'location' in r2.headers:
                base_domain = r2.headers['location'].strip().rstrip('/')
                print(f"✅ Ana Domain Bulundu: {base_domain}")
                return base_domain
        return base_domain
    except Exception as e:
        print(f"Domain Hatası: {e}")
        return base_domain

def get_channel_m3u8(channel_id, base_domain):
    try:
        matches_url = f"{base_domain}/matches?id={channel_id}"
        r = requests.get(matches_url, headers=HEADERS, timeout=10, verify=False)
        
        # Güncel sistemdeki fetch yakalama mantığı
        fetch_match = re.search(r'fetch\(\s*["\'](.*?)["\']', r.text)
        
        if fetch_match:
            fetch_url = fetch_match.group(1).strip()
            
            # Eğer id URL'nin sonunda yoksa ekle
            if not fetch_url.endswith(channel_id): 
                fetch_url += channel_id
            
            cust_headers = HEADERS.copy()
            cust_headers['Origin'] = base_domain
            cust_headers['Referer'] = base_domain
            
            r2 = requests.get(fetch_url, headers=cust_headers, timeout=10, verify=False)
            
            # Güncel sistemdeki birleştirilmiş ve güçlendirilmiş regex mantığı
            m3u8_match = re.search(r'"(?:stream|url|source|deismackanal)":\s*"(.*?\.m3u8|.*?)"', r2.text)
            
            if m3u8_match:
                link = m3u8_match.group(1).replace('\\', '')
                # Geçerli bir link olup olmadığını kontrol et
                if link.endswith('.m3u8') or link.startswith('http'):
                    return link
        return None
    except Exception:
        return None

def get_channels_list():
    return [
        {"id": "bein-sports-1", "name": "beIN Sports 1"},
        {"id": "bein-sports-2", "name": "beIN Sports 2"},
        {"id": "bein-sports-3", "name": "beIN Sports 3"},
        {"id": "bein-sports-4", "name": "beIN Sports 4"},
        {"id": "s-sport", "name": "S Sport 1"},
        {"id": "s-sport-2", "name": "S Sport 2"},
        {"id": "tivibu-spor-1", "name": "Tivibu Spor 1"},
        {"id": "tivibu-spor-2", "name": "Tivibu Spor 2"},
        {"id": "tivibu-spor-3", "name": "Tivibu Spor 3"},
        {"id": "trt-spor", "name": "TRT Spor"},
        {"id": "trt-yildiz", "name": "TRT Yildiz"},
        {"id": "trt1", "name": "TRT 1"},
        {"id": "aspor", "name": "A Spor"},
    ]

def main():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    print(f"{GREEN}--- AtomSporTV Tarayıcı (Güncel Klasör Modu) ---{RESET}")
    
    base_domain = get_base_domain()
    channels = get_channels_list()

    print(f"⚡ Linkler '{OUTPUT_FOLDER}' klasörüne yazılıyor...")

    count = 0
    for i, channel in enumerate(channels):
        print(f"{i+1}. {channel['name']} taranıyor...", end=" ", flush=True)
        
        m3u8_url = get_channel_m3u8(channel['id'], base_domain)
        
        if m3u8_url:
            file_name = f"{channel['id']}.m3u8"
            file_path = os.path.join(OUTPUT_FOLDER, file_name)
            
            file_content = f"{M3U8_HEADER}\n{m3u8_url}"
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_content)
                
            print(f"{GREEN}✓ Kaydedildi: {file_name}{RESET}")
            count += 1
        else:
            print("✗ Link bulunamadı")

    print(f"\n✅ İŞLEM TAMAM! {count} adet kanal '{OUTPUT_FOLDER}' klasörüne kaydedildi.")

if __name__ == "__main__":
    main()
