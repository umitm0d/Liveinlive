import time
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- AYARLAR ---
BASE_URL = "https://tvdiziler.tv/dizi-izle"
WORKER_BASE_URL = "https://tvdiziler.umittv.workers.dev/?id=" 
OUTPUT_FILE = "iptv_list.m3u"

def setup_driver():
    chrome_options = Options()
    
    # Performans ve Stabilite Ayarları
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    # Resimleri kapatarak sayfa geçişlerini hızlandır
    chrome_options.add_argument("--blink-settings=imagesEnabled=false") 
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Anti-bot
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    if os.path.exists("/usr/bin/google-chrome"):
        chrome_options.binary_location = "/usr/bin/google-chrome"
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"Driver oluşturma hatası: {e}")
        raise

def extract_slug(full_url):
    if not full_url: return None
    return full_url.rstrip('/').split('/')[-1]

def get_latest_episode_slug(driver, show_url):
    """
    Dizi sayfasına girip en güncel bölümün slug'ını alır.
    DÜZELTME: Yan menüdeki (Medcezir gibi) linkleri değil, 
    sadece o diziye ait linkleri alır.
    """
    try:
        # Şu an taranan dizinin ana slug'ını al (örn: bir-peri-masali)
        current_show_slug = extract_slug(show_url)
        
        # Dizi sayfasına git
        driver.get(show_url)
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Sayfadaki tüm linkleri al
        potential_links = driver.find_elements(By.TAG_NAME, "a")
        
        # Bölüm linklerini filtrele
        valid_episodes = []
        
        for link in potential_links:
            try:
                href = link.get_attribute("href")
                if not href: continue
                
                slug = extract_slug(href)
                if not slug: continue
                
                # KRİTİK KONTROL: Bulunan link, dizinin kendi ismini içeriyor mu?
                # Eğer dizi "bir-peri-masali" ise, bulunan linkte "bir-peri-masali" geçmeli.
                # "medcezir" linkinde bu geçmediği için elenecek.
                if current_show_slug not in slug:
                    continue
                
                # Gereksiz linkleri ele
                ignorable = ["fragman", "tanitim", "oyuncular", "cast", "takvim", "page="]
                if any(x in slug for x in ignorable):
                    continue

                # Sadece bölüm veya izleme linki mi?
                if "bolum" in slug or "izle" in slug:
                    # Ana dizi linkinin aynısıysa alma
                    if slug == current_show_slug:
                        continue
                        
                    valid_episodes.append(slug)
                    
            except:
                continue
        
        # Eğer geçerli bölümler bulduysak
        if valid_episodes:
            # Genellikle en üstteki veya listedeki ilk link en yeni bölümdür.
            # Medcezir sorunu 'current_show_slug not in slug' ile çözüldü.
            return valid_episodes[0]

        return None
        
    except Exception as e:
        return None

def scrape_all_pages():
    driver = None
    playlist_data = []
    series_urls = []
    
    try:
        driver = setup_driver()
        print(f"Tarama Başlatılıyor...")
        
        driver.get(BASE_URL)
        page_num = 1
        
        # --- 1. AŞAMA: TÜM SAYFALARDAKİ DİZİLERİ TOPLA ---
        while True:
            print(f"\n--- Sayfa {page_num} taranıyor ---")
            
            # Sayfanın yüklendiğinden emin ol
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
            
            current_page_links = driver.find_elements(By.TAG_NAME, "a")
            count_on_page = 0
            
            for link in current_page_links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    
                    # Dizi kartlarını tespit etme filtresi
                    if href and "/dizi/" in href and len(text) > 1:
                        # Gereksiz linkleri ele
                        if any(x in href for x in ["page=", "takvim", "profil", "giris", "tur/"]):
                            continue
                        
                        # Zaten listeye eklenmemişse ekle
                        if not any(s[1] == href for s in series_urls):
                            series_urls.append((text, href))
                            count_on_page += 1
                except:
                    continue
            
            print(f"✓ Sayfa {page_num}: {count_on_page} yeni dizi bulundu.")
            
            # SONRAKİ SAYFA KONTROLÜ
            try:
                # Pagination (Sayfalama) yapısını bulmaya çalış
                # Genellikle "»" işareti veya "Sonraki" yazısı olur
                next_page_btn = None
                
                # Farklı seçiciler dene
                selectors = [
                    "//a[contains(text(), '»')]",
                    "//a[contains(@class, 'page-link') and contains(@href, 'page=')]",
                    f"//a[contains(@href, 'page={page_num + 1}')]"
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            # O anki sayfadan daha büyük bir sayfa numarasına gidiyor mu?
                            for elem in elements:
                                next_href = elem.get_attribute("href")
                                if next_href and f"page={page_num + 1}" in next_href:
                                    next_page_btn = next_href
                                    break
                        if next_page_btn: break
                    except:
                        continue
                
                if next_page_btn:
                    print(f"» Sonraki sayfaya geçiliyor: {next_page_btn}")
                    driver.get(next_page_btn)
                    page_num += 1
                    time.sleep(3) # Sayfa yüklemesi için bekle
                else:
                    print("Listedeki son sayfaya gelindi veya sonraki sayfa butonu bulunamadı.")
                    break
                    
            except Exception as e:
                print(f"Sayfa geçiş hatası: {e}")
                break
        
        print(f"\n{'='*40}")
        print(f"TOPLAM {len(series_urls)} DİZİ BULUNDU. BÖLÜMLER ARANIYOR...")
        print(f"{'='*40}")
        
        # --- 2. AŞAMA: HER DİZİNİN SON BÖLÜMÜNÜ BUL ---
        for index, (title, url) in enumerate(series_urls):
            # İlerleme durumunu göster
            print(f"[{index+1}/{len(series_urls)}] {title} taranıyor...")
            
            episode_slug = get_latest_episode_slug(driver, url)
            
            if episode_slug:
                worker_link = f"{WORKER_BASE_URL}{episode_slug}&ext=m3u8"
                playlist_data.append((title, worker_link))
                print(f"  ✓ ID: {episode_slug}")
            else:
                print(f"  ✗ Bölüm bulunamadı")

    except Exception as e:
        print(f"KRİTİK HATA: {e}")
    finally:
        if driver:
            driver.quit()
    
    return playlist_data

def save_m3u(data):
    if not data:
        print("Veri yok, dosya oluşturulmadı.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            clean_title = title.replace(",", " -").replace('"', "'")
            f.write(f'#EXTINF:-1 group-title="Diziler", {clean_title}\n')
            f.write(f"{link}\n")
    
    print(f"\nTAMAMLANDI! Dosya: {OUTPUT_FILE}")
    print(f"Toplam Kanal: {len(data)}")

if __name__ == "__main__":
    scrape_data = scrape_all_pages()
    save_m3u(scrape_data)
