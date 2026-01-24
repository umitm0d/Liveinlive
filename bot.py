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
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def extract_slug_from_href(href):
    """https://tvdiziler.tv/esref-ruya-29-bolum-full-izle -> esref-ruya-29-bolum-full-izle"""
    if not href:
        return None
    
    # URL'yi temizle
    href = href.strip()
    
    # Base URL'yi kaldır
    if href.startswith("https://tvdiziler.tv/"):
        slug = href[22:]  # "https://tvdiziler.tv/" sonrasını al
    elif href.startswith("/"):
        slug = href[1:]  # Başındaki / kaldır
    else:
        slug = href
    
    # Sondaki / varsa kaldır
    slug = slug.rstrip('/')
    
    # Sadece bölüm içeren slug'ları al
    # "bolum" veya "son-bolum" içermeli
    if "bolum" not in slug.lower():
        return None
    
    # "izle" ile bitmeli
    if not slug.endswith("-izle"):
        # Eğer "full-izle" ile bitiyorsa, sadece "izle" yap
        if slug.endswith("-full-izle"):
            slug = slug[:-10] + "-izle"
        else:
            slug = slug + "-izle"
    
    return slug

def scrape_all_pages():
    driver = setup_driver()
    playlist_data = []
    seen_slugs = set()
    page_num = 1
    
    try:
        while True:
            if page_num == 1:
                page_url = BASE_URL
            else:
                page_url = f"{BASE_URL}/{page_num}"
            
            print(f"\n{'='*60}")
            print(f"Sayfa {page_num} taranıyor: {page_url}")
            print(f"{'='*60}")
            
            driver.get(page_url)
            
            # Sayfanın yüklenmesini bekle
            time.sleep(5)
            
            # Sayfanın yüklendiğini kontrol et
            try:
                # Farklı olası elementleri dene
                selectors = [
                    ".little-series", 
                    ".poster-xs",
                    ".poster-media",
                    "ul li",
                    "div[class*='series']"
                ]
                
                element_found = False
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if len(elements) > 0:
                            print(f"✓ Element bulundu: {selector} ({len(elements)} adet)")
                            element_found = True
                            break
                    except:
                        continue
                
                if not element_found:
                    print("⚠ Hiç element bulunamadı!")
                    # Debug için sayfa kaynağını göster
                    page_source = driver.page_source[:500]
                    print(f"Sayfa (ilk 500 karakter):\n{page_source}")
                    
            except Exception as e:
                print(f"⚠ Bekleme hatası: {e}")
            
            # 1. YÖNTEM: Son bölümlerden (little-series)
            print("\n1. Son bölümleri tarıyor...")
            episode_cards = driver.find_elements(By.CSS_SELECTOR, ".little-series li, .poster-xs, div[class*='poster']")
            print(f"   Bulunan kart: {len(episode_cards)}")
            
            # 2. YÖNTEM: Tüm linkleri tarı
            print("\n2. Tüm linkleri tarıyor...")
            all_links = driver.find_elements(By.TAG_NAME, "a")
            print(f"   Toplam link: {len(all_links)}")
            
            # Tüm yöntemleri birleştir
            all_elements = episode_cards + all_links
            
            new_items_count = 0
            processed_count = 0
            
            for element in all_elements:
                try:
                    processed_count += 1
                    
                    # Elementten href al
                    if hasattr(element, 'get_attribute'):
                        href = element.get_attribute("href")
                    else:
                        # Eğer element bir WebElement değilse atla
                        continue
                    
                    if not href:
                        continue
                    
                    # Sadece tvdiziler.tv linklerini al
                    if "tvdiziler.tv" not in href:
                        continue
                    
                    # Slug'ı çıkar
                    slug = extract_slug_from_href(href)
                    
                    if not slug:
                        continue
                    
                    # Zaten işlenmiş mi?
                    if slug in seen_slugs:
                        continue
                    
                    # Başlığı al
                    try:
                        # Önce h2, h3 veya .truncate class'ını dene
                        title_elem = element.find_element(By.CSS_SELECTOR, "h2, h3, .truncate, [itemprop='name']")
                        title = title_elem.text.strip()
                    except:
                        # Elementin kendi text'ini al
                        title = element.text.strip()
                    
                    if not title or len(title) < 2:
                        # Slug'dan başlık oluştur
                        title = slug.replace("-", " ").replace(" bolum", "").replace(" full izle", "").title()
                    
                    # Temizle
                    title = title.replace(" izle", "").replace(" HD", "").strip()
                    
                    # Worker linkini oluştur
                    worker_link = f"{WORKER_BASE_URL}{slug}&ext=m3u8"
                    
                    # Test için birkaç tanesini göster
                    if new_items_count < 5:
                        print(f"   Örnek: {title[:30]:30} -> {slug[:40]}")
                    
                    # Listeye ekle
                    playlist_data.append((title, worker_link))
                    seen_slugs.add(slug)
                    new_items_count += 1
                    
                    # Her 20 işlemde bir ilerleme göster
                    if new_items_count % 20 == 0:
                        print(f"   İşlenen: {new_items_count}")
                    
                except Exception as e:
                    if processed_count % 100 == 0:
                        # Çok fazla hata gösterme
                        continue
            
            print(f"\n✓ Sayfa {page_num}: {new_items_count} yeni bölüm eklendi")
            
            # Pagination kontrolü
            if new_items_count == 0 and page_num > 1:
                print("\n⚠ Yeni içerik bulunamadı. Tarama tamamlandı.")
                break
            
            # Sonraki sayfa için URL kontrolü
            next_page_exists = False
            try:
                # Sonraki sayfa linklerini ara
                next_buttons = driver.find_elements(By.XPATH, 
                    "//a[contains(text(), 'Sonraki') or contains(text(), 'İleri') or contains(text(), 'Next') or contains(@rel, 'next')]")
                
                for btn in next_buttons:
                    if btn.is_displayed():
                        next_page_exists = True
                        break
                
                # Sayfa numarası linklerini kontrol et
                page_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/dizi-izle/']")
                for link in page_links:
                    href = link.get_attribute("href")
                    if href and str(page_num + 1) in href:
                        next_page_exists = True
                        break
                        
            except:
                pass
            
            if not next_page_exists and page_num > 3:
                print("\n⚠ Son sayfaya ulaşıldı.")
                break
            
            page_num += 1
            time.sleep(2)  # Sunucuyu yormamak için bekle
            
            # Test için ilk 3 sayfayı tarasın
            if page_num > 3:
                print("\n⚠ Test için ilk 3 sayfa taranıyor. Devam etmek için kodu değiştirin.")
                break
            
    except Exception as e:
        print(f"\n✗ Hata: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n✓ Tarayıcı kapatıldı")
    
    return playlist_data

