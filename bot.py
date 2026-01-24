import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse

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

def clean_dizi_slug(url):
    """URL'den temiz dizi slug'ını çıkarır: dizi-adi-izle formatında"""
    if not url or "/dizi/" not in url:
        return None
    
    # URL'yi parçala
    parsed = urlparse(url)
    path = parsed.path
    
    # /dizi/ kısmından sonrasını al
    if "/dizi/" in path:
        slug = path.split("/dizi/")[-1].rstrip('/')
    else:
        slug = path.lstrip('/').rstrip('/')
    
    # Eğer slug bölüm içeriyorsa (29-bolum gibi), sadece dizi adını al
    # Örnek: esref-ruya-29-bolum-full-izle -> esref-ruya-izle
    # Örnek: esref-ruya-son-bolum-izle-68 -> esref-ruya-izle
    
    # Bölüm numaralarını ve "son-bolum" ifadesini temizle
    slug = re.sub(r'-\d+-bolum-', '-izle-', slug)
    slug = re.sub(r'-son-bolum-', '-izle-', slug)
    slug = re.sub(r'-\d+$', '', slug)  # Sondaki sayıları kaldır
    
    # "izle" ekini kontrol et ve düzelt
    if not slug.endswith('-izle'):
        # "full-izle" varsa düzelt
        if '-full-izle' in slug:
            slug = slug.replace('-full-izle', '-izle')
        elif '-izle-' in slug:
            # Örnek: esref-ruya-izle-68 -> esref-ruya-izle
            slug = slug.split('-izle-')[0] + '-izle'
        else:
            slug = slug + '-izle'
    
    # "-hd" ekini kaldır
    slug = slug.replace('-hd', '')
    
    return slug

def get_correct_slug_from_dizi_page(driver, dizi_url):
    """Dizi sayfasına gidip doğru slug'ı bul"""
    try:
        driver.get(dizi_url)
        time.sleep(3)
        
        # İlk bölüm linkini bul
        episode_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/dizi/']")
        
        for link in episode_links[:5]:  # İlk 5 linki kontrol et
            href = link.get_attribute("href")
            if href and "bolum" in href and "izle" in href:
                # Bölüm linkinden temiz dizi slug'ını çıkar
                clean_slug = clean_dizi_slug(href)
                if clean_slug:
                    return clean_slug
                    
    except Exception as e:
        print(f"  Dizi sayfası hatası: {e}")
    
    return None

