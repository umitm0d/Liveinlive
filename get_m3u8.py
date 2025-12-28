import requests
import re
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "tr-TR,tr;q=0.9"
}

s = requests.Session()
s.headers.update(headers)

with open("idlist.txt", "r") as f:
    ids = [i.strip() for i in f if i.strip()]

out = open("m3u8_list.txt", "w")

for vid in ids:
    url = f"https://www.youtube.com/watch?v={vid}"
    r = s.get(url, timeout=15)
    html = r.text

    m = re.search(r'"hlsManifestUrl":"([^"]+\.m3u8[^"]*)"', html)
    if m:
        m3u8 = m.group(1).replace("\\/", "/")
        out.write(m3u8 + "\n")
    else:
        out.write(f"# YOK: {vid}\n")

    time.sleep(2)

out.close()