def save_m3u(data):
    if not data:
        print("\n✗ Liste boş olduğu için dosya oluşturulmadı.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            # Başlıktaki özel karakterleri temizle
            clean_title = title.replace(",", " -").replace('"', "'").replace(":", " -")
            f.write(f'#EXTINF:-1 group-title="TvDiziler", {clean_title}\n')
            f.write(f"{link}\n")
    
    print(f"\n{'='*60}")
    print(f"✓ İŞLEM TAMAMLANDI")
    print(f"{'='*60}")
    print(f"Toplam İçerik: {len(data)}")
    print(f"Çıktı Dosyası: {OUTPUT_FILE}")
    
    # Test için ilk 5 linki göster
    if data:
        print("\nİlk 5 bölüm:")
        print("-" * 60)
        for i, (title, link) in enumerate(data[:5], 1):
            print(f"{i:2}. {title}")
            print(f"    {link}")
        
        # Link testi yap
        print("\n✓ Test ediliyor...")
        import requests
        success_count = 0
        
        for title, link in data[:3]:  # İlk 3'ü test et
            try:
                response = requests.head(link, timeout=10)
                if response.status_code == 200:
                    print(f"   ✓ {title[:30]:30} ÇALIŞIYOR")
                    success_count += 1
                else:
                    print(f"   ✗ {title[:30]:30} HATA: {response.status_code}")
            except Exception as e:
                print(f"   ✗ {title[:30]:30} BAĞLANTI HATASI: {e}")
        
        print(f"\n✓ Test sonucu: {success_count}/3 başarılı")

def main():
    print("TV Dizileri Bölüm Scraper")
    print("="*60)
    print("NOT: Bu kod bölüm linklerini tarar (https://tvdiziler.tv/esref-ruya-29-bolum-full-izle)")
    print("Çıktı: https://tvdiziler.umittv.workers.dev/?id=esref-ruya-29-bolum-full-izle&ext=m3u8")
    print("="*60)
    
    # Örnek test
    print("\nÖrnek test:")
    test_urls = [
        "https://tvdiziler.tv/esref-ruya-29-bolum-full-izle",
        "https://tvdiziler.tv/kizilcik-serbeti-122-bolum-izle",
        "https://tvdiziler.tv/gonul-dagi-202-bolum-izle"
    ]
    
    for url in test_urls:
        slug = extract_slug_from_href(url)
        if slug:
            worker_link = f"{WORKER_BASE_URL}{slug}&ext=m3u8"
            print(f"✓ {url}")
            print(f"  -> {worker_link}")
        else:
            print(f"✗ Geçersiz: {url}")
    
    # Ana tarama
    all_data = scrape_all_pages()
    save_m3u(all_data)

if __name__ == "__main__":
    main()
