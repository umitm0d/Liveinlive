import os
import requests
import yaml
import sys
import re

# --- Yardımcı Fonksiyonlar ---

def load_config():
    # Önce environment variable'dan kontrol et
    source_url = os.getenv('SOURCE_PLAYLIST_URL')
    if source_url:
        return {
            'source_playlist_url': source_url,
            'output_file': 'umitm0d.m3u'
        }
    
    # Sonra config.yml'den dene
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

# --- Ana Fonksiyon ---
def main():
    config = load_config()
    source_content = fetch_playlist(config['source_playlist_url'])
    channels_list = parse_source_playlist(source_content)
    new_playlist_content = build_new_playlist(channels_list)
    save_playlist(new_playlist_content, config['output_file'])

if __name__ == "__main__":
    main()
