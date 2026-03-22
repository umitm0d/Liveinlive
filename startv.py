import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
import re
import time

base_url = "https://www.startv.com.tr"
img_base_url = "https://media.startv.com.tr/star-tv"
dizi_url = "https://www.startv.com.tr/dizi"
m3u_file = "startv.m3u"
pattern = r'"apiUrl\\":\\"(.*?)\\"'

api_params = {
    "sort": "episodeNo asc",
    "limit": "100"
}

def get_items_page(url):
    """Ana sayfadan tüm dizi linklerini al"""
    item_list = []
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    links = soup.find_all("a", href=re.compile(r'^/dizi/'))
    seen = set()
    for a in links:
        href = a.get("href")
        if href and href not in seen:
            seen.add(href)
            item_url = base_url + href
            slug = href.split("/")[-1]
            name = slug.replace("-", "").strip()  # boşlukları temizle
            item_list.append({
                "name": name,
                "img": "",  # Daha sonra API’den ekle
                "url": item_url
            })
    return item_list

def get_item_api_url(url):
    """Dizi sayfasından apiUrl al"""
    api_path = ""
    r = requests.get(url + "/bolumler")
    results = re.findall(pattern, r.text)
    if results:
        api_path = results[0]
    return api_path

def get_item_api(path):
    """API’den bölümleri çek"""
    item_list = []
    params = api_params.copy()
    flag = True
    skip = 0
    url = base_url + path
    while flag:
        params["skip"] = skip
        try:
            r = requests.get(url, params=params)
            data = r.json()
            items = data.get("items", [])
            for item in items:
                # '-' yerine boşluk koy
                name = f'{item["heading"]} {item["title"]}'
                name = name.replace("-", " ").replace("  ", " ").strip()
                img = img_base_url + item["image"]["fullPath"] if item.get("image") else ""
                stream_url = ""
                if "video" in item:
                    stream_url = f'https://dygvideo.dygdigital.com/api/redirect?PublisherId=1&ReferenceId=StarTV_{item["video"]["referenceId"]}&SecretKey=NtvApiSecret2014*&.m3u8'
                if stream_url:
                    item_list.append({
                        "name": name,
                        "img": img,
                        "stream_url": stream_url
                    })
            if len(items) < 100:
                flag = False
            else:
                skip += 100
        except:
            flag = False
    return item_list

def main(start=0, end=0):
    data = []
    series_list = get_items_page(dizi_url)
    if end == 0:
        end_index = len(series_list)
    else:
        end_index = end

    for i in tqdm(range(start, end_index)):
        serie = series_list[i]
        print(i+1, serie["name"])
        api_path = get_item_api_url(serie["url"])
        if not api_path:
            continue
        episodes = get_item_api(api_path)
        temp_serie = serie.copy()
        temp_serie["episodes"] = episodes
        data.append(temp_serie)

    # M3U oluştur
    with open(m3u_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for serie in data:
            for ep in serie["episodes"]:
                line = f'#EXTINF:-1 tvg-id="vod.tr" tvg-name="TR: {ep["name"]}" tvg-logo="{ep["img"]}" group-title="STARTV Dizileri",TR: {ep["name"]}\n{ep["stream_url"]}\n'
                f.write(line)

    print(f"{m3u_file} başarıyla oluşturuldu!")

if __name__ == "__main__":
    main()
