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
        while True:
            if page_num == 1:
                page_url = BASE_URL  # İlk sayfa için sadece BASE_URL kullan
            else:
                page_url = f"{BASE_URL}/{page_num}"
            
            print(f"Tarama Yapılıyor: Sayfa {page_num} - {page_url}")
            
            driver.get(page_url)
            
            # Sayfanın yüklenmesini bekle
            time.sleep(3)  # Daha uzun bekleme süresi
            
            # Daha esnek bir bekleme stratejisi
            try:
                # Sayfada herhangi bir içeriğin yüklenmesini bekle
                wait = WebDriverWait(driver, 15)
                # Farklı olası konteynerları dene
                selectors_to_try = [
                    "div[class*='series']", 
                    "div[class*='dizi']",
                    "a[href*='/dizi/']",
                    "div.poster",
                    "div.card",
                    "ul.little-series",
                    "div.flex-wrap",
                    "body"
                ]
                
                for selector in selectors_to_try:
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        print(f"Sayfa yüklendi - bulunan element: {selector}")
                        break
                    except:
                        continue
                
            except Exception as e:
                print(f"Sayfa yüklenirken hata: {e}")
                # Ekran görüntüsü al (hata ayıklama için)
                try:
                    driver.save_screenshot(f"error_page_{page_num}.png")
                except:
                    pass
                break

            # Dizi linklerini bul - tüm olası seçenekleri dene
            card_selectors = [
                "a[href*='/dizi/']",
                "div.poster a",
                "div.card a",
                ".poster-xs a",
                ".poster-media a",
                "ul.little-series a",
                "div.series-item a",
                "div[class*='series-card'] a"
            ]
            
            cards = []
            for selector in card_selectors:
                try:
                    found_cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if found_cards:
                        print(f"{len(found_cards)} adet kart bulundu - selector: {selector}")
                        cards.extend(found_cards)
                        # Benzersiz kartları al
                        unique_cards = []
                        seen_hrefs = set()
                        for card in cards:
                            href = card.get_attribute("href")
                            if href and href not in seen_hrefs:
                                seen_hrefs.add(href)
                                unique_cards.append(card)
                        cards = unique_cards
                        break
                except:
                    continue
            
            if not cards:
                print(f"Sayfa {page_num} boş döndü veya kartlar bulunamadı.")
                
                # Sayfa içeriğini kontrol et
                page_content = driver.page_source[:500] if driver.page_source else "Boş"
                print(f"Sayfa içeriği (ilk 500 karakter): {page_content}")
                
                # Hata durumunda sayfanın HTML'sini kaydet
                with open(f"debug_page_{page_num}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                
                if page_num == 1:
                    print("İlk sayfa bile yüklenemedi. Site yapısı değişmiş olabilir.")
                break

            print(f"Sayfa {page_num}: {len(cards)} adet potansiyel dizi kartı bulundu")

            new_items_count = 0
            for i, card in enumerate(cards):
                try:
                    full_href = card.get_attribute("href")
                    if not full_href or "/dizi/" not in full_href:
                        continue
                    
                    slug = extract_slug(full_href)

                    if not slug or slug in seen_slugs:
                        continue

                    # Başlık alma
                    title = ""
                    try:
                        # Önce img alt text'ini dene
                        img = card.find_element(By.CSS_SELECTOR, "img")
                        title = img.get_attribute("alt")
                    except:
                        try:
                            # Sonra p veya span içindeki text'i dene
                            title_elem = card.find_element(By.CSS_SELECTOR, "p, span, h3, h4, div[class*='title']")
                            title = title_elem.text.strip()
                        except:
                            # En son kendi text'ini al
                            title = card.text.strip()
                    
                    if not title or len(title) < 2:
                        title = slug.replace("-", " ").title()
                    
                    # Başlığı temizle
                    title = " ".join(title.split())  # Fazla boşlukları temizle
                    
                    worker_link = f"{WORKER_BASE_URL}{slug}&ext=m3u8"
                    playlist_data.append((title, worker_link))
                    seen_slugs.add(slug)
                    new_items_count += 1
                    
                    if new_items_count % 10 == 0:
                        print(f"  İşlenen: {new_items_count}/{len(cards)}")
                        
                except Exception as e:
                    print(f"Kart işlenirken hata ({i}. kart): {str(e)[:100]}")
                    continue
            
            print(f"Sayfa {page_num}: {new_items_count} yeni içerik eklendi.")
            
            # Sonraki sayfa butonunu kontrol et
            try:
                next_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'Sonraki') or contains(text(), 'İleri') or contains(text(), 'Next')]")
                next_buttons.extend(driver.find_elements(By.CSS_SELECTOR, "[rel='next'], .next-page, .pagination-next"))
                
                has_next_page = False
                for btn in next_buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        has_next_page = True
                        break
                
                if not has_next_page and new_items_count == 0:
                    print("Son sayfaya ulaşıldı.")
                    break
                    
            except:
                # Pagination bulunamazsa, bir sonraki sayfa numarasını dene
                if new_items_count == 0 and page_num > 1:
                    print("Yeni içerik bulunamadı, döngüden çıkılıyor.")
                    break
            
            page_num += 1
            time.sleep(2)  # Siteyi yormamak için bekle

    except Exception as e:
        print(f"Ana hata oluştu: {e}")
        import traceback
        traceback.print_exc()
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
            # Diğer özel karakterleri de temizle
            clean_title = clean_title.replace("\"", "'")
            f.write(f'#EXTINF:-1 group-title="TvDiziler-Tum", {clean_title}\n')
            f.write(f"{link}\n")
    
    print(f"\n--- İŞLEM TAMAM ---")
    print(f"Toplam İçerik: {len(data)}")
    print(f"Dosya: {OUTPUT_FILE}")
    
    # Hangi dizilerin eklendiğini göster
    print("\n--- EKLENEN İLK 10 DİZİ ---")
    for i, (title, _) in enumerate(data[:10], 1):
        print(f"{i}. {title}")

if __name__ == "__main__":
    print("TV Dizileri tarayıcısı başlatılıyor...")
    all_data = scrape_all_pages()
    save_m3u(all_data)
