import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://tvdiziler.tv/dizi-izle"
WORKER_BASE_URL = "https://tvdiziler.umittv.workers.dev/?id="
OUTPUT_FILE = "iptv_list.m3u"

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

def extract_slug(url):
    if not url:
        return None
    return url.rstrip("/").split("/")[-1]

def get_last_episode_slug(driver, dizi_url):
    driver.get(dizi_url)
    time.sleep(5)

    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='bolum']")
    for a in links:
        href = a.get_attribute("href")
        if href and "full-izle" in href:
            return extract_slug(href)

    return None

def scrape():
    driver = setup_driver()
    playlist = []
    seen = set()

    print("Dizi listesi açılıyor...")
    driver.get(BASE_URL)
    time.sleep(10)

    # 🔥 TEXT’E BAKMADAN SADECE HREF
    dizi_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/dizi/']")
    print(f"Bulunan dizi linki: {len(dizi_links)}")

    for a in dizi_links:
        try:
            dizi_url = a.get_attribute("href")
            if not dizi_url or dizi_url in seen:
                continue

            seen.add(dizi_url)

            dizi_slug = extract_slug(dizi_url)
            title = dizi_slug.replace("-", " ").title()

            print(f"→ {title}")

            episode_slug = get_last_episode_slug(driver, dizi_url)
            if not episode_slug:
                print("   ✗ Bölüm yok")
                continue

            worker = f"{WORKER_BASE_URL}{episode_slug}&ext=m3u8"
            playlist.append((title, worker))

            print(f"   ✓ OK")

        except Exception as e:
            print("   HATA:", e)

    driver.quit()
    return playlist

def save_m3u(data):
    if not data:
        print("Liste boş.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in data:
            f.write(f'#EXTINF:-1 group-title="TvDiziler", {title}\n')
            f.write(link + "\n")

    print(f"\n✓ M3U oluşturuldu: {OUTPUT_FILE}")
    print(f"Toplam içerik: {len(data)}")

if __name__ == "__main__":
    print("TvDiziler → IPTV Worker Test")
    print("=" * 40)
    data = scrape()
    save_m3u(data)
