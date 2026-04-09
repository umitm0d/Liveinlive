import requests
import json
import os
import re
import time
import concurrent.futures

# --- AYARLAR ---
API_KEY = "6fabef7bd74e01efcd81d35c39c4a049"
BASE_URL = "https://api.themoviedb.org/3"
VIDMODY_BASE = "https://vidmody.com/vs"
IMG_URL = "https://image.tmdb.org/t/p/w500"

# Her çalışmada kaç sayfa ileri gitsin? (Arşiv için)
STEP_SIZE = 500 
# Toplamda nerede dursun? (3000 sayfa = ~60.000 film)
MAX_TOTAL_PAGES = 3000
# Her çalışmada en baştan kaç sayfa taransın? (Yeni düşenleri yakalamak için)
FRESH_PAGES_CHECK = 10 

MAX_WORKERS = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Dosya Yolları
DB_FILE = "output/movies_db.json" # Ana veritabanı (silinmez, büyür)
STATE_FILE = "output/movie_state.json" # Nerede kaldığımızı tutar
M3U_FILE = "output/movies_all.m3u"

os.makedirs("output", exist_ok=True)

# --- YARDIMCI FONKSİYONLAR ---
def load_json(path, default_val):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default_val

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get("imdb_id")
    except:
        return None
    return None

# --- TARAMA MOTORU ---
def scrape_pages(start_page, end_page, label="Tarama"):
    print(f"--- {label}: Sayfa {start_page} - {end_page} arası taranıyor ---")
    found_movies = {} # ID bazlı dictionary (Duplicate önlemek için)

    for page in range(start_page, end_page + 1):
        try:
            url = f"{BASE_URL}/movie/popular?api_key={API_KEY}&language=tr-TR&page={page}"
            data = requests.get(url).json()
            results = data.get('results', [])

            pending_checks = []
            movie_map = {}

            # Linkleri hazırla
            for item in results:
                tmdb_id = item['id']
                imdb_id = get_imdb_id(tmdb_id)
                
                if imdb_id:
                    link = f"{VIDMODY_BASE}/{imdb_id}"
                    pending_checks.append(link)
                    movie_map[link] = {
                        "id": imdb_id,
                        "tmdb_id": tmdb_id,
                        "title": item['title'],
                        "poster": f"{IMG_URL}{item['poster_path']}" if item.get('poster_path') else "",
                        "overview": item.get('overview', ""),
                        "release_date": item.get('release_date', ""),
                        "vote_average": item.get('vote_average', 0)
                    }

            # Toplu kontrol et
            if pending_checks:
                active_links = batch_check_urls(pending_checks)
                print(f"   Sayfa {page}: {len(active_links)} aktif film bulundu.")

                for link in active_links:
                    info = movie_map[link]
                    # Sözlüğe kaydet (key = imdb_id) böylece aynı film tekrar eklenmez
                    found_movies[info['id']] = {
                        "id": info['id'],
                        "title": info['title'],
                        "poster": info['poster'],
                        "link": link,
                        "group": "Yeni Eklenenler" if page <= FRESH_PAGES_CHECK else "Filmler"
                    }
        except Exception as e:
            print(f"   Hata (Sayfa {page}): {e}")
            
    return found_movies

# --- ANA İŞLEM ---
if __name__ == "__main__":
    start_time = time.time()

    # 1. Eski Veritabanını ve Durumu Yükle
    # Veritabanını {imdb_id: data} formatına çeviriyoruz ki güncelleme kolay olsun
    db_list = load_json(DB_FILE, [])
    # Listeyi dictionary'e çevir (Hızlı arama ve güncelleme için)
    full_db = {item['id']: item for item in db_list}
    
    state = load_json(STATE_FILE, {"last_page": 0})
    current_last_page = state["last_page"]

    print(f"BAŞLANGIÇ DURUMU: Veritabanında {len(full_db)} film var. Son taranan sayfa: {current_last_page}")

    # 2. ADIM: TAZELEME (İlk sayfaları kontrol et - Yeni çıkanlar)
    print("\n>>> MOD 1: YENİ İÇERİK KONTROLÜ (İlk sayfalar) <<<")
    fresh_movies = scrape_pages(1, FRESH_PAGES_CHECK, label="Tazeleme")
    
    # Yeni bulunanları DB'ye ekle veya güncelle
    for mid, mdata in fresh_movies.items():
        mdata['group'] = "Yeni Eklenenler" # Grubunu güncelle
        full_db[mid] = mdata # Varsa üzerine yazar (günceller), yoksa ekler.

    # 3. ADIM: ARŞİV (Kaldığı yerden devam et)
    if current_last_page < MAX_TOTAL_PAGES:
        start_p = current_last_page + 1
        end_p = min(current_last_page + STEP_SIZE, MAX_TOTAL_PAGES)
        
        print(f"\n>>> MOD 2: ARŞİV GENİŞLETME (Sayfa {start_p} - {end_p}) <<<")
        archive_movies = scrape_pages(start_p, end_p, label="Arşiv")
        
        # Arşivden gelenleri DB'ye ekle
        for mid, mdata in archive_movies.items():
            if mid not in full_db: # Sadece veritabanında YOKSA ekle
                mdata['group'] = "Filmler"
                full_db[mid] = mdata
        
        # Yeni konumu kaydet
        state["last_page"] = end_p
    else:
        print("\n>>> HEDEF SAYFAYA (3000) ULAŞILDI. SADECE YENİLER GÜNCELLENDİ. <<<")

    # 4. KAYDETME
    print("\n--- KAYIT İŞLEMLERİ ---")
    
    # Dictionary'i tekrar Listeye çevirip kaydet
    final_list = list(full_db.values())
    
    # En yeniler en üstte olsun diye ID veya Tarihe göre sıralayabilirsin.
    # Burada basitçe ters çeviriyoruz (genellikle son eklenenler sonda olur, başa alalım)
    # Veya 'Yeni Eklenenler' grubunu başa alabiliriz:
    final_list.sort(key=lambda x: 0 if x.get('group') == "Yeni Eklenenler" else 1)

    save_json(DB_FILE, final_list)
    save_json(STATE_FILE, state)

    # M3U Oluştur
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for item in final_list:
            grp = item.get('group', 'Filmler')
            f.write(f'#EXTINF:-1 group-title="{grp}" tvg-logo="{item["poster"]}", {item["title"]}\n')
            f.write(f'{item["link"]}\n')

    print(f"BİTTİ. Toplam Film: {len(final_list)}. Son Sayfa: {state['last_page']}")
    print(f"Süre: {int(time.time() - start_time)} sn.")
