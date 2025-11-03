import requests
import re
import concurrent.futures
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor
import time
import urllib3
import os
import dropbox

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -----------------------------
# Dropbox ve M3U sabitleri
# -----------------------------
DOCS_DIR = "docs"
os.makedirs(DOCS_DIR, exist_ok=True)
OUTPUT_FILE = f"{DOCS_DIR}/playlist.m3u"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz"
TVG_ID = "Blank.Dummy.us"
LOGO_URL = "https://github.com/BuddyChewChew/gen-playlist/blob/main/docs/chb.png?raw=true"

# Cache for URL validation
url_cache = {}

# -----------------------------
# Fonksiyonlar
# -----------------------------
def fetch_content(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.text
    except requests.RequestException as e:
        print(f"Error fetching content: {e}")
        return None

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def check_stream(url, timeout=8, max_attempts=1):
    if url in url_cache:
        return url_cache[url]

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': '*/*',
        'Connection': 'close',
        'Referer': 'https://www.google.com/'
    }

    for attempt in range(max_attempts):
        try:
            if url.endswith(('.m3u8', '.m3u')):
                # Check playlist
                response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
                if response.status_code != 200:
                    return False, url
                # Fetch full playlist for m3u8
                if url.endswith('.m3u8'):
                    response = requests.get(url, headers=headers, timeout=timeout, verify=False)
                    if response.status_code == 200 and '#EXTM3U' in response.text:
                        if '#EXT-X-STREAM-INF' in response.text:
                            variants = re.findall(r'\n([^\n\.]+\.m3u8[^\n]*)', response.text)
                            if variants:
                                variant_url = variants[0]
                                if not variant_url.startswith('http'):
                                    variant_url = urljoin(url, variant_url)
                                return check_stream(variant_url, timeout, 1)
                        return True, url
                    else:
                        return False, url
            else:
                # Direct video/audio
                range_headers = headers.copy()
                range_headers['Range'] = 'bytes=0-1024'
                with requests.get(url, headers=range_headers, timeout=timeout, stream=True, verify=False) as response:
                    if response.status_code in (200, 206):
                        chunk = next(response.iter_content(chunk_size=1024), None)
                        if not chunk:
                            return False, url
                        content_type = response.headers.get('Content-Type', '').lower()
                        if not any(x in content_type for x in ['video/', 'audio/', 'application/octet-stream', 'application/vnd.apple.mpegurl']):
                            return False, url
                        url_cache[url] = (True, url)
                        return True, url
        except Exception:
            if attempt == max_attempts - 1:
                return False, url
            time.sleep(1)
    return False, url

def convert_to_m3u(content, output_file, max_workers=20):
    lines = content.split('\n')
    current_group = ""
    m3u_lines = [
        "#EXTM3U x-tvg-url=\"" + EPG_URL + "\"",
        "#EXT-X-TVG-URL: " + EPG_URL
    ]
    entries = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.endswith(',#genre#'):
            current_group = line.split(',#genre#')[0].strip()
            entries.append(('group', current_group, None))
        elif ',' in line and is_valid_url(line.split(',')[-1]):
            parts = line.rsplit(',', 1)
            if len(parts) == 2 and is_valid_url(parts[1]):
                name, url = parts
                entries.append(('stream', name.strip(), url.strip(), current_group))

    # Parallel stream validation
    valid_streams = []
    stream_entries = [e for e in entries if e[0] == 'stream']
    print(f"Checking {len(stream_entries)} streams for availability...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_entry = {executor.submit(check_stream, e[2]): e for e in stream_entries}
        for future in concurrent.futures.as_completed(future_to_entry):
            entry = future_to_entry[future]
            try:
                is_valid, url = future.result()
                if is_valid:
                    valid_streams.append((entry[1], url, entry[3]))
                    print(f"✓ {entry[1]}")
                else:
                    print(f"✗ {entry[1]} (unreachable)")
            except Exception as e:
                print(f"✗ {entry[1]} (error: {str(e)})")

    # Build M3U file
    current_group = ""
    seen_urls = set()
    for entry in entries:
        if entry[0] == 'group':
            current_group = entry[1]
            m3u_lines.append(f"#EXTINF:-1 tvg-id=\"{TVG_ID}\" group-title=\"{current_group}\",{current_group}")
            m3u_lines.append("#" + current_group)
        else:
            match = next((s for s in valid_streams if s[0]==entry[1] and s[2]==current_group and s[1]==entry[2] and s[1] not in seen_urls), None)
            if match:
                seen_urls.add(match[1])
                m3u_lines.append(f"#EXTINF:-1 tvg-id=\"{TVG_ID}\" tvg-logo=\"{LOGO_URL}\" group-title=\"{current_group}\",{entry[1].split(' ',1)[0] if ' ' in entry[1] else entry[1]}")
                m3u_lines.append(match[1])

    print(f"\nFound {len(valid_streams)}/{len(stream_entries)} working streams")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_lines))
    print(f"Successfully converted to {output_file}")

def upload_to_dropbox(file_path, dropbox_path):
    dbx = dropbox.Dropbox(
        oauth2_refresh_token=os.environ["DROPBOX_REFRESH_TOKEN"],
        app_key=os.environ["DROPBOX_APP_KEY"],
        app_secret=os.environ["DROPBOX_APP_SECRET"]
    )
    with open(file_path, 'rb') as f:
        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
    print(f"✅ Uploaded to Dropbox: {dropbox_path}")

def main():
    url = "https://raw.githubusercontent.com/jack2713/my/refs/heads/main/my02.txt"
    content = fetch_content(url)
    if content:
        start_time = time.time()
        convert_to_m3u(content, OUTPUT_FILE)
        upload_to_dropbox(OUTPUT_FILE, "/XPORN/playlist.m3u")
        end_time = time.time()
        print(f"\nProcessing completed in {end_time - start_time:.2f} seconds")
    else:
        print("Failed to fetch content. Check URL.")

if __name__ == "__main__":
    main()
