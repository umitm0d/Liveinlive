import requests
from bs4 import BeautifulSoup
import re
import concurrent.futures
import time

# --- AYARLAR ---
BASE_URL = "https://www.hdfilmizle.life"
OUTPUT_FILE = "hdfilmizle.m3u"

# ARTIK FULL ÇEKİYOR
DIZI_BASLANGIC_SAYFASI = 1
DIZI_BITIS_SAYFASI = 50  # Dizi son sayfa

FILM_BASLANGIC_SAYFASI = 1
FILM_BITIS_SAYFASI = 975  # Film son sayfa (Bunu isteğine göre 1000 de yapabilirsin site arttıkça)

# Hız ayarı (Çok yüksek yaparsan GitHub IP'si banlanabilir, 10 ideal)
WORKER_COUNT = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": BASE_URL
}

def get_soup(url):
    """Verilen URL'e gider ve BeautifulSoup objesi döner. Hata alırsan 3 kez dener."""
    retries = 3
    for _ in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            time.sleep(2) # Hata olursa 2 saniye bekle tekrar dene
            continue
    return None

def extract_vidrame_m3u8(page_url):
    """Bir izleme sayfasındaki vidrame ID'sini bulur ve m3u8 linkini döner."""
    soup = get_soup(page_url)
    if not soup:
        return None

    iframe = soup.find("iframe", class_="vpx")
    if iframe:
        src = iframe.get("data-src") or iframe.get("src")
        if src and "vidrame.pro" in src:
            match = re.search(r"vidrame\.pro/vr/([a-zA-Z0-9]+)", src)
            if match:
                vid_id = match.group(1)
                return f"https://vidrame.pro/vr/get/{vid_id}/master.m3u8"
    return None

def process_episode(dizi_adi, poster_url, bolum_url, bolum_basligi):
    """Tek bir bölümü işler."""
    full_bolum_url = BASE_URL + bolum_url if not bolum_url.startswith("http") else bolum_url
    m3u8_link = extract_vidrame_m3u8(full_bolum_url)
    
    if m3u8_link:
        tvg_name = f"TR:{dizi_adi} {bolum_basligi}"
        entry = (
            f'#EXTINF:-1 tvg-id="" tvg-name="{tvg_name}" '
            f'tvg-logo="{poster_url}" group-title="Dizi-Panel-2",{tvg_name}\n'
            f'{m3u8_link}\n'
        )
        return entry
    return None

def process_movie(movie_card):
    """Tek bir filmi işler."""
    try:
        title_tag = movie_card.find("h2", class_="title")
        title = title_tag.text.strip() if title_tag else "Bilinmeyen Film"
        
        img_tag = movie_card.find("img", class_="lazyload")
        poster_path = ""
        if img_tag:
            poster_path = img_tag.get("data-src") or img_tag.get("src")
        
        poster_url = BASE_URL + poster_path if poster_path and not poster_path.startswith("http") else poster_path

        link_tag = movie_card
        href = link_tag.get("href")
        full_movie_url = BASE_URL + href if href else ""

        if full_movie_url:
            m3u8_link = extract_vidrame_m3u8(full_movie_url)
            if m3u8_link:
                tvg_name = f"TR:{title}"
                entry = (
                    f'#EXTINF:-1 tvg-id="" tvg-name="{tvg_name}" '
                    f'tvg-logo="{poster_url}" group-title="Film-Panel-2",{tvg_name}\n'
                    f'{m3u8_link}\n'
                )
                return entry
    except Exception:
        pass
    return None

def get_series_from_page(page_num):
    """Dizi sayfasını tarar."""
    url = f"{BASE_URL}/yabanci-dizi-izle-2/page/{page_num}/"
    soup = get_soup(url)
    entries = []
    
    if not soup: return []

    container = soup.find("div", id="moviesListResult")
    if not container: return []

    dizi_cards = container.find_all("a", class_="poster")
    
    for card in dizi_cards:
        dizi_href = card.get("href")
        dizi_full_url = dizi_href if dizi_href.startswith("http") else BASE_URL + dizi_href
        
        img_tag = card.find("img", class_="lazyload")
        poster_path = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""
        poster_url = BASE_URL + poster_path if poster_path and not poster_path.startswith("http") else poster_path
        
        title_tag = card.find("h2", class_="title")
        dizi_adi = title_tag.text.strip() if title_tag else "Bilinmeyen Dizi"

        detail_soup = get_soup(dizi_full_url)
        if detail_soup:
            episode_links = detail_soup.find_all("a", href=re.compile(r"/sezon-\d+/bolum-\d+/"))
            processed_urls = set()
            
            for ep_link in episode_links:
                ep_href = ep_link.get("href")
                if ep_href in processed_urls: continue
                processed_urls.add(ep_href)

                ep_title_tag = ep_link.find("h3")
                ep_title = ep_title_tag.text.strip() if ep_title_tag else "Bölüm X"
                
                entry = process_episode(dizi_adi, poster_url, ep_href, ep_title)
                if entry: entries.append(entry)
    return entries

def get_movies_from_page(page_num):
    """Film sayfasını tarar."""
    url = f"{BASE_URL}/page/{page_num}/" if page_num > 1 else f"{BASE_URL}/"
    if page_num == 1: url = f"{BASE_URL}/page/1/" 

    soup = get_soup(url)
    entries = []
    if not soup: return []

    container = soup.find("div", id="moviesListResult")
    if not container: return []

    movie_cards = container.find_all("a", class_="poster")
    for card in movie_cards:
        entry = process_movie(card)
        if entry: entries.append(entry)
    return entries

def main():
    print(f"Bot tam modda başlatılıyor. Diziler: {DIZI_BITIS_SAYFASI} sayfa, Filmler: {FILM_BITIS_SAYFASI} sayfa taranacak.")
    
    # Dosyayı sıfırdan oluştur
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

    # --- DİZİLER ---
    print("\n--- DİZİLER ÇEKİLİYOR ---")
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
        future_to_page = {executor.submit(get_series_from_page, i): i for i in range(DIZI_BASLANGIC_SAYFASI, DIZI_BITIS_SAYFASI + 1)}
        for future in concurrent.futures.as_completed(future_to_page):
            page_num = future_to_page[future]
            try:
                data = future.result()
                if data:
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                        for item in data: f.write(item)
                    print(f"[OK] Dizi Sayfası {page_num} bitti.")
                else:
                    print(f"[!] Dizi Sayfası {page_num} boş döndü.")
            except Exception as e:
                print(f"[HATA] Dizi Sayfa {page_num}: {e}")

    # --- FİLMLER ---
    print("\n--- FİLMLER ÇEKİLİYOR ---")
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
        future_to_page = {executor.submit(get_movies_from_page, i): i for i in range(FILM_BASLANGIC_SAYFASI, FILM_BITIS_SAYFASI + 1)}
        for future in concurrent.futures.as_completed(future_to_page):
            page_num = future_to_page[future]
            try:
                data = future.result()
                if data:
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                        for item in data: f.write(item)
                    print(f"[OK] Film Sayfası {page_num} bitti.")
                else:
                    print(f"[!] Film Sayfası {page_num} boş döndü.")
            except Exception as e:
                print(f"[HATA] Film Sayfa {page_num}: {e}")

    print(f"\nİşlem bitti! Tüm veriler '{OUTPUT_FILE}' dosyasına kaydedildi.")

if __name__ == "__main__":
    main()
