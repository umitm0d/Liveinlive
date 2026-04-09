import requests
import json
import sys

# --- BURAYA SADECE TOKEN'I YAPIŞTIR ---
# Verdiğin token'ı buraya ekledim.
# Eğer "401" hatası alırsan yeni token'ı buraya tırnak içine yapıştır.
MY_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IkhPNnNLclR0OGNodHBhRWJMVThJdER3LUVtS2k3Vjk3QTdKY0JRUnYySVEiLCJ0eXAiOiJKV1QifQ.eyJlbWFpbCI6Im1yLmF5a3V0c2VuQGdtYWlsLmNvbSIsImV4cCI6MTc3MDA3ODIwNSwiaWF0IjoxNzcwMDU2NjA1LCJqdGkiOiI5MGUyMzM3OC0zMDQ0LTQ3M2EtODI4MS0yYzdhOTVmMmIzZWYiLCJraWRzIjpmYWxzZSwibWF0dXJpdHlMZXZlbCI6IjE4KyIsIm5hbWUiOiJBeWt1dCDFn2VuIiwicGFpckp0aSI6ImFlZjYxZDY1LWQ2NTMtNDMwZC05YTMxLTNkZDg3ZTA0NjFlZSIsInBpZCI6IjYwZjExMjgzLTliYzktNDlkNi1hMDA0LWVjZDc2NGRiM2MwNiIsInNpZCI6ImJiNTQwNmMyLWRjM2MtNGZmZS1iZjE5LTUwNTE1ZTAyODUwMSIsInN1YiI6ImMyNDA2NzFkLTc1NzgtNGZhNS04YmQzLTkzZjQ4Yjg1Mzc0ZCJ9.ZAUHjfMbLxSEXyv6TwQbJZwbfwtH7C7h83CZrd4rImDn0DdksC-oKxni5gYx6bRqUPV2cDwWIF8aMFN8khDB5hSMgK5WwWmtxbLGhm5JCWwxx3An3QkDCpiZiesDQj-wqxtb4cjl6ZjbeIeXN_7qPO-7QHTu8aDjYkmUUxpPFWL4jUNyezUULKV8YtEnnSq6Z4zgYg2gfDYWLRYGxPVj0ojcXaQnjp4pqKp9d-M23_vXFyFl8BclvUwcvvW_UbVRM4zgI28yShVJg2ozwafQWgc4gL7jdJfYfOSD0swPdAjCifVdgkXGJT1ZcFyAiymSVblMdfCb4BJGF8g5P5kPiA"

# --- AYARLAR ---
BASE_URL = "https://eu1.tabii.com/apigateway"
TARGET_ID = "149106_149112"  # Diziler Listesi

# Android Taklidi Yapan Başlıklar
HEADERS = {
    "Authorization": f"Bearer {MY_TOKEN}",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; SM-G960F Build/QP1A.190711.020)",
    "Content-Type": "application/json",
    "x-tenant-id": "TRT"
}

def get_data_direct():
    print(f"📡 Token ile {TARGET_ID} sayfasına erişim deneniyor...")
    
    url = f"{BASE_URL}/pbr/v1/pages/browse/{TARGET_ID}"
    
    try:
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code == 200:
            print("✅ BAŞARILI! Sayfa verisi çekildi.")
            return response.json()
        elif response.status_code == 401:
            print("❌ HATA: Token geçersiz veya süresi dolmuş (401 Unauthorized).")
            print("👉 Lütfen güncel bir token alıp koddaki MY_TOKEN alanına yapıştır.")
            sys.exit(1)
        else:
            print(f"❌ HATA: Sayfaya erişilemedi. Kod: {response.status_code}")
            print(f"Cevap: {response.text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        sys.exit(1)

def generate_files(data):
    if not data:
        print("❌ Veri boş.")
        return

    m3u_content = "#EXTM3U\n"
    json_list = []
    
    # İçerikleri Bul
    elements = []
    if "components" in data:
        for comp in data["components"]:
            if "elements" in comp:
                elements.extend(comp["elements"])

    print(f"📂 Listede {len(elements)} öğe bulundu. Linkler oluşturuluyor...")

    for item in elements:
        try:
            item_id = item.get("id")
            title = item.get("title", "Bilinmeyen")
            
            # Görsel URL
            img = ""
            if "images" in item and item["images"]:
                img = item["images"][0].get("url", "")
                if img and not img.startswith("http"):
                    img = f"https://cms-tabii-assets.tabii.com{img}"

            # MPD Linki
            stream_url = f"{BASE_URL}/pbr/v1/media/{item_id}/master.mpd"

            # M3U Formatı
            m3u_content += f'#EXTINF:-1 tvg-id="{item_id}" tvg-logo="{img}", {title}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
            m3u_content += f'#EXTVLCOPT:http-header-authorization=Bearer {MY_TOKEN}\n'
            m3u_content += f'{stream_url}\n'

            # JSON Formatı
            json_list.append({
                "id": item_id,
                "title": title,
                "thumbnail": img,
                "stream_url": stream_url,
                "headers": {
                    "Authorization": f"Bearer {MY_TOKEN}",
                    "User-Agent": HEADERS["User-Agent"]
                }
            })
        except:
            continue

    # Dosyaları Kaydet
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    with open("tabii_data.json", "w", encoding="utf-8") as f:
        json.dump(json_list, f, ensure_ascii=False, indent=4)

    print("✅ İşlem Tamam! playlist.m3u oluşturuldu.")

if __name__ == "__main__":
    # Token zaten yukarıda tanımlı
    data = get_data_direct()
    generate_files(data)
