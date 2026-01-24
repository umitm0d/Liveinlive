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
    # Hata ayıklama için headless'i kapatın, çalıştığında tekrar açabilirsiniz
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    # Anti-bot koruma önlemleri
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def extract_slug(full_url):
    """URL'den dizi slug'ını çıkarır"""
    if not full_url: 
        return None
    return full_url.rstrip('/').split('/')[-1]

def scrape_all_pages():
    driver = setup_driver()
    playlist_data = []
    seen_slugs = set()
    
    try:
        print(f"Tarama Başlatılıyor: {BASE_URL}")
        driver.get(BASE_URL)
        
        # Sayfanın tam yüklenmesini bekle (alfabetik listeler için)
        time.sleep(5)
        
        # Sayfanın yüklendiğini kontrol et
        page_title = driver.title
        print(f"Sayfa Başlığı: {page_title}")
        
        # Sayfanın HTML içeriğini kontrol et (debug için)
        page_source = driver.page_source
        if "A" in page_source and "B" in page_source:  # Alfabetik bölümler var mı?
            print("✓ Alfabetik dizi listesi tespit edildi")
        else:
            print("✗ Alfabetik dizi listesi bulunamadı!")
            print("İlk 1000 karakter:", page_source[:1000])
        
        # 1. YÖNTEM: Tüm dizi linklerini topla
        all_dizi_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/dizi/"]')
        print(f"\nToplam {len(all_dizi_links)} adet '/dizi/' içeren link bulundu")
        
        # Filtrelenmiş linkler
        filtered_links = []
        unwanted_texts = ["Giriş yap", "Kayıt ol", "Şifremi Unuttum", "Gönder", ""]
        
        for link in all_dizi_links:
            try:
                href = link.get_attribute('href')
                text = link.text.strip()
                
                # İstenmeyen linkleri filtrele
                if not text or text in unwanted_texts:
                    continue
                    
                # Geçersiz href kontrolü
                if not href or "javascript:void" in href:
                    continue
                    
                filtered_links.append((href, text))
                
            except:
                continue
        
        print(f"Filtrelenmiş dizi link sayısı: {len(filtered_links)}")
        
        # 2. YÖNTEM: Alfabetik bölümlerdeki linkleri ara
        # Her harf bölümündeki linkleri ayrı ayrı bul
        alphabet_sections = driver.find_elements(By.XPATH, '//div[contains(@class, "flex") or contains(@class, "section")]')
        
        if alphabet_sections:
            print(f"Alfabetik bölüm sayısı: {len(alphabet_sections)}")
        
        # Her iki yöntemden gelen linkleri işle
        all_links_set = set(filtered_links)  # Tekilleştirme
        
        print(f"\nToplam {len(all_links_set)} benzersiz dizi linki işlenecek")
        
        # Linkleri işle
        processed_count = 0
        for href, title in all_links_set:
            try:
                # Slug'ı çıkar
                slug = extract_slug(href)
                
                if not slug:
                    continue
                    
                # Zaten işlenmiş mi kontrol et
                if slug in seen_slugs:
                    continue
                
                # Geçersiz slug'ları filtrele
                if any(x in slug for x in ["kesfet", "takvim", "film-izle", "profile", "oyuncu"]):
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
                processed_count += 1
                
                # İlerleme durumu
                if processed_count % 20 == 0:
                    print(f"  İşlenen: {processed_count}/{len(all_links_set)} - {clean_title}")
                    
            except Exception as e:
                print(f"  Hata ({href}): {str(e)[:50]}")
                continue
        
        print(f"\nBaşarıyla işlenen dizi sayısı: {processed_count}")
        
        # Eğer hiç dizi bulunamazsa, alternatif yöntem dene
        if processed_count == 0:
            print("\nAlternatif tarama yöntemi deneniyor...")
            
            # Tüm linkleri göster (debug için)
            print("\nTüm bulunan linkler:")
            for i, (href, text) in enumerate(filtered_links[:50], 1):
                print(f"{i:3}. {text[:40]:40} -> {href}")
            
            # Basit yöntem: tüm <a> tag'larını kontrol et
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    
                    if href and "/dizi/" in href and text and len(text) > 2:
                        slug = extract_slug(href)
                        if slug and slug not in seen_slugs:
                            worker_link = f"{WORKER_BASE_URL}{slug}&ext=m3u8"
                            playlist_data.append((text, worker_link))
                            seen_slugs.add(slug)
                            
                except:
                    continue
            
            print(f"Alternatif yöntemle bulunan: {len(playlist_data)}")
    
    except Exception as e:
        print(f"\n✗ Hata Oluştu: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("\nTarayıcı kapatıldı")
    
    return playlist_data

def save_m3u(data):
    if not data:
        print("\n✗ Liste boş olduğu için dosya oluşturulmadı.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            # Başlıktaki virgülleri temizle (M3U formatı için önemli)
            clean_title = title.replace(",", " -").replace('"', "'")
            f.write(f'#EXTINF:-1 group-title="TvDiziler-Tum", {clean_title}\n')
            f.write(f"{link}\n")
    
    print(f"\n{'='*50}")
    print(f"✓ İŞLEM TAMAMLANDI")
    print(f"{'='*50}")
    print(f"Toplam İçerik: {len(data)}")
    print(f"Çıktı Dosyası: {OUTPUT_FILE}")
    
    # Örnek içerikleri göster
    if len(data) > 0:
        print(f"\nİlk 10 Dizi:")
        for i, (title, link) in enumerate(data[:10], 1):
            print(f"{i:2}. {title[:50]}")
        
        print(f"\nSon 5 Dizi:")
        for i, (title, link) in enumerate(data[-5:], len(data)-4):
            print(f"{i:2}. {title[:50]}")

if __name__ == "__main__":
    print("="*50)
    print("TV Dizileri IPTV Playlist Oluşturucu")
    print("="*50)
    
    all_data = scrape_all_pages()
    save_m3u(all_data)
    
    # Ek bilgi
    if all_data:
        print(f"\n✓ Playlist başarıyla oluşturuldu!")
        print(f"✓ {OUTPUT_FILE} dosyasını IPTV oynatıcınızda kullanabilirsiniz.")
    else:
        print(f"\n✗ Hiç veri toplanamadı.")
        print("✗ Lütfen:")
        print("  1. İnternet bağlantınızı kontrol edin")
        print("  2. Siteye erişiminizi kontrol edin")
        print("  3. CSS seçicilerinin güncel olduğundan emin olun")
