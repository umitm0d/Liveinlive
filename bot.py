import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://tvdiziler.tv/diziler"
WORKER = "https://tvdiziler.umittv.workers.dev/?id="
OUT = "iptv_list.m3u"

def driver_setup():
    opt = Options()
    opt.add_argument("--headless")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--window-size=1920,1080")
    opt.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
    opt.add_experimental_option("excludeSwitches", ["enable-automation"])
    opt.add_experimental_option("useAutomationExtension", False)

    drv = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opt
    )
    drv.execute_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    )
    return drv

def scroll_all(driver):
    last = 0
    while True:
        height = driver.execute_script("return document.body.scrollHeight")
        if height == last:
            break
        last = height
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)

def get_episode_slug(driver, dizi_url):
    driver.get(dizi_url)
    time.sleep(4)
    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='-bolum-full-izle']")
    if links:
        return links[0].get_attribute("href").split("/")[-1]
    return None

def run():
    d = driver_setup()
    print("Dizi listesi çekiliyor...")
    d.get(BASE_URL)
    time.sleep(5)

    scroll_all(d)

    cards = d.find_elements(By.CSS_SELECTOR, "a[href*='/dizi/']")
    print("Bulunan dizi:", len(cards))

    data = []
    seen = set()

    for c in cards:
        href = c.get_attribute("href")
        title = c.text.strip()
        if not href or not title or href in seen:
            continue
        seen.add(href)

        print("→", title)
        slug = get_episode_slug(d, href)
        if not slug:
            print("   ✗ bölüm yok")
            continue

        data.append((title, f"{WORKER}{slug}&ext=m3u8"))
        print("   ✓ OK")

    d.quit()
    return data

def save(lst):
    if not lst:
        print("Liste boş.")
        return
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for t, l in lst:
            f.write(f'#EXTINF:-1,{t}\n{l}\n')
    print("✓ M3U hazır:", OUT)

if __name__ == "__main__":
    print("TvDiziler → IPTV Worker BOT")
    print("=" * 45)
    res = run()
    save(res)
