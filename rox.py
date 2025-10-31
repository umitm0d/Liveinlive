import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.exceptions import RequestException
import logging

BASE_URL = "https://roxiestreams.cc"

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


def discover_sections(base_url):
    """Finds main category links (e.g., /nba, /ufc)."""
    logging.info(f"Discovering sections on {base_url}...")
    sections_found = []
    try:
        resp = SESSION.get(base_url, timeout=10)
        resp.raise_for_status()
    except RequestException as e:
        logging.error(f"Failed to fetch base URL {base_url}: {e}")
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
            logging.info(f"  [Found] {title} -> {abs_url}")
            sections_found.append((abs_url, title))

    return sections_found


def discover_event_links(section_url):
    """Finds event links from each category page."""
    events = set()
    try:
        resp = SESSION.get(section_url, timeout=10)
        resp.raise_for_status()
    except RequestException as e:
        logging.warning(f"  Failed to fetch section page {section_url}: {e}")
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
        logging.warning(f"    Failed to fetch event page {page_url}: {e}")
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
        logging.info(f"\n--- Processing Section: {section_title} ({section_url}) ---")

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

    output_filename = "Roxiestreams.m3u8"
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(playlist_lines))
        logging.info(f"\n--- SUCCESS ---")
        logging.info(f"Playlist saved as {output_filename}")
        logging.info(f"Total valid streams found: {(len(playlist_lines) - 1) // 2}")
    except IOError as e:
        logging.error(f"Failed to write file {output_filename}: {e}")


if __name__ == "__main__":
    main()
