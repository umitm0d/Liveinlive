import json
import os
import time
import concurrent.futures
import requests

# --- AYARLAR ---
API_KEY = "6fabef7bd74e01efcd81d35c39c4a049"
BASE_URL = "https://api.themoviedb.org/3"
VIDMODY_BASE = "https://vidmody.com/vs"
IMG_URL = "https://image.tmdb.org/t/p/w500"

MAX_WORKERS = 30
PAGE_DEPTH_ARCHIVE = 3
PAGE_DEPTH_NEW = 10

# --- GÜVENLİK AYARI (YENİ) ---
# GitHub Actions genelde 6 saat (21600 sn) verir.
# Biz 5.5 saatte (19800 sn) duralım ki kaydetmeye ve yüklemeye vakit kalsın.
MAX_RUN_TIME = 19800 

os.makedirs("output/diziler", exist_ok=True)
JSON_FILE = "output/series_all.json"
M3U_FILE = "output/series_all.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Tarih ve Kategori Ayarları
NEW_YEARS = [2026, 2025]
ARCHIVE_YEARS = range(2024, 1990, -1) 

GENRES = {
    10759: "Aksiyon & Macera",
    16: "Animasyon",
    35: "Komedi",
    80: "Suç",
    99: "Belgesel",
    18: "Dram",
    10751: "Aile",
    10762: "Çocuk",
    9648: "Gizem",
    10765: "Bilim Kurgu & Fantastik",
    37: "Vahşi Batı"
}

def load_existing_data():
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing_ids = {item['id'] for item in data if 'id' in item}
                print(f"--- HAFIZA: {len(data)} dizi yüklendi. ---")
                return data, existing_ids
        except:
            pass
    return [], set()

def check_single_url(url):
    try:
        response = requests.head(url, headers=HEADERS, timeout=2, allow_redirects=True)
        if response.status_code == 200:
            return url
    except:
        pass
    return None

def batch_check_urls(url_list):
    valid_urls = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(check_single_url, url): url for url in url_list}
        for future in concurrent.futures.as_completed(future_to_url):
            result = future.result()
            if result:
                valid_urls.add(result)
    return valid_urls

def get_imdb_id(tmdb_id):
    try:
        url = f"{BASE_URL}/tv/{tmdb_id}/external_ids?api_key={API_KEY}"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            return r.json().get("imdb_id")
    except:
        pass
    return None

def get_series_details(tmdb_id):
    try:
        url = f"{BASE_URL}/tv/{tmdb_id}?api_key={API_KEY}"
        return requests.get(url, timeout=3).json()
    except:
        return None

def save_files(all_series_data, m3u_entries):
    """Verileri diske kaydeder"""
    print("\n--- GÜVENLİ KAYIT YAPILIYOR ---")
    
    # JSON Kaydet
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(all_series_data, f, ensure_ascii=False, indent=4)
    
    # M3U Kaydet
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        # Sıralama
        def sort_key(item):
            cat = item.get("group_title", "")
            if cat == "Son Eklenenler": return 0
            if "Yerli" in cat: return 1
            return 2 
            
        for item in sorted(m3u_entries, key=sort_key):
            f.write(f'#EXTINF:-1 group-title="{item["group"]}" tvg-logo="{item["logo"]}", {item["name"]}\n')
            f.write(f'{item["url"]}\n')
    print("--- KAYIT TAMAMLANDI ---")

