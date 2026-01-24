import time
import os
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
    
    # GitHub Actions ve Performans Ayarları
    chrome_options.add_argument("--headless") # Tarayıcıyı gizli modda çalıştır
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false") # Resimleri yükleme (Hız için)
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Anti-bot koruma önlemleri
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # GitHub Actions path kontrolü
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
    """URL'den son kısmı (slug) çıkarır"""
    if not full_url: return None
    return full_url.rstrip('/').split('/')[-1]

def get_latest_episode_slug(driver, show_url):
    """
    Dizi sayfasına gider ve en son bölümün (veya ilk sıradaki bölümün) slug'ını bulur.
    Örnek hedef: esref-ruya-29-bolum-full-izle
    """
    try:
        driver.get(show_url)
        # Sayfanın yüklenmesini bekle
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Olası bölüm linklerini ara. Genellikle "full-izle" veya "bolum-izle" içerir.
        # "fragman" içerenleri hariç tutacağız.
        potential_links = driver.find_elements(By.TAG_NAME, "a")
        
        for link in potential_links:
            href = link.get_attribute("href")
            text = link.text.lower()
            
            if href and ("-bolum-" in href or "full-izle" in href):
                # Fragmanları atla
                if "fragman" in href or "tanitim" in href:
                    continue
                
                # Slug'ı al
                slug = extract_slug(href)
                
                # Eğer slug mantıklıysa (dizi anasayfası değilse) döndür
                if slug and slug != extract_slug(show_url):
                    return slug
                    
        return None
    except Exception as e:
        print(f"    Bölüm bulma hatası: {e}")
        return None

def scrape_all_pages():
    driver = None
    playlist_data = []
    
    # Önce tüm dizi URL'lerini toplayacağız
    series_urls = []
    
    try:
        driver = setup_driver()
        print(f"1. AŞAMA: Dizi Listesi Taranıyor: {BASE_URL}")
        
        driver.get(BASE_URL)
        time.sleep(5) 
        
        # Tüm linkleri al
        all_links = driver.find_elements(By.TAG_NAME, "a")
        
        seen_urls = set()
        
        for link in all_links:
            try:
                href = link.get_attribute("href")
                text = link.text.strip()
                
                if href and "/dizi/" in href and len(text) > 2:
                    if href not in seen_urls:
                        # Filtreleme
                        if any(x in href for x in ["takvim", "profil", "giris"]):
                            continue
                            
                        series_urls.append((text, href))
                        seen_urls.add(href)
            except:
                continue
                
        print(f"✓ Toplam {len(series_urls)} dizi bulundu. Şimdi bölüm linkleri aranacak...")
        
        # 2. AŞAMA: Her dizinin içine girip bölüm linki al
        # GitHub Actions'ta zaman aşımını önlemek için max 50 dizi ile sınırlayabilirsin.
        # Hepsini istiyorsan aşağıdaki [:50] kısmını kaldır.
        for index, (title, url) in enumerate(series_urls): 
            print(f"[{index+1}/{len(series_urls)}] İşleniyor: {title}")
            
            episode_slug = get_latest_episode_slug(driver, url)
            
            if episode_slug:
                # Worker linkini oluştur
                worker_link = f"{WORKER_BASE_URL}{episode_slug}&ext=m3u8"
                playlist_data.append((title, worker_link))
                print(f"    ✓ Bulundu: {episode_slug}")
            else:
                print(f"    ✗ Bölüm linki bulunamadı.")
            
            # Sunucuyu yormamak için kısa bekleme
            # time.sleep(0.5) 
            
    except Exception as e:
        print(f"Genel Hata: {e}")
    finally:
        if driver:
            driver.quit()
            
    return playlist_data

def save_m3u(data):
    if not data:
        print("Liste boş, dosya oluşturulmuyor.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            clean_title = title.replace(",", " -").replace('"', "'")
            f.write(f'#EXTINF:-1 group-title="Diziler", {clean_title}\n')
            f.write(f"{link}\n")
    
    print(f"\nDosya kaydedildi: {OUTPUT_FILE}")
    print(f"Toplam Eklenen Dizi: {len(data)}")

if __name__ == "__main__":
    data = scrape_all_pages()
    save_m3u(data)
