import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.exceptions import RequestException
import logging
import dropbox
from datetime import datetime
import os
import json

# Base URL'i environment variable'dan al
BASE_URL = os.getenv('ROXIESTREAMS_BASE_URL', '')
if not BASE_URL:
    logging.error("ROXIESTREAMS_BASE_URL environment variable tanımlı değil!")
    exit(1)

TV_INFO = {
    "ppv": ("PPV.EVENTS.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/PPV.png", "PPV"),
    "soccer": ("Soccer.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Soccer.png", "Soccer"),
    "ufc": ("UFC.Fight.Pass.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/CombatSports2.png", "UFC"),
    "fighting": ("PPV.EVENTS.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Combat-Sports.png", "Combat Sports"),
    "nfl": ("Football.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Maxx.png", "NFL"),
    "nba": ("NBA.Basketball.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Basketball-2.png", "NBA"),
    "mlb": ("MLB.Baseball.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Baseball3.png", "MLB"),
    "wwe": ("PPV.EVENTS.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/WWE2.png", "WWE"),
    "f1": ("Racing.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/F1.png", "Formula 1"),
    "motorsports": ("Racing.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/F1.png", "Motorsports"),
    "nascar": ("Racing.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Motorsports2.png", "NASCAR Cup Series"),
}

DISCOVERY_KEYWORDS = list(TV_INFO.keys()) + ['streams']
SECTION_BLOCKLIST = ['olympia']

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': BASE_URL
})