def scrape_all_pages():
    driver = setup_driver()
    playlist_data = []
    seen_slugs = set()
    
    try:
        print(f"Tarama Başlatılıyor: {BASE_URL}")
        driver.get(BASE_URL)
        
        # Sayfanın yüklenmesini bekle
        time.sleep(8)
        
        # Alfabetik dizi linklerini bul - DİKKAT: Bu sayfada dizi listesi var, bölümler değil!
        all_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/dizi/"]')
        print(f"Bulunan dizi linkleri: {len(all_links)}")
        
        # Linkleri filtrele ve işle
        for i, link in enumerate(all_links):
            try:
                href = link.get_attribute("href")
                text = link.text.strip()
                
                # Filtreleme
                if not href or not text or text in ["Giriş yap", "Kayıt ol", ""]:
                    continue
                
                # Sadece ana dizi sayfalarını al (bölüm sayfalarını değil)
                # Dizi sayfası: /dizi/esref-ruya-izle
                # Bölüm sayfası: /dizi/esref-ruya-29-bolum-full-izle
                
                # Eğer link bölüm içermiyorsa (bolum kelimesi yoksa), bu bir dizi ana sayfasıdır
                if "bolum" not in href.lower():
                    # Temiz slug oluştur
                    clean_slug = clean_dizi_slug(href)
                    
                    if not clean_slug or clean_slug in seen_slugs:
                        continue
                    
                    # Başlığı temizle
                    clean_title = text.replace(" izle", "").replace(" HD", "").strip()
                    
                    # Worker linkini oluştur
                    worker_link = f"{WORKER_BASE_URL}{clean_slug}&ext=m3u8"
                    
                    # Test et
                    test_url = worker_link
                    print(f"{i+1:3}. {clean_title[:30]:30} -> {clean_slug}")
                    
                    playlist_data.append((clean_title, worker_link))
                    seen_slugs.add(clean_slug)
                    
            except Exception as e:
                print(f"  Link hatası: {e}")
                continue
        
        print(f"\n✓ Toplam {len(playlist_data)} dizi bulundu")
        
        # Eğer az sayıda dizi bulunduysa, alternatif yöntem dene
        if len(playlist_data) < 50:
            print("\nAlternatif yöntem deneniyor...")
            
            # Ana sayfadaki son bölümlerden dizi isimlerini al
            episode_sections = driver.find_elements(By.CSS_SELECTOR, ".poster-xs, .poster-media")
            
            for section in episode_sections[:50]:  # İlk 50'yi kontrol et
                try:
                    link = section.find_element(By.TAG_NAME, "a")
                    href = link.get_attribute("href")
                    
                    if href and "/dizi/" in href and "bolum" in href:
                        # Bölüm linkinden dizi slug'ını çıkar
                        clean_slug = clean_dizi_slug(href)
                        
                        if clean_slug and clean_slug not in seen_slugs:
                            # Başlığı bul
                            try:
                                title_elem = section.find_element(By.CSS_SELECTOR, "h2, h3, .truncate")
                                title = title_elem.text.strip()
                            except:
                                title = clean_slug.replace("-", " ").replace(" izle", "").title()
                            
                            clean_title = title.replace(" HD", "").replace(" izle", "").strip()
                            worker_link = f"{WORKER_BASE_URL}{clean_slug}&ext=m3u8"
                            
                            playlist_data.append((clean_title, worker_link))
                            seen_slugs.add(clean_slug)
                            
                            print(f"  + {clean_title[:30]} -> {clean_slug}")
                            
                except:
                    continue
        
    except Exception as e:
        print(f"\n✗ Hata: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
    
    return playlist_data

def save_m3u(data):
    if not data:
        print("\n✗ Liste boş!")
        return
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            clean_title = title.replace(",", " -").replace('"', "'")
            f.write(f'#EXTINF:-1 group-title="TvDiziler", {clean_title}\n')
            f.write(f"{link}\n")
    
    print(f"\n{'='*60}")
    print(f"✓ TAMAMLANDI: {len(data)} dizi")
    print(f"✓ Dosya: {OUTPUT_FILE}")
    print(f"{'='*60}")
    
    # Test için birkaç link göster
    if data:
        print("\nTest linkleri:")
        for i, (title, link) in enumerate(data[:5], 1):
            print(f"{i}. {title}")
            print(f"   {link}")
        
        # Linkleri test et
        print("\nLink testleri:")
        import requests
        for title, link in data[:3]:
            try:
                response = requests.head(link, timeout=5)
                status = "✓ Çalışıyor" if response.status_code == 200 else f"✗ Hata: {response.status_code}"
                print(f"  {title[:20]:20} {status}")
            except:
                print(f"  {title[:20]:20} ✗ Bağlantı hatası")

def main():
    print("TV Dizileri IPTV Scraper")
    print("="*60)
    
    # Örnek test
    test_urls = [
        "https://tvdiziler.tv/dizi/esref-ruya-29-bolum-full-izle",
        "https://tvdiziler.tv/dizi/esref-ruya-son-bolum-izle-68",
        "https://tvdiziler.tv/dizi/esref-ruya-izle"
    ]
    
    print("Slug temizleme testi:")
    for url in test_urls:
        slug = clean_dizi_slug(url)
        worker_link = f"{WORKER_BASE_URL}{slug}&ext=m3u8" if slug else "Geçersiz"
        print(f"  {url}")
        print(f"  -> {slug}")
        print(f"  -> {worker_link}\n")
    
    # Ana tarama
    all_data = scrape_all_pages()
    save_m3u(all_data)

if __name__ == "__main__":
    main()