def process_series_batch(api_url, category_name, existing_ids, all_series_data, m3u_entries, add_year=False):
    try:
        response = requests.get(api_url, timeout=8)
        if response.status_code != 200: return False
        
        results = response.json().get('results', [])
        if not results: return False

        unknown_series = [s for s in results if s['id'] not in existing_ids]
        if not unknown_series: return True 

        for item in unknown_series:
            # --- ZAMAN KONTROLÜ (HER DİZİDE KONTROL ET) ---
            # Eğer global start_time değişkenini okuyamazsak diye parametre taşımak yerine
            # basitçe main fonksiyonundaki kontrolü bekleyebiliriz ama 
            # buraya da koymak en güvenlisidir.
            pass # Burası sadece yapı için, asıl kontrol main döngüsünde.

            tmdb_id = item['id']
            imdb_id = get_imdb_id(tmdb_id)
            if not imdb_id or imdb_id in existing_ids: continue

            test_link = f"{VIDMODY_BASE}/{imdb_id}/s1/e01"
            if not check_single_url(test_link): continue

            print(f"   > Bulundu: {item['name']}")
            details = get_series_details(tmdb_id)
            if not details: continue

            series_name = item['name']
            if add_year and item.get('first_air_date'):
                year = item['first_air_date'].split('-')[0]
                series_name = f"{series_name} ({year})"
            
            poster = f"{IMG_URL}{item['poster_path']}" if item.get('poster_path') else ""

            all_episode_links = []
            episode_map = {}

            for season in details.get('seasons', []):
                s_num = season['season_number']
                ep_count = season['episode_count']
                if s_num > 0:
                    for ep in range(1, ep_count + 1):
                        link = f"{VIDMODY_BASE}/{imdb_id}/s{s_num}/e{ep:02d}"
                        all_episode_links.append(link)
                        episode_map[link] = {"s": s_num, "e": ep}
            
            if all_episode_links:
                active_links = batch_check_urls(all_episode_links)
                if active_links:
                    existing_ids.add(item['id'])
                    sorted_links = sorted(list(active_links), key=lambda x: (episode_map[x]['s'], episode_map[x]['e']))
                    
                    series_obj = {
                        "id": item['id'],
                        "name": series_name,
                        "poster": poster,
                        "category": category_name,
                        "episodes": []
                    }

                    for link in sorted_links:
                        inf = episode_map[link]
                        series_obj["episodes"].append({
                            "season": inf['s'],
                            "episode": inf['e'],
                            "link": link
                        })
                        m3u_entries.append({
                            "group": category_name,
                            "logo": poster,
                            "name": f"{series_name} - S{inf['s']} B{inf['e']}",
                            "url": link,
                            "group_title": category_name
                        })
                    
                    all_series_data.append(series_obj)
                    print(f"     + Eklendi: {series_name} ({len(active_links)} Bölüm)")

        return True
    except:
        return False

def main():
    start_time = time.time()
    
    all_series_data, existing_ids = load_existing_data()
    m3u_entries = []

    # Eski verileri M3U listesine tekrar yükle
    for s in all_series_data:
        for ep in s['episodes']:
            m3u_entries.append({
                "group": s.get('category', 'Diziler'),
                "logo": s.get('poster', ''),
                "name": f"{s['name']} - S{ep['season']} B{ep['episode']}",
                "url": ep['link'],
                "group_title": s.get('category', 'Diziler')
            })

    # --- SÜRE DOLDU MU KONTROLÜ İÇİN FONKSİYON ---
    def is_time_up():
        if (time.time() - start_time) > MAX_RUN_TIME:
            print(f"\n!!! SÜRE DOLDU ({int((time.time() - start_time)/60)} dk). GÜVENLİ ÇIKIŞ YAPILIYOR !!!")
            return True
        return False

    # 1. VİTRİN
    print("\n=== BÖLÜM 1: VİTRİN ===")
    for year in NEW_YEARS:
        if is_time_up(): break # Süre kontrolü
        
        print(f"> {year}...")
        for page in range(1, PAGE_DEPTH_NEW + 1):
            if is_time_up(): break # Sayfa geçişinde kontrol
            url = f"{BASE_URL}/discover/tv?api_key={API_KEY}&language=tr-TR&sort_by=popularity.desc&first_air_date_year={year}&page={page}"
            process_series_batch(url, "Son Eklenenler", existing_ids, all_series_data, m3u_entries)

    # 2. YERLİ
    if not is_time_up():
        print("\n=== BÖLÜM 2: YERLİ ===")
        for page in range(1, 11):
            if is_time_up(): break
            url = f"{BASE_URL}/discover/tv?api_key={API_KEY}&language=tr-TR&sort_by=popularity.desc&with_original_language=tr&page={page}"
            process_series_batch(url, "Diziler | Yerli", existing_ids, all_series_data, m3u_entries, add_year=True)

    # 3. ARŞİV
    if not is_time_up():
        print(f"\n=== BÖLÜM 3: ARŞİV ===")
        for year in ARCHIVE_YEARS:
            if is_time_up(): break # Yıl bitince kontrol
            print(f"\n> Yıl: {year}...")
            
            for genre_id, genre_name in GENRES.items():
                if is_time_up(): break # Tür bitince kontrol
                
                for page in range(1, PAGE_DEPTH_ARCHIVE + 1):
                    # Burada her sayfa isteğinde de kontrol edebiliriz ama
                    # yıl/tür başlarında kontrol etmek genelde yeterlidir.
                    url = f"{BASE_URL}/discover/tv?api_key={API_KEY}&language=tr-TR&sort_by=popularity.desc&first_air_date_year={year}&with_genres={genre_id}&page={page}"
                    process_series_batch(url, f"Diziler | {genre_name}", existing_ids, all_series_data, m3u_entries, add_year=True)

    # --- SONUÇ ---
    # Döngü ya bittiği için ya da 'break' ile kırıldığı için buraya gelir.
    # Her iki durumda da KAYDETME işlemi çalışır.
    save_files(all_series_data, m3u_entries)
    
    print(f"Toplam Süre: {int(time.time() - start_time)} saniye.")

if __name__ == "__main__":
    main()
