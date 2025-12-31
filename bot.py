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
SITE_URL = "https://tvdiziler.tv"
WORKER_BASE_URL = "https://tvdiziler.umittv.workers.dev/?id="
OUTPUT_FILE = "iptv_list.m3u"

def setup_driver():
    """GitHub Actions ve Linux sunucularda çalışacak 'Headless' Chrome ayarları."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ekran olmadan çalıştır
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    # Sürücüyü otomatik yükle ve başlat
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def extract_slug(full_url):
    """URL'den video kimliğini (slug) ayıklar."""
    if not full_url: return None
    return full_url.rstrip('/').split('/')[-1]

def scrape_tvdiziler():
    driver = setup_driver()
    playlist_data = []
    seen_slugs = set()

    try:
        print(f"Bağlanıyor: {SITE_URL}")
        driver.get(SITE_URL)

        # Sayfanın yüklenmesi için bekle
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.little-series")))

        # Lazy-load (yavaş yüklenen) içerikler için sayfayı aşağı kaydır
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)

        # Hem büyük bannerları hem de alt listeyi tara
        # Verdiğin HTML yapısındaki linkleri yakalıyoruz
        cards = driver.find_elements(By.CSS_SELECTOR, ".poster-media, .poster-xs")

        for card in cards:
            try:
                link_elem = card.find_element(By.TAG_NAME, "a")
                full_href = link_elem.get_attribute("href")
                slug = extract_slug(full_href)

                if not slug or slug in seen_slugs or "javascript" in slug:
                    continue

                # Başlık tespiti (P etiketi daha detaylı bilgi içeriyor)
                try:
                    title = card.find_element(By.CSS_SELECTOR, "p.truncate").text
                except:
                    title = card.find_element(By.TAG_NAME, "h2").text

                if not title: title = slug

                # Linki Worker formatına sok
                worker_link = f"{WORKER_BASE_URL}{slug}"
                
                playlist_data.append((title, worker_link))
                seen_slugs.add(slug)
                print(f"Eklendi: {title}")

            except:
                continue

    except Exception as e:
        print(f"Hata çıktı: {e}")
    finally:
        driver.quit()
    
    return playlist_data

def save_m3u(data):
    """M3U8 Dosyasını UTF-8 formatında kaydeder."""
    if not data:
        print("Veri bulunamadı, dosya oluşturulmadı.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            f.write(f'#EXTINF:-1 group-title="TvDiziler", {title}\n')
            f.write(f"{link}\n")
    print(f"Başarılı: {OUTPUT_FILE} oluşturuldu. Toplam: {len(data)}")

if __name__ == "__main__":
    results = scrape_tvdiziler()
    save_m3u(results)
