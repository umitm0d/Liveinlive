import re
import certifi
import os
import requests
import dropbox

# Environment variables'dan al
CHANNEL_LOGO = os.getenv("CHANNEL_LOGO", "https://github.com/BuddyChewChew/gen-playlist/blob/main/docs/ch.png?raw=true")
DOCS_DIR = "docs"
PLAYLIST_FILE = f"{DOCS_DIR}/combined_playlist.m3u"

# Server URL'leri environment'dan al
SERVER2_URL = os.getenv("SERVER2_URL", "https://adult-tv-channels.click/C1Ep6maUdBIeKDQypo7a")
SERVER3_URL = os.getenv("SERVER3_URL", "https://fuckflix.click/8RLxsc2AW1q8pvyvjqIQ")

# Klasör yoksa oluştur
os.makedirs(DOCS_DIR, exist_ok=True)

def create_nojekyll():
    with open(f"{DOCS_DIR}/.nojekyll", "w") as f:
        pass

def upload_to_dropbox(file_path, dropbox_path):
    dbx = dropbox.Dropbox(
        oauth2_refresh_token=os.environ["DROPBOX_REFRESH_TOKEN"],
        app_key=os.environ["DROPBOX_APP_KEY"],
        app_secret=os.environ["DROPBOX_APP_SECRET"]
    )
    with open(file_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
    print(f"✅ Playlist Dropbox'a yüklendi: {dropbox_path}")

def runServers():
    create_nojekyll()

    # Başlık satırı
    with open(PLAYLIST_FILE, "w", encoding='utf-8-sig') as file:
        file.write("#EXTM3U x-tvg-url=\"https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz\"\n")

    # Server 1
    for i, name in enumerate(lis):
        print(f"{i+1}. {name}")
        server1(i + 1, name)

    # Server 2
    for i, hash in enumerate(hashCode):
        print(f"{i+1}. {channels[i]}")
        server2(hash, channels[i])

    # Server 3
    for i, hash in enumerate(hashcode_3):
        print(f"{i+1}. {channels_3[i]}")
        server3(hash, channels_3[i])

    # Dropbox yüklemesi
    upload_to_dropbox(PLAYLIST_FILE, "/XPORN/combined_playlist.m3u")

def server1(i, name):
    print("Running Server 1")
    url = f"https://thedaddy.to/embed/{name}.php"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://adult-tv-channels.com",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        response = requests.get(url, headers=headers, verify=certifi.where(), timeout=10)
        match = re.search(r'file:\s*"([^"]+playlist\.m3u8[^"]*)"', response.text)
        if match:
            stream_url = match.group(1)
            with open(PLAYLIST_FILE, "a", encoding='utf-8-sig') as file:
                file.write(f'#EXTINF:-1 tvg-id="Adult.Programming.Dummy.us" tvg-name="{name}" tvg-logo="{CHANNEL_LOGO}" group-title="Adult 1",{name}\n')
                file.write(f"{stream_url}\n")
        else:
            print(f"😡 Server 1 - URL bulunamadı: {name}")
    except Exception as e:
        print(f"Server 1 hata: {name} -> {str(e)}")

def server2(hash, name):
    print("Running Server 2")
    try:
        res = requests.post(
            f"{SERVER2_URL}/{hash}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        data = res.json()
        token = data["fileUrl"]
        stream_url = f"https://moonlight.wideiptv.top/{name}/index.fmp4.m3u8?token={token}"
        with open(PLAYLIST_FILE, "a", encoding='utf-8-sig') as file:
            file.write(f'#EXTINF:-1 tvg-id="Adult.Programming.Dummy.us" tvg-name="{name}" tvg-logo="{CHANNEL_LOGO}" group-title="Adult 2",{name}\n')
            file.write(f"{stream_url}\n")
    except Exception as e:
        print(f"Server 2 hata: {name} -> {str(e)}")

def server3(hash, name):
    print("Running Server 3")
    try:
        res = requests.post(
            f"{SERVER3_URL}/{hash}", 
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        data = res.json()
        token = data["fileUrl"]
        stream_url = f"https://moonlight.wideiptv.top/{name}/index.fmp4.m3u8?token={token}"
        with open(PLAYLIST_FILE, "a", encoding='utf-8-sig') as file:
            file.write(f'#EXTINF:-1 tvg-id="Adult.Programming.Dummy.us" tvg-name="{name}" tvg-logo="{CHANNEL_LOGO}" group-title="Adult 3",{name}\n')
            file.write(f"{stream_url}\n")
    except Exception as e:
        print(f"Server 3 hata: {name} -> {str(e)}")

# Kanal listeleri (aynı)
lis = [
    "brazzerstv","hustlerhd","hustlertv","penthouse","redlight","penthousepassion","vivid",
    "dorcel","superone","oxax","passie","eroxxx","playboy","pinko","extasy","penthousereality",
    "kinoxxx","pinkerotic","pinkerotic7","pinkerotic8","evilangel","private","beate","meiden",
    "centoxcento","barelylegal","venus","freextv","erox","passion","satisfaction","jasmin",
    "fap","olala","miamitv"
]

hashCode = [
    "Sdw0p0xE3E","yoni9C8jfd","ZS40W182Zq","czS16artgz","xBFRYv6yXh","hghdvp9Z03","ByYpxFkJZe",
    "5LvPjA7oms","HdcCGPssEy","sI8DBZkklJ","sSEWMS7slF","dRTbLz32p7","Sd6GJ5uMmj","IDLur5k1x2",
    "4FVedsyYlB","S8XdeQ0R1t","svpUwVLRR8","A2PZR5jdH8","3uGUuSP7HX","oEd93JisZ3","E3WyHBCn6j",
    "5QeEhtMv0v","ZQgSJJmzAx","JTzDFcBdgp","58Nyzda2hb","ZvBCE7cpgP","V2D4lPbasF","t6VXUhiBYF",
    "JiA1DWNWJc"
]

channels = [
    "ExxxoticaTV","LeoTV","LeoGoldTV","EvilAngel","VIXEN","Extasy4K","PinkoClubTV","BrazzersTVEU",
    "HustlerHD","RedlightHD","SecretCircleTV","PenthouseGold","Television-X","Private","HOT-HD",
    "BODYSEX","DorcelTV","TransAngels","SuperONE","SextremeTV","SeXation","PassionXXX","HustlerTV",
    "EroX-XxX","EroLuxeShemales","DesireTV","CentoXCento","Barely-Legal-TV","Venus"
]

hashcode_3 = [
    "5LvPjA7oms","CudzGm9xm6","T3PIyktDDU","9itOC3AHqJ","OWMDBFfu89","QOOfbBqT4v","2x7HptDKuX",
    "esdMCy0VGM","6s6dIMWGXi","Sdw0p0xE3E","ZS40W182Zq","yoni9C8jfd","czS16artgz","hghdvp9Z03",
    "xBFRYv6yXh","E3WyHBCn6j","HdcCGPssEy","ByYpxFkJZe","Sd6GJ5uMmj","t6VXUhiBYF","58Nyzda2hb",
    "sSEWMS7slF","s4URaZHdvZ","sI8DBZkklJ","YC81XHWeHu","v3UeIcgWXa","dRTbLz32p7","IDLur5k1x2",
    "JAZlXsiLni","R4ol8r2lki","kpTVK5NF1w","m6Elk7hY4x","S8XdeQ0R1t","4FVedsyYlB","svpUwVLRR8",
    "A2PZR5jdH8","3uGUuSP7HX","oEd93JisZ3","5QeEhtMv0v","ZQgSJJmzAx","JTzDFcBdgp","ZvBCE7cpgP",
    "V2D4lPbasF","JiA1DWNWJc","jK2r6H1Dlj"
]

channels_3 = [
    "BrazzersTVEU","Tiny4k1","Tiny4k2","Tiny4k3","PenthouseBLACK","Penthouse","NuartTV","Mofos",
    "cum4k","ExxxoticaTV","LeoGoldTV","LeoTV","EvilAngel","Extasy4K","VIXEN","SeXation","HustlerHD",
    "PinkoClubTV","Television-X","Barely-Legal-TV","EroLuxeShemales","SecretCircleTV","Beate-Uhse",
    "RedlightHD","DorcelTVAfrica","PlayboyTV","PenthouseGold","Private","HOTMan","SexyHOT",
    "TransErotica","HOTXXL","BODYSEX","HOT-HD","DorcelTV","TransAngels","SuperONE","SextremeTV",
    "PassionXXX","HustlerTV","EroX-XxX","DesireTV","CentoXCento","Venus","XXL"
]

# Script başlat
if __name__ == "__main__":
    runServers()
