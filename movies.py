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

MAX_WORKERS = 30         # Hız
PAGE_DEPTH_ARCHIVE = 5   # Eski yıllar için sayfa derinliği
PAGE_DEPTH_NEW = 20      # Yeni yıllar (Vitrin) için sayfa derinliği

# Klasör Kontrolü
os.makedirs("output", exist_ok=True)
JSON_FILE = "output/movies_all.json"
M3U_FILE = "output/movies_all.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# --- TARİH ARALIĞI (SİNEMA TARİHİNE GÖRE DÜZENLENDİ) ---
# 1. Vitrin Yılları (Son Eklenenler - En Üstte)
NEW_YEARS = [2026, 2025]

# 2. Arşiv Yılları (Geriye Kalanlar)
# 2024'ten başlar, 1880'e (İlk filmlere) kadar iner.
ARCHIVE_YEARS = range(2024, 1880, -1) 

# --- KATEGORİLER ---
GENRES = {
    28: "Aksiyon",
    12: "Macera",
    16: "Animasyon",
    35: "Komedi",
    80: "Suç",
    99: "Belgesel",
    18: "Dram",
    10751: "Aile",
    14: "Fantastik",
    36: "Tarih",
    27: "Korku",
    10402: "Müzik",
    9648: "Gizem",
    10749: "Romantik",
    878: "Bilim Kurgu",
    10770: "TV Filmi",
    53: "Gerilim",
    10752: "Savaş",
    37: "Vahşi Batı"
}

def load_existing_data():
    """Hafızayı yükler (Eski kayıtları hatırlar)"""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing_ids = {item['id'] for item in data if 'id' in item}
                print(f"--- HAFIZA: {len(data)} film zaten var. Üstüne ekleniyor. ---")
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
        url = f"{BASE_URL}/movie/{tmdb_id}/external_ids?api_key={API_KEY}"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            return r.json().get("imdb_id")
    except:
        pass
    return None

def save_m3u(filename, content_list):
    """M3U Sıralaması: 1. Son Eklenenler, 2. Yerli, 3. Diğerleri"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        def sort_key(item):
            cat = item.get("category", "")
            if cat == "Son Eklenenler": return 0
            if "Yerli" in cat: return 1
            return 2 
            
        sorted_list = sorted(content_list, key=sort_key)
        
        for item in sorted_list:
            group = item.get("category", "Filmler")
            title = item.get("title", "Bilinmeyen")
            f.write(f'#EXTINF:-1 group-title="{group}" tvg-logo="{item.get("poster", "")}", {title}\n')
            f.write(f'{item.get("link", "")}\n')

def process_batch(api_url, category_name, existing_ids, all_movies, add_year=False):
    """API işlemleri"""
    try:
        response = requests.get(api_url, timeout=8)
        if response.status_code != 200: return False 
        
        results = response.json().get('results', [])
        if not results: return False

        pending_checks = []
        movie_map = {}
        
        # Veritabanında olmayanları ayır
        unknown_movies = [m for m in results if m['id'] not in existing_ids]
        if not unknown_movies: return True

        for item in unknown_movies:
            imdb_id = get_imdb_id(item['id'])
            if imdb_id and imdb_id not in existing_ids:
                link = f"{VIDMODY_BASE}/{imdb_id}"
                pending_checks.append(link)
                
                title_text = item['title']
                if add_year and item.get('release_date'):
                    year_str = item['release_date'].split('-')[0]
                    title_text = f"{title_text} ({year_str})"

                movie_map[link] = {
                    "id": item['id'],
                    "title": title_text,
                    "poster": f"{IMG_URL}{item['poster_path']}" if item.get('poster_path') else "",
                    "category": category_name
                }

        if pending_checks:
            active_links = batch_check_urls(pending_checks)
            count = 0
            for link in active_links:
                info = movie_map[link]
                if info['id'] not in existing_ids:
                    existing_ids.add(info['id'])
                    all_movies.append({
                        "id": info['id'],
                        "title": info['title'],
                        "poster": info['poster'],
                        "link": link,
                        "category": info['category']
                    })
                    count += 1
            if count > 0:
                print(f"   + {count} film -> {category_name}")
        return True

    except Exception as e:
        print(f"Hata: {e}")
        return False

def main():
    start_time = time.time()
    all_movies, existing_ids = load_existing_data()
    
    # --- 1. VİTRİN (2026-2025) ---
    print("\n=== BÖLÜM 1: VİTRİN (SON EKLENENLER) ===")
    for year in NEW_YEARS:
        print(f"> {year} Vitrini Taranıyor...")
        for page in range(1, PAGE_DEPTH_NEW + 1):
            url = f"{BASE_URL}/discover/movie?api_key={API_KEY}&language=tr-TR&sort_by=popularity.desc&primary_release_year={year}&page={page}"
            if not process_batch(url, "Son Eklenenler", existing_ids, all_movies):
                break

    # --- 2. YERLİ FİLMLER (Tüm Tarih) ---
    print("\n=== BÖLÜM 2: YERLİ FİLMLER ===")
    for page in range(1, 21):
        url = f"{BASE_URL}/discover/movie?api_key={API_KEY}&language=tr-TR&sort_by=popularity.desc&with_original_language=tr&page={page}"
        if not process_batch(url, "Filmler | Yerli", existing_ids, all_movies, add_year=True):
            break

    # --- 3. BÜYÜK ARŞİV (2024 -> 1880) ---
    print(f"\n=== BÖLÜM 3: SİNEMA TARİHİ ({ARCHIVE_YEARS.start} - {ARCHIVE_YEARS.stop}) ===")
    
    for year in ARCHIVE_YEARS:
        print(f"\n> Yıl: {year} işleniyor...")
        has_movies_in_year = False
        
        for genre_id, genre_name in GENRES.items():
            for page in range(1, PAGE_DEPTH_ARCHIVE + 1):
                url = f"{BASE_URL}/discover/movie?api_key={API_KEY}&language=tr-TR&sort_by=popularity.desc&primary_release_year={year}&with_genres={genre_id}&page={page}"
                
                result = process_batch(url, f"Filmler | {genre_name}", existing_ids, all_movies, add_year=True)
                
                if result: has_movies_in_year = True
                else: break 
        
        if not has_movies_in_year:
            print(f"   (Bu yılda veri bulunamadı, hızlı geçiliyor...)")

    # --- KAYIT ---
    print("\n--- KAYDEDİLİYOR ---")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(all_movies, f, ensure_ascii=False, indent=4)
    
    save_m3u(M3U_FILE, all_movies)
    
    print(f"TAMAMLANDI. Toplam Film: {len(all_movies)}")
    print(f"Süre: {int(time.time() - start_time)} sn.")

if __name__ == "__main__":
    main()
