import requests
import json
import re

# Ülke isimlerini Türkçeye çevirme eşleme tablosu
country_mapping = {
    "Germany": ("Almanya", "Almanca"),
    "United Kingdom": ("Birleşik Krallık", "İngilizce"),
    "France": ("Fransa", "Fransızca"),
    "Turkey": ("Türkiye", "Türkçe"),
    "Italy": ("İtalya", "İtalanca"),
    "Spain": ("İspanya", "İspanyolca"),
    "Albania": ("Arnavutluk", "Arnavutça"),
    "Arabia": ("Arabistan", "Arapça"),
    "Balkans": ("Balkanlar", "Türkçe"),
    "Bulgaria": ("Bulgaristan", "Bulgarca"),
    "Netherlands": ("Hollanda", "Felemenkçe"),
    "Poland": ("Polonya", "Lehçe"),
    "Portugal": ("Portekiz", "Portekizce"),
    "Russia": ("Rusya", "Rusça"),
}

# Sabit logo URL'si (tüm kanallar için kullanılacak)
FIXED_LOGO_URL = "https://raw.githubusercontent.com/umitm0d/Alakart/refs/heads/main/umitm0d.png"

# Kanal adı -> tvg-id eşleme tablosu (kullanıcı tarafından verilen liste)
tvg_id_mapping = {
    "beIN": "bein",
    "beIN MOVIES PREMIERE": "beinmoviespremiere",
    "beIN MOVIES TURK": "beinmoviesturk",
    "beIN MOVIES STARS": "beinmoviesstars",
    "beIN SERIES 1": "beinseries1",
    "beIN SERIES 2": "beinseries2",
    "beIN İZ": "beini̇z",
    "beIN H&E": "beinh&e",
    "beIN GURME": "beingurme",
    "SHOW TV": "showtv",
    "TRT 1": "trt1",
    "KANAL D": "kanald",
    "ATV": "atv",
    "NOW": "now",
    "STAR TV": "startv",
    "TV8": "tv8",
    "360": "360",
    "CNBC-e": "cnbc-e",
    "BLOOMBERG HT": "bloomberght",
    "AHABER": "ahaber",
    "TRT HABER": "trthaber",
    "KANAL 7": "kanal7",
    "A2": "a2",
    "BEYAZ TV": "beyaztv",
    "tv100": "tv100",
    "ÜLKE TV": "ulketv",
    "TVNET": "tvnet",
    "24 TV": "24tv",
    "NTV": "ntv",
    "CNN TURK": "cnnturk",
    "A PARA": "apara",
    "HABERTURK": "haberturk",
    "TGRT HABER": "tgrthaber",
    "EKOTURK": "ekoturk",
    "HABERGLOBAL": "haberglobal",
    "TELE 1": "tele1",
    "EKOL TV": "ekoltv",
    "FLASH HABER": "flashhaber",
    "LİDER HABER TV": "li̇derhabertv",
    "ULUSAL TV": "ulusaltv",
    "HALK TV": "halktv",
    "TV2": "tv2",
    "TV8,5": "tv8,5",
    "TRT 3 / TRT SPOR": "trt3/trtspor",
    "TRT AVAZ": "trtavaz",
    "TRT KURDI": "trtkurdi",
    "TÜRKHABER TV": "turkhabertv",
    "SÖZCÜ TV": "sozcutv",
    "TRT TURK": "trtturk",
    "KRT TV": "krttv",
    "BENGÜTÜRK": "benguturk",
    "TRT 2": "trt2",
    "VAV TV": "vavtv",
    "DİYANET TV": "di̇yanettv",
    "AKİT TV": "aki̇ttv",
    "GZT": "gzt",
    "TYT TÜRK": "tytturk",
    "HT SPOR": "htspor",
    "FB TV": "fbtv",
    "beIN SPORTS 1": "beinsports1",
    "beIN SPORTS 2": "beinsports2",
    "beIN SPORTS 3": "beinsports3",
    "beIN SPORTS 4": "beinsports4",
    "beIN SPORTS 5": "beinsports5",
    "beIN SPORTS MAX 1": "beinsportsmax1",
    "beIN SPORTS MAX 2": "beinsportsmax2",
    "beIN SPORTS HABER": "beinsportshaber",
    "TRT SPOR": "trtspor",
    "TRT SPOR YILDIZ": "trtsporyildiz",
    "A SPOR": "aspor",
    "EUROSPORT 1": "eurosport1",
    "EUROSPORT 2": "eurosport2",
    "TLC": "tlc",
    "MCM TOP": "mcmtop",
    "MEZZO": "mezzo",
    "TRT MÜZİK": "trtmuzi̇k",
    "FASHION TV": "fashiontv",
    "BBC FIRST": "bbcfirst",
    "RAI1": "rai1",
    "TRT  ARABI": "trtarabi",
    "CGTN": "cgtn",
    "BLOOMBERG": "bloomberg",
    "A NEWS": "anews",
    "BBC WORLD NEWS": "bbcworldnews",
    "TRT WORLD": "trtworld",
    "CNN INTERNATIONAL": "cnninternational",
    "AL JAZEERA CHANNEL": "aljazeerachannel",
    "AL JAZEERA INTERNATIONAL": "aljazeerainternational",
    "EURONEWS": "euronews",
    "TRT EBA HD": "trtebahd",
    "TRT ÇOCUK": "trtcocuk",
    "CBeebies": "cbeebies",
    "BABY TV": "babytv",
    "Da Vinci": "davinci",
    "DISNEY JUNIOR": "disneyjunior",
    "CARTOON NETWORK": "cartoonnetwork",
    "MİNİKAGO": "mi̇ni̇kago",
    "NICK JR": "nickjr",
    "NICKELODEON HD": "nickelodeonhd",
    "NATIONAL GEO.": "nationalgeo.",
    "BBC EARTH": "bbcearth",
    "TARİH TV": "tari̇htv",
    "NAT.GEO.WILD": "nat.geo.wild",
    "DMAX": "dmax",
    "YABAN TV": "yabantv",
    "TRT BELGESEL": "trtbelgesel",
    "DISCOVERY CHANNEL": "discoverychannel",
    "BRT 1": "brt1",
    "BRT 2": "brt2",
}

