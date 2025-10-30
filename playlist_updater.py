import os
import requests
import yaml
import sys
import re
import json

# --- Yardımcı Fonksiyonlar ---

def load_config():
    source_url = os.getenv('SOURCE_PLAYLIST_URL')
    if source_url:
        return {
            'source_playlist_url': source_url,
            'output_file': 'umitm0d.m3u'
        }

    try:
        with open('config.yml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if not config:
                print("HATA: Yapılandırma dosyası boş")
                sys.exit(1)
            return config
    except FileNotFoundError:
        print("HATA: Config dosyası bulunamadı ve SOURCE_PLAYLIST_URL environment variable tanımlı değil")
        sys.exit(1)
    except Exception as e:
        print(f"HATA: Yapılandırma okunurken hata: {e}")
        sys.exit(1)


def fetch_playlist(url):
    try:
        print(f"Kaynak liste indiriliyor: {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"HATA: Kaynak liste indirilemedi: {e}")
        sys.exit(1)


def parse_source_playlist(source_content):
    print("\n--- Kaynak Liste Analiz Ediliyor ---")
    channels = []
    lines = source_content.splitlines()
    last_extinf = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#EXTINF:'):
            last_extinf = line
        elif last_extinf and not line.startswith('#'):
            group_title = "GRUPSUZ KANALLAR"
            match = re.search(r'group-title=(["\'])(.*?)\1', last_extinf, re.IGNORECASE)
            if match:
                title = match.group(2).strip()
                if title:
                    group_title = title
            channels.append({
                'group': group_title,
                'extinf': last_extinf,
                'url': line
            })
            last_extinf = None

    print(f"\nAnaliz tamamlandı. Toplam {len(channels)} kanal bulundu.")
    if len(channels) == 0:
        print("UYARI: Kaynak listeden hiç kanal ayrıştırılamadı.")
    return channels


def build_new_playlist(channels):
    if not channels:
        return "#EXTM3U\n# UYARI: İşlenecek hiç kanal bulunamadı."

    channels.sort(key=lambda x: (x['group'].lower(), x['extinf'].lower()))

    turkish_channels = []
    other_channels = []

    turkish_keywords = ['türk', 'turk', 'türkçe', 'turkish']

    for channel in channels:
        content_to_check = (channel['group'] + " " + channel['extinf']).lower()
        if any(keyword in content_to_check for keyword in turkish_keywords):
            turkish_channels.append(channel)
        else:
            other_channels.append(channel)

    output_lines = ['#EXTM3U']

    for channel in turkish_channels + other_channels:
        output_lines.append(channel['extinf'])
        output_lines.append(channel['url'])

    return "\n".join(output_lines)


def save_playlist(content, output_file):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nİşlem başarıyla tamamlandı! Yeni liste: '{output_file}'")
    except IOError as e:
        print(f"HATA: Sonuç dosyası yazılamadı: {e}")
        sys.exit(1)


# --- Dropbox Fonksiyonları ---

def get_dropbox_access_token():
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")

    if not all([refresh_token, app_key, app_secret]):
        print("UYARI: Dropbox kimlik bilgileri eksik, yükleme atlanacak.")
        return None

    try:
        response = requests.post(
            "https://api.dropbox.com/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth=(app_key, app_secret),
            timeout=20
        )
        response.raise_for_status()
        access_token = response.json().get("access_token")
        return access_token
    except Exception as e:
        print(f"HATA: Dropbox access token alınamadı: {e}")
        return None


def upload_to_dropbox(local_file, dropbox_path):
    """Dropbox'a dosyayı YALNIZCA overwrite modunda yükler (link sabit kalır)."""
    access_token = get_dropbox_access_token()
    if not access_token:
        return

    print(f"\nDropbox'a yükleniyor (üzerine yazılacak): {dropbox_path}")
    try:
        with open(local_file, "rb") as f:
            data = f.read()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
            "Dropbox-API-Arg": json.dumps({
                "path": dropbox_path,
                "mode": "overwrite",   # 🔑 sadece üzerine yazar, silmez
                "mute": False
            })
        }

        response = requests.post(
            "https://content.dropboxapi.com/2/files/upload",
            headers=headers,
            data=data,
            timeout=60
        )

        if response.status_code == 200:
            print("✅ Dropbox yüklemesi başarılı (dosya güncellendi)!")
            ensure_shared_link(access_token, dropbox_path)
        else:
            print(f"❌ Dropbox yüklemesi başarısız: {response.text}")

    except Exception as e:
        print(f"HATA: Dropbox yüklemesinde hata: {e}")


def ensure_shared_link(access_token, dropbox_path):
    """Paylaşım linki zaten varsa onu kullan, yoksa oluştur."""
    try:
        # 1. Mevcut linki kontrol et
        list_resp = requests.post(
            "https://api.dropboxapi.com/2/sharing/list_shared_links",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"path": dropbox_path},
            timeout=15
        )
        list_data = list_resp.json()
        links = list_data.get("links", [])
        if links:
            print(f"🔗 Paylaşım linki (sabit): {links[0]['url']}")
            return links[0]['url']

        # 2. Yoksa yeni link oluştur
        create_resp = requests.post(
            "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"path": dropbox_path, "settings": {"requested_visibility": "public"}},
            timeout=15
        )
        create_data = create_resp.json()
        if "url" in create_data:
            print(f"🔗 Yeni paylaşım linki oluşturuldu: {create_data['url']}")
            return create_data["url"]
        else:
            print(f"❌ Paylaşım linki oluşturulamadı: {create_data}")
    except Exception as e:
        print(f"HATA: Paylaşım linki kontrolü başarısız: {e}")
        return None


# --- Ana Fonksiyon ---

def main():
    config = load_config()
    source_content = fetch_playlist(config['source_playlist_url'])
    channels_list = parse_source_playlist(source_content)
    new_playlist_content = build_new_playlist(channels_list)
    save_playlist(new_playlist_content, config['output_file'])
    upload_to_dropbox(config['output_file'], f"/{config['output_file']}")


if __name__ == "__main__":
    main()
