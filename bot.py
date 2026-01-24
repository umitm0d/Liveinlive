import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ================== AYARLAR ==================
BASE_URL = "https://tvdiziler.tv/dizi-izle"
WORKER_BASE_URL = "https://tvdiziler.umittv.workers.dev/?id="
OUTPUT_FILE = "iptv_list.m3u"

# ================== DRIVER ==================
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver

# ================== BÖLÜM SLUG BUL ==================
def get_episode_slug(driver, dizi_url):
    driver.get(dizi_url)
    time.sleep(4)

    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='-bolum-full-izle']")
    for link in links:
        href = link.get_attribute("href")
        if href:
            return href.rstrip("/").split("/")[-1]

    return None

# ================== SCRAPER ==================
def scrape():
    driver = setup_driver()
    playlist = []
    seen = set()

    print("Dizi listesi açılıyor...")
    driver.get(BASE_URL)
    time.sleep(6)

    dizi_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/dizi/']")
    print(f"Bulunan dizi linki: {len(dizi_links)}")

    for a in dizi_links:
        try:
            dizi_url = a.get_attribute("href")
            title = a.text.strip()

            if not dizi_url or not title or dizi_url in seen:
                continue

            seen.add(dizi_url)
            print(f"\n→ {title}")

            episode_slug = get_episode_slug(driver, dizi_url)

            if not episode_slug:
                print("   ✗ Bölüm bulunamadı")
                continue

            worker_link = f"{WORKER_BASE_URL}{episode_slug}&ext=m3u8"
            playlist.append((title, worker_link))

            print(f"   ✓ {worker_link}")

        except Exception as e:
            print("   Hata:", e)

    driver.quit()
    return playlist

# ================== M3U KAYDET ==================
def save_m3u(data):
    if not data:
        print("\nListe boş.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            title = title.replace(",", " -").replace('"', "'")
            f.write(f'#EXTINF:-1 group-title="TvDiziler", {title}\n')
            f.write(f"{link}\n")

    print(f"\n✓ M3U oluşturuldu: {OUTPUT_FILE}")
    print(f"Toplam içerik: {len(data)}")

# ================== MAIN ==================
if __name__ == "__main__":
    print("TvDiziler → IPTV Worker BOT")
    print("=" * 45)

    data = scrape()
    save_m3u(data)
