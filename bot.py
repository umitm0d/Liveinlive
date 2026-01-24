import requests
import re

# ================== AYARLAR ==================
DIZILER_URL = "https://tvdiziler.tv/diziler"
WORKER_BASE = "https://tvdiziler.umittv.workers.dev/?id="
OUTPUT_FILE = "iptv_list.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# ================== DIZI SLUGLARINI CEK ==================
def get_dizi_slugs():
    print("Dizi listesi çekiliyor...")
    r = requests.get(DIZILER_URL, headers=HEADERS, timeout=15)

    if r.status_code != 200:
        print("Sayfa alınamadı:", r.status_code)
        return []

    slugs = re.findall(r'/dizi/([a-z0-9\-]+)', r.text)
    slugs = sorted(set(slugs))

    print(f"Bulunan dizi sayısı: {len(slugs)}")
    return slugs

# ================== M3U OLUSTUR ==================
def create_m3u(slugs):
    if not slugs:
        print("Liste boş.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for slug in slugs:
            title = slug.replace("-", " ").title()

            # 🔥 Worker son bölümü otomatik çözüyor
            stream_url = f"{WORKER_BASE}{slug}&latest=1&ext=m3u8"

            f.write(f'#EXTINF:-1 group-title="TvDiziler", {title}\n')
            f.write(stream_url + "\n")

    print("\n✓ M3U oluşturuldu")
    print("Dosya:", OUTPUT_FILE)
    print("Toplam kanal:", len(slugs))

# ================== MAIN ==================
if __name__ == "__main__":
    print("TvDiziler → IPTV Worker BOT")
    print("=" * 45)

    dizi_slugs = get_dizi_slugs()
    create_m3u(dizi_slugs)
