import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# --- AYARLAR ---
BASE_DOMAIN = "https://vidsrc-embed.ru"

CONTENT_LIST = [
    {
        "id": "tt0944947", 
        "name": "Game of Thrones", 
        "type": "tv", 
        "image": "https://image.tmdb.org/t/p/w500/1XS1oqL89opfnbGw83TrgnpKoAT.jpg",
        "seasons": [{"season_num": 1, "episode_count": 1}] 
    },
    {
        "id": "tt5433140", 
        "name": "Hızlı ve Öfkeli 10", 
        "type": "movie",
        "image": "https://image.tmdb.org/t/p/w500/fiVW06jE7z9YnO4trhaMEdclSiC.jpg"
    }
]

def get_m3u8_via_selenium(url):
    """
    Sayfayı gerçek tarayıcıda açar ve ağ trafiğinden m3u8 linkini yakalar.
    """
    print(f"--> Tarayıcı açılıyor: {url}")
    
    # Ağ trafiğini (Performance Logs) izlemek için ayarlar
    capabilities = DesiredCapabilities.CHROME
    capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

    chrome_options = Options()
    chrome_options.add_argument("--headless") # Arayüzsüz mod
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options, desired_capabilities=capabilities)
    
    m3u8_link = None
    
    try:
        driver.get(url)
        time.sleep(5) # Sayfanın ve player'ın yüklenmesi için bekle
        
        # Tarayıcının ağ (network) kayıtlarını çek
        logs = driver.get_log("performance")

        for entry in logs:
            message = json.loads(entry["message"])["message"]
            if "Network.requestWillBeSent" in message["method"]:
                request_url = message["params"]["request"]["url"]
                
                # Link .m3u8 içeriyor mu kontrol et
                if ".m3u8" in request_url:
                    m3u8_link = request_url
                    break # İlk bulunanı al ve çık
                    
    except Exception as e:
        print(f"Hata: {e}")
    finally:
        driver.quit()
        
    return m3u8_link

def main():
    playlist_data = []
    m3u_content = "#EXTM3U\n"

    for item in CONTENT_LIST:
        targets = []
        if item["type"] == "movie":
            targets.append({"url": f"{BASE_DOMAIN}/embed/movie/{item['id']}", "title": item["name"], "group": "Filmler"})
        elif item["type"] == "tv":
            for season in item["seasons"]:
                for ep in range(1, season["episode_count"] + 1):
                    ep_title = f"{item['name']} S{season['season_num']:02d}E{ep:02d}"
                    targets.append({
                        "url": f"{BASE_DOMAIN}/embed/tv/{item['id']}/{season['season_num']}/{ep}",
                        "title": ep_title,
                        "group": item["name"]
                    })

        for target in targets:
            video_url = get_m3u8_via_selenium(target["url"])
            
            if video_url:
                print(f"✅ BULUNDU: {target['title']}")
                
                playlist_data.append({
                    "name": target["title"],
                    "url": video_url,
                    "image": item["image"],
                    "group": target["group"]
                })
                
                m3u_content += f'#EXTINF:-1 group-title="{target["group"]}" tvg-logo="{item["image"]}",{target["title"]}\n{video_url}\n'
            else:
                print(f"❌ BULUNAMADI (JS Yüklenmedi veya Link Yok): {target['title']}")

    # Dosyaları Kaydet
    with open("playlist.json", "w", encoding="utf-8") as f:
        json.dump(playlist_data, f, ensure_ascii=False, indent=4)
        
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)

    print("\n🎉 İşlem Tamamlandı!")

if __name__ == "__main__":
    main()