def get_tvg_id(name, language_code):
    """Kanal adına göre tvg-id belirle; eşleşme tablosunda yoksa eski yönteme düş."""
    if name in tvg_id_mapping:
        return tvg_id_mapping[name]
    # Eşleşme yoksa fallback: eski mantık (isim + dil kodu)
    return f"{name.lower().replace(' ', '').replace('.', '')}.{language_code}"

def sort_key(tvg_name):
    """Sıralama önceliği belirleme"""
    tvg_name_lower = tvg_name.lower()
    is_bein_spor = "bein" in tvg_name_lower and "spor" in tvg_name_lower
    is_spor = "spor" in tvg_name_lower or "sport" in tvg_name_lower

    if is_bein_spor:
        group_priority = 0
    elif is_spor:
        group_priority = 1
    else:
        group_priority = 2

    return (group_priority, tvg_name_lower)

# JSON verisini çek
url = "https://www2.vavoo.to/live2/index?countries=all&output=json"
response = requests.get(url)
channels = response.json()

# Türkiye kanallarını filtrele ve işle
turkey_channels = []

for channel in channels:
    group = channel["group"]

    # Sadece Turkey (Türkiye) kategorisindeki kanalları işle
    if group != "Turkey":
        continue

    name = channel["name"]
    channel_url = channel["url"]

    # Ülke adına göre tvg-country ve tvg-language belirleme
    country_name, language_code = country_mapping.get(group, (group, "xx"))

    # tvg-id oluşturma (eşleşme tablosundan, yoksa fallback)
    tvg_id = get_tvg_id(name, language_code)

    # URL formatını değiştirme
    stream_url = channel_url.replace("live2/play", "play").replace(".ts", "/index.m3u8")

    # Logo her zaman sabit logo
    logo = FIXED_LOGO_URL

    # Kanal bilgilerini listeye ekle
    turkey_channels.append({
        'name': name,
        'tvg_id': tvg_id,
        'logo': logo,
        'language_code': language_code,
        'stream_url': stream_url,
        'sort_priority': sort_key(name)
    })

print(f"Toplam {len(turkey_channels)} kanal bulundu.")

# Sıralama: Önce Bein Spor, sonra diğer spor kanalları, sonra genel kanallar
# Her grup içinde alfabetik
turkey_channels.sort(key=lambda x: x['sort_priority'])

# Kanal sayılarını hesapla
bein_spor_count = sum(1 for c in turkey_channels if c['sort_priority'][0] == 0)
other_spor_count = sum(1 for c in turkey_channels if c['sort_priority'][0] == 1)
general_count = sum(1 for c in turkey_channels if c['sort_priority'][0] == 2)
total_count = len(turkey_channels)

print(f"Bein Spor kanalları: {bein_spor_count}")
print(f"Diğer Spor kanalları: {other_spor_count}")
print(f"Genel kanallar: {general_count}")

# M3U dosya içeriği oluştur
m3u_content = "#EXTM3U\n"

for channel in turkey_channels:
    m3u_content += f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}" tvg-name="{channel["name"]}" tvg-logo="{channel["logo"]}" group-title="Vavoo Tv" tvg-country="TR" tvg-language="{channel["language_code"]}", {channel["name"]}\n {channel["stream_url"]}\n'

# Dosyayı bulunduğu dizine kaydet
with open("vavoo.m3u", "w", encoding="utf-8") as f:
    f.write(m3u_content)

print(f"M3U listesi oluşturuldu: vavoo.m3u")
print("İşlem tamamlandı.")
