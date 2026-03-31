import requests
import re
import urllib3
import warnings
import os
import concurrent.futures

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

OUTPUT_FILENAME = "Ümitm0d.m3u"
STATIC_LOGO = "https://i.hizliresim.com/6d22jbw.gif"

def get_andro_content():
    print("--- Andro Panel ---")
    results = []
    base_pattern = "https://mahsunsports{}.xyz"
    headers = HEADERS.copy()

    channels = [
        ("androstreamlivebiraz1", 'TR:beIN Sport 1 HD'),
        ("androstreamlivebs1", 'TR:beIN Sport 1 HD'),
        ("androstreamlivebs2", 'TR:beIN Sport 2 HD'),
        ("androstreamlivebs3", 'TR:beIN Sport 3 HD'),
        ("androstreamlivebs4", 'TR:beIN Sport 4 HD'),
        ("androstreamlivebs5", 'TR:beIN Sport 5 HD'),
        ("androstreamlivebsm1", 'TR:beIN Sport Max 1 HD'),
        ("androstreamlivebsm2", 'TR:beIN Sport Max 2 HD'),
        ("androstreamlivess1", 'TR:S Sport 1 HD'),
        ("androstreamlivess2", 'TR:S Sport 2 HD'),
        ("androstreamlivets", 'TR:Tivibu Sport HD'),
        ("androstreamlivets1", 'TR:Tivibu Sport 1 HD'),
        ("androstreamlivets2", 'TR:Tivibu Sport 2 HD'),
        ("androstreamlivets3", 'TR:Tivibu Sport 3 HD'),
        ("androstreamlivets4", 'TR:Tivibu Sport 4 HD'),
        ("androstreamlivesm1", 'TR:Smart Sport 1 HD'),
        ("androstreamlivesm2", 'TR:Smart Sport 2 HD'),
        ("androstreamlivees1", 'TR:Euro Sport 1 HD'),
        ("androstreamlivees2", 'TR:Euro Sport 2 HD'),
        ("androstreamliveexn", 'TR:Exxen HD'),
        ("androstreamliveexn1", 'TR:Exxen 1 HD'),
        ("androstreamliveexn2", 'TR:Exxen 2 HD'),
        ("androstreamliveexn3", 'TR:Exxen 3 HD'),
        ("androstreamliveexn4", 'TR:Exxen 4 HD'),
        ("androstreamliveexn5", 'TR:Exxen 5 HD'),
        ("androstreamliveexn6", 'TR:Exxen 6 HD'),
        ("androstreamliveexn7", 'TR:Exxen 7 HD'),
        ("androstreamliveexn8", 'TR:Exxen 8 HD'),
        ("androstreamlivelivetb", 'TR:Tabii HD'),
        ("androstreamlivetb1", 'TR:Tabii 1 HD'),
        ("androstreamlivetb2", 'TR:Tabii 2 HD'),
        ("androstreamlivetb3", 'TR:Tabii 3 HD'),
        ("androstreamlivetb4", 'TR:Tabii 4 HD'),
        ("androstreamlivetb5", 'TR:Tabii 5 HD'),
        ("androstreamlivetb6", 'TR:Tabii 6 HD'),
        ("androstreamlivetb7", 'TR:Tabii 7 HD'),
        ("androstreamlivetb8", 'TR:Tabii 8 HD'),
    ]

    def check_domain(index):
        url = base_pattern.format(index)
        try:
            response = requests.get(url, headers=headers, timeout=5, verify=False)
            if response.status_code == 200:
                return url
        except:
            return None
        return None

    print("Andro Panel icin aktif domain araniyor (10-99)...")
    active_site = None
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(check_domain, i) for i in range(10, 100)]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                active_site = result
                executor.shutdown(wait=False, cancel_futures=True)
                break

    if not active_site:
        print("Andro Panel: 10 ile 99 arasinda aktif site bulunamadi.")
        return results

    print(f"Andro Panel Guncel Domain Bulundu: {active_site}")
    event_url = f"{active_site}/event.html?id=androstreamlivebs1"
    print(f"Event sayfasi kontrol ediliyor: {event_url}")

    try:
        r2 = requests.get(event_url, headers=headers, verify=False, timeout=10)
        h2_text = r2.text
    except Exception as e:
        print(f"Andro Panel: Event sayfasi alinamadi. Hata: {e}")
        return results

    baseurl_match = re.search(r'baseurls\s*=\s*\[(.*?)\]', h2_text, re.DOTALL | re.IGNORECASE)
    if not baseurl_match:
        print("Andro Panel: baseurls dizisi event sayfasinda bulunamadi.")
        return results

    urls_text = baseurl_match.group(1).replace('"', '').replace("'", "").replace("\n", "").replace("\r", "")
    servers = [url.strip() for url in urls_text.split(',') if url.strip().startswith("http")]
    servers = list(set(servers))
    print(f"Bulunan Sunucular: {servers}")

    active_servers = []
    test_id = "androstreamlivebs1"
    for server in servers:
        server = server.rstrip('/')
        test_url = f"{server}/{test_id}.m3u8" if "checklist" in server else f"{server}/checklist/{test_id}.m3u8"
        test_url = test_url.replace("checklist//", "checklist/")
        try:
            temp_response = requests.get(test_url, headers={'Referer': active_site + "/"}, verify=False, timeout=5)
            if temp_response.status_code == 200:
                active_servers.append(server)
        except:
            continue

    for server in active_servers:
        server = server.rstrip('/')
        for cid, cname in channels:
            final_url = f"{server}/{cid}.m3u8" if "checklist" in server else f"{server}/checklist/{cid}.m3u8"
            final_url = final_url.replace("checklist//", "checklist/")
            entry = f'#EXTINF:-1 tvg-logo="{STATIC_LOGO}" group-title="ümitm0d", {cname}\n#EXTVLCOPT:http-referrer={active_site}/\n{final_url}'
            results.append(entry)

    return results


def main():
    print("Ümitm0d AndroTV Bot Başladı...")
    all_content = ["#EXTM3U"]
    all_content.extend(get_andro_content())

    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write("\n".join(all_content))
        full_path = os.path.abspath(OUTPUT_FILENAME)
        total_channels = len(all_content) - 1
        print("\nTamamlandı!")
        print(f"Dosya: {OUTPUT_FILENAME}")
        print(f"Kanal Sayısı: {total_channels}")
        print(f"Yol: {full_path}")
    except IOError as e:
        print(f"\nHata: {e}")


if __name__ == "__main__":
    main()
