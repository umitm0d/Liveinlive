import time
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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def extract_slug(full_url):
    if not full_url: return None
    return full_url.rstrip('/').split('/')[-1]

def scrape_all_pages():
    driver = setup_driver()
    playlist_data = []
    seen_slugs = set()
    page_num = 1
    
    try:
        while True: # Sayfalar bitene kadar devam et
            page_url = f"{BASE_URL}/{page_num}"
            print(f"Tarama Yapılıyor: Sayfa {page_num}")
            
            driver.get(page_url)
            
            # Sayfada dizi kartlarının yüklenmesini bekle
            try:
                wait = WebDriverWait(driver, 10)
                # Sitedeki dizi listesi konteynerini bekliyoruz
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.little-series, .flex-wrap")))
            except:
                print("Daha fazla içerik bulunamadı veya sayfa yüklenemedi. Tarama bitiriliyor.")
                break

            # Sayfadaki linkleri topla
            # poster-xs ve poster-media sınıflarını içeren tüm a etiketlerini al
            cards = driver.find_elements(By.CSS_SELECTOR, ".poster-xs a, .poster-media a")
            
            if not cards:
                print(f"Sayfa {page_num} boş döndü. İşlem tamamlanıyor.")
                break

            new_items_count = 0
            for card in cards:
                try:
                    full_href = card.get_attribute("href")
                    slug = extract_slug(full_href)

                    if not slug or slug in seen_slugs or any(x in slug for x in ["kesfet", "takvim", "film-izle"]):
                        continue

                    # Başlık alma (p etiketi varsa detaylı, yoksa a içindeki text)
                    try:
                        title = card.find_element(By.CSS_SELECTOR, "p.truncate").text
                    except:
                        title = card.text.split('\n')[0] if card.text else slug
                    
                    if not title: title = slug

                    worker_link = f"{WORKER_BASE_URL}{slug}&ext=m3u8"
                    playlist_data.append((title, worker_link))
                    seen_slugs.add(slug)
                    new_items_count += 1
                except:
                    continue
            
            print(f"Sayfa {page_num}: {new_items_count} yeni içerik eklendi.")
            
            # Eğer bir sayfadan hiç yeni içerik gelmediyse muhtemelen sona ulaştık
            if new_items_count == 0:
                print("Yeni içerik bulunamadı, döngüden çıkılıyor.")
                break
                
            page_num += 1
            time.sleep(1) # Siteyi yormamak için kısa mola

    except Exception as e:
        print(f"Hata Oluştu: {e}")
    finally:
        driver.quit()
    
    return playlist_data

def save_m3u(data):
    if not data:
        print("Liste boş olduğu için dosya oluşturulmadı.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            # Başlıktaki virgülleri temizle (M3U formatı için önemli)
            clean_title = title.replace(",", " -")
            f.write(f'#EXTINF:-1 group-title="TvDiziler-Tum", {clean_title}\n')
            f.write(f"{link}\n")
    
    print(f"\n--- İŞLEM TAMAM ---")
    print(f"Toplam Sayfa: {page_num - 1}")
    print(f"Toplam İçerik: {len(data)}")
    print(f"Dosya: {OUTPUT_FILE}")

if __name__ == "__main__":
    all_data = scrape_all_pages()
    save_m3u(all_data)

Tarama Yapılıyor: Sayfa 1 

Daha fazla içerik bulunamadı veya sayfa yüklenemedi. Tarama bitiriliyor. 

Liste boş olduğu için dosya oluşturulmadı

 hatası veriyor halbuki var dosya
