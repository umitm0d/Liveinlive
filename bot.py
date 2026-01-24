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
    
    # GitHub Actions için gerekli ayarlar
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Anti-bot koruma önlemleri
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # GitHub Actions için özel path
    chrome_options.binary_location = "/usr/bin/google-chrome"  # GitHub Actions'ta Chrome path'i
    
    try:
        print("ChromeDriver yükleniyor...")
        # ChromeDriverManager'ı sessiz modda çalıştır
        service = Service(ChromeDriverManager().install())
        
        print("Chrome başlatılıyor...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Anti-bot tespitini atlatmak için
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        print(f"Driver oluşturma hatası: {e}")
        raise

def extract_slug(full_url):
    """URL'den dizi slug'ını çıkarır"""
    if not full_url: 
        return None
    return full_url.rstrip('/').split('/')[-1]

def scrape_all_pages():
    driver = None
    playlist_data = []
    seen_slugs = set()
    
    try:
        driver = setup_driver()
        print(f"Tarama Başlatılıyor: {BASE_URL}")
        
        driver.get(BASE_URL)
        
        # Sayfanın yüklenmesini bekle
        time.sleep(8)  # GitHub Actions'ta daha uzun bekle
        
        # Sayfanın yüklendiğini kontrol et
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("✓ Sayfa başarıyla yüklendi")
        except:
            print("⚠ Sayfa tam yüklenemedi, devam ediliyor...")
        
        # Debug için sayfa kaynağını kontrol et
        page_source = driver.page_source[:500]
        print(f"Sayfa içeriği (ilk 500 karakter): {page_source}")
        
        # Alfabetik harfleri kontrol et
        if any(letter in page_source for letter in ["A</h", "B</h", "C</h"]):
            print("✓ Alfabetik dizi listesi tespit edildi")
        else:
            print("✗ Alfabetik dizi listesi bulunamadı")
        
        # TÜM dizi linklerini bul - basit ve etkili yöntem
        all_links = driver.find_elements(By.TAG_NAME, "a")
        print(f"Toplam {len(all_links)} adet link bulundu")
        
        # Dizi linklerini filtrele
        dizi_links = []
        for link in all_links:
            try:
                href = link.get_attribute("href")
                text = link.text.strip()
                
                if not href or not text:
                    continue
                    
                # Sadece /dizi/ içeren ve anlamlı metni olan linkleri al
                if "/dizi/" in href and len(text) > 2:
                    if text not in ["Giriş yap", "Kayıt ol", "Şifremi Unuttum", ""]:
                        dizi_links.append((href, text))
                        
            except:
                continue
        
        print(f"Filtrelenmiş dizi link sayısı: {len(dizi_links)}")
        
        # Linkleri işle
        for href, title in dizi_links:
            try:
                # Slug'ı çıkar
                slug = extract_slug(href)
                
                if not slug or slug in seen_slugs:
                    continue
                
                # Geçersiz slug'ları filtrele
                if any(x in slug for x in ["kesfet", "takvim", "film-izle", "profile"]):
                    continue
                
                # Başlık temizleme
                clean_title = title.strip()
                if not clean_title:
                    clean_title = slug.replace("-", " ").title()
                
                # Worker linkini oluştur
                worker_link = f"{WORKER_BASE_URL}{slug}&ext=m3u8"
                
                # Listeye ekle
                playlist_data.append((clean_title, worker_link))
                seen_slugs.add(slug)
                
                # Her 20 dizi için ilerleme göster
                if len(seen_slugs) % 20 == 0:
                    print(f"  İşlenen dizi sayısı: {len(seen_slugs)}")
                    
            except Exception as e:
                print(f"  Hata ({href[:50]}): {str(e)[:50]}")
                continue
        
        print(f"\n✓ Başarıyla işlenen dizi sayısı: {len(playlist_data)}")
        
        # Eğer hiç dizi bulunamazsa, alternatif CSS seçicileri dene
        if len(playlist_data) == 0:
            print("\nAlternatif tarama yöntemleri deneniyor...")
            
            # CSS seçicileri ile dizi kartlarını ara
            selectors_to_try = [
                "a[href*='/dizi/']",
                ".poster-xs a",
                "ul.little-series a",
                "div.poster-media a",
                "li a[href*='/dizi/']"
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"  {selector}: {len(elements)} element bulundu")
                    
                    for elem in elements[:20]:  # İlk 20'yi kontrol et
                        try:
                            href = elem.get_attribute("href")
                            text = elem.text.strip()
                            
                            if href and text and "/dizi/" in href:
                                print(f"    Örnek: {text[:30]} -> {href[:50]}")
                        except:
                            continue
                            
                except:
                    continue
        
    except Exception as e:
        print(f"\n✗ Ana hata: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()
            print("✓ Tarayıcı kapatıldı")
    
    return playlist_data

def save_m3u(data):
    if not data:
        print("\n✗ Liste boş olduğu için dosya oluşturulmadı.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            # Başlıktaki virgülleri temizle
            clean_title = title.replace(",", " -").replace('"', "'")
            f.write(f'#EXTINF:-1 group-title="TvDiziler-Tum", {clean_title}\n')
            f.write(f"{link}\n")
    
    print(f"\n{'='*60}")
    print(f"✓ İŞLEM TAMAMLANDI")
    print(f"{'='*60}")
    print(f"Toplam İçerik: {len(data)}")
    print(f"Çıktı Dosyası: {OUTPUT_FILE}")
    
    # Örnek içerikleri göster
    if len(data) > 0:
        print(f"\nİlk 5 Dizi:")
        for i, (title, link) in enumerate(data[:5], 1):
            print(f"  {i}. {title}")
        
        print(f"\nSon 5 Dizi:")
        for i, (title, link) in enumerate(data[-5:], len(data)-4):
            print(f"  {i}. {title}")

if __name__ == "__main__":
    print("="*60)
    print("TV Dizileri IPTV Playlist Oluşturucu - GitHub Actions")
    print("="*60)
    
    all_data = scrape_all_pages()
    save_m3u(all_data)
    
    # GitHub Actions için çıktı
    if all_data:
        print(f"\n✓ SUCCESS: {len(all_data)} dizi bulundu")
    else:
        print(f"\n✗ WARNING: Hiç dizi bulunamadı")
