#!/usr/bin/env python3
import requests
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

TOTAL = 5000
WORKERS = 40
PROXY = "https://proxy.umittv.workers.dev/?url="

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.ginikoturkish.com/"
}

ALLOWED_DOMAINS = ["trn03.tulix.tv", "tgn.bozztv.com"]

TURKISH_KEYWORDS = [
    'TRT', 'ATV', 'TV8', 'SHOW', 'KANAL', 'STAR', 'NOW', 'FOX', 'KANAL 7',
    'BEYAZ', 'FLASH', 'TGRT', 'TELE1', 'KRT', 'HALK', 'SZC', 'EKOL',
    'HABER', 'NTV', 'CNN', '24 TV', 'ULUSAL', 'BLOOMBERG',
    'SPOR', 'SPORT', 'BEIN', 'TJK', 'BELGESEL', 'DMAX', 'TLC',
    'SINEMA', 'YESILCAM', 'DIZI', 'FILM', 'COCUK', 'MINIKA'
]


def check_channel(ch_id):
    """Her iki domain için iki ayrı URL'yi dener, ilk bulunanı döner."""

    endpoints = [
        ("ginikoturkish", f"https://ginikoturkish.com/xml/secure/plist.php?ch={ch_id}"),
        ("giniko",        f"https://www.giniko.com/xml/secure/plist.php?ch={ch_id}"),
    ]

    for source, url in endpoints:
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue

            text = r.text
            if "HlsStreamURL" not in text:
                continue
            if "<string>false</string>" not in text:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            stream_url = None
            last_isvod = None

            # Satır bazlı parse (plist formatı)
            for i, line in enumerate(lines):
                if line == "isVOD" and i + 1 < len(lines):
                    last_isvod = lines[i + 1]
                if line == "HlsStreamURL" and i + 1 < len(lines):
                    u = lines[i + 1]
                    if u.startswith("http") and last_isvod == "false":
                        stream_url = u
                        break

            # Regex fallback
            if not stream_url:
                m = re.search(
                    r'<key>isVOD</key>\s*<string>false</string>.*?'
                    r'<key>HlsStreamURL</key>\s*<string>(.*?)</string>',
                    text, re.DOTALL
                )
                if m:
                    stream_url = m.group(1)

            if not stream_url:
                continue

            # Domain filtresi: izin verilen domainlerden biri olmalı
            if not any(d in stream_url for d in ALLOWED_DOMAINS):
                continue

            # İsim
            name = None
            for i, line in enumerate(lines):
                if line == "name" and i + 1 < len(lines) and not lines[i + 1].startswith("http"):
                    name = lines[i + 1].replace(" - Live", "").strip()
                    break
            if not name:
                m = re.search(r'<key>name</key>\s*<string>(.*?)</string>', text)
                name = m.group(1).replace(" - Live", "").strip() if m else f"Kanal {ch_id}"

            # Logo
            logo = None
            for i, line in enumerate(lines):
                if line == "logoUrlHD" and i + 1 < len(lines) and lines[i + 1].startswith("http"):
                    logo = lines[i + 1]
                    break
            if not logo:
                m = re.search(r'<key>logoUrlHD</key>\s*<string>(.*?)</string>', text)
                logo = m.group(1) if m else f"https://www.giniko.com/logos/190x110/{ch_id}.jpg"

            print(f"✓ [{source}] {ch_id}: {name}")

            return {
                "id": ch_id,
                "name": name,
                "logo": logo,
                "stream": stream_url,
                "proxied_stream": f"{PROXY}{stream_url}",
                "source": source,
                "xmlUrl": url
            }

        except:
            continue

    return None


def is_turkish(name):
    name_upper = name.upper()
    if any(c in name_upper for c in "ĞÜŞİÖÇI"):
        return True
    return any(k in name_upper for k in TURKISH_KEYWORDS)


def main():
    print(f"Tarama başlıyor: 1-{TOTAL} (her iki domain)\n")
    results = []

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(check_channel, i): i for i in range(1, TOTAL + 1)}
        done = 0

        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result:
                results.append(result)
            if done % 100 == 0:
                print(f"[{done}/{TOTAL}] Bulunan: {len(results)} kanal")

    # Türk kanalları önce, sonra ID sırasına göre
    results.sort(key=lambda x: (not is_turkish(x["name"]), x["id"]))

    # JSON kaydet
    with open("umitginiko.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # M3U oluştur
    m3u_lines = ["#EXTM3U\n"]
    for ch in results:
        group = "Türk Kanalları" if is_turkish(ch["name"]) else "Yabancı Kanallar"
        m3u_lines.append(
            f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" '
            f'tvg-logo="{ch["logo"]}" group-title="{group}",{ch["name"]}\n'
            f'{ch["proxied_stream"]}\n'
        )

    with open("umitginiko.m3u", "w", encoding="utf-8") as f:
        f.writelines(m3u_lines)

    turkish_count = sum(1 for ch in results if is_turkish(ch["name"]))
    print(f"\nToplam {len(results)} kanal bulundu")
    print(f"  → Türk kanalı : {turkish_count}")
    print(f"  → Yabancı     : {len(results) - turkish_count}")
    print("umitginiko.json kaydedildi")
    print("umitginiko.m3u  kaydedildi (proxy ile)")


if __name__ == "__main__":
    main()
