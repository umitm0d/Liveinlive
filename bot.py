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

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver

# ================== HELPERS ==================
def extract_slug(url):
    if not url:
        return None
    return url.rstrip("/").split("/")[-1]

def get_last_episode_slug(driver, dizi_url):
    driver.get(dizi_url)
    time.sleep(5)

    episode_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='bolum']")
    for link in episode_links:
        href = link.get_attribute("href")
        if href and "full-izle" in href:
            return extract_slug(href)

    return None

# ================== SCRAPER ==================
def scrape():
    driver = setup_driver()
    playlist = []
    seen = set()

    print("Dizi listesi açılıyor...")
    driver.get(BASE_URL)
    time.sleep(8)

    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/dizi/']")
    print(f"Bulunan dizi linki: {len(links)}")

    for a in links:
        try:
            dizi_url = a.get_attribute("href")
            title = a.text.strip()

            if not dizi_url or not title or dizi_url in seen:
                continue

            seen.add(dizi_url)

            print(f"→ {title}")
            episode_slug = get_last_episode_slug(driver, dizi_url)

            if not episode_slug:
                print("   ✗ Bölüm bulunamadı")
                continue

            worker_link = f"{WORKER_BASE_URL}{episode_slug}&ext=m3u8"
            playlist.append((title, worker_link))

            print(f"   ✓ {worker_link}")

        except Exception as e:
            print("   Hata:", e)
            continue

    driver.quit()
    return playlist

# ================== SAVE ==================
def save_m3u(data):
    if not data:
        print("Liste boş.")
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
    print("TvDiziler → IPTV Worker Test")
    print("=" * 40)

    data = scrape()
    save_m3u(data)