M3U8_REGEX = re.compile(r'https?://[^\s"\'<>`]+\.m3u8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_dropbox_access_token():
    """Environment variables'dan Dropbox token'ını alır"""
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")

    if not all([refresh_token, app_key, app_secret]):
        logging.warning("Dropbox kimlik bilgileri eksik, yükleme atlanacak.")
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
        logging.info("Dropbox access token başarıyla alındı")
        return access_token
    except Exception as e:
        logging.error(f"Dropbox access token alınamadı: {e}")
        return None

def upload_to_dropbox(local_file, dropbox_path):
    """Dropbox'a dosyayı YALNIZCA overwrite modunda yükler (link sabit kalır)."""
    access_token = get_dropbox_access_token()
    if not access_token:
        return None

    logging.info(f"Dropbox'a yükleniyor (üzerine yazılacak): {dropbox_path}")
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
            logging.info("✅ Dropbox yüklemesi başarılı (dosya güncellendi)!")
            return ensure_shared_link(access_token, dropbox_path)
        else:
            logging.error(f"❌ Dropbox yüklemesi başarısız: {response.text}")
            return None

    except Exception as e:
        logging.error(f"HATA: Dropbox yüklemesinde hata: {e}")
        return None

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
            shared_url = links[0]['url']
            download_url = shared_url.replace("?dl=0", "?dl=1")
            logging.info(f"🔗 Paylaşım linki (sabit): {download_url}")
            return download_url

        # 2. Yoksa yeni link oluştur
        create_resp = requests.post(
            "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"path": dropbox_path, "settings": {"requested_visibility": "public"}},
            timeout=15
        )
        create_data = create_resp.json()
        if "url" in create_data:
            shared_url = create_data["url"]
            download_url = shared_url.replace("?dl=0", "?dl=1")
            logging.info(f"🔗 Yeni paylaşım linki oluşturuldu: {download_url}")
            return download_url
        else:
            logging.error(f"❌ Paylaşım linki oluşturulamadı: {create_data}")
            return None
    except Exception as e:
        logging.error(f"HATA: Paylaşım linki kontrolü başarısız: {e}")
        return None

def discover_sections(base_url):
    """Finds main category links (e.g., /nba, /ufc)."""
    logging.info(f"Discovering sections...")
    sections_found = []
    try:
        resp = SESSION.get(base_url, timeout=10)
        resp.raise_for_status()
    except RequestException as e:
        logging.error(f"Failed to fetch base URL: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    discovered_urls = set()

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        title = a_tag.get_text(strip=True)
        if not href or href.startswith(('#', 'javascript:', 'mailto:')) or not title:
            continue

        abs_url = urljoin(base_url, href)

        if any(blocked in abs_url.lower() for blocked in SECTION_BLOCKLIST):
            continue

        if (urlparse(abs_url).netloc == urlparse(base_url).netloc and
                any(keyword in abs_url.lower() for keyword in DISCOVERY_KEYWORDS) and
                abs_url not in discovered_urls):

            discovered_urls.add(abs_url)
            logging.info(f"  [Found] {title}")
            sections_found.append((abs_url, title))

    return sections_found

def discover_event_links(section_url):
    """Finds event links from each category page."""
    events = set()
    try:
        resp = SESSION.get(section_url, timeout=10)
        resp.raise_for_status()
    except RequestException as e:
        logging.warning(f"  Failed to fetch section page: {e}")
        return events

    soup = BeautifulSoup(resp.text, 'html.parser')
    event_table = soup.find('table', id='eventsTable')
    if not event_table:
        return events

    for a_tag in event_table.find_all('a', href=True):
        href = a_tag['href']
        title = a_tag.get_text(strip=True)
        if not href or not title:
            continue
        abs_url = urljoin(section_url, href)
        if abs_url.startswith(BASE_URL):
            events.add((abs_url, title))
    return events

def extract_m3u8_links(page_url):
    """Extracts .m3u8 links from event page."""
    links = set()
    try:
        resp = SESSION.get(page_url, timeout=10)
        resp.raise_for_status()
        links.update(M3U8_REGEX.findall(resp.text))
    except RequestException as e:
        logging.warning(f"    Failed to fetch event page: {e}")
    return links

def check_stream_status(m3u8_url):
    """Validates a .m3u8 stream."""
    try:
        resp = SESSION.head(m3u8_url, timeout=5, allow_redirects=True)
        return resp.status_code == 200
    except RequestException:
        return False

def get_tv_info(url):
    """Matches a section URL to tvg-id, logo, and smart name."""
    for key, (tvgid, logo, group_name) in TV_INFO.items():
        if key in url.lower():
            return tvgid, logo, group_name
    return ("Unknown.Dummy.us", "", "Misc")

def main():
    playlist_lines = ["#EXTM3U"]

    sections = list(discover_sections(BASE_URL))
    if not sections:
        logging.error("No sections discovered.")
        return

    logging.info(f"Found {len(sections)} sections. Scraping for events...")

    for section_url, section_title in sections:
        logging.info(f"\n--- Processing Section: {section_title} ---")

        tv_id, logo, group_name = get_tv_info(section_url)
        event_links = discover_event_links(section_url)

        if not event_links:
            logging.info(f"  No event sub-pages found. Scraping directly.")
            event_links = {(section_url, section_title)}

        valid_count = 0
        for event_url, event_title in event_links:
            logging.info(f"  Scraping: {event_title}")
            m3u8_links = extract_m3u8_links(event_url)

            for link in m3u8_links:
                if check_stream_status(link):
                    playlist_lines.append(
                        f'#EXTINF:-1 tvg-logo="{logo}" tvg-id="{tv_id}" group-title="Roxiestreams - {group_name}",{event_title}'
                    )
                    playlist_lines.append(link)
                    valid_count += 1

        logging.info(f"  Added {valid_count} valid streams for {group_name} section.")

    # SABİT dosya adı kullan - her seferinde aynı dosyanın üzerine yazsın
    output_filename = "Roxiestreams.m3u8"
    
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(playlist_lines))
        logging.info(f"\n--- LOCAL SUCCESS ---")
        logging.info(f"Playlist saved as {output_filename}")
        logging.info(f"Total valid streams found: {(len(playlist_lines) - 1) // 2}")
        
        # Dropbox'a yükle - SABİT dosya adıyla
        logging.info("\n--- DROPBOX UPLOAD ---")
        dropbox_path = f"/{output_filename}"  # Her zaman aynı dosya
        download_url = upload_to_dropbox(output_filename, dropbox_path)
        
        if download_url:
            logging.info(f"📥 SABİT İndirme Linki: {download_url}")
            # Artık txt dosyasına kaydetmiyoruz, sadece log'da gösteriyoruz
        else:
            logging.warning("⚠ Dropbox'a yükleme başarısız veya atlandı!")

    except IOError as e:
        logging.error(f"Failed to write file {output_filename}: {e}")

if __name__ == "__main__":
    main()
