import requests
import os
import sys
import time
import json
from datetime import datetime

# API KEY - ortam değişkeninden okunur, koda GÖMÜLMEZ.
# Yerelde çalıştırırken: export TMDB_API_KEY="senin_anahtarin"
# GitHub Actions'ta: repo Settings > Secrets and variables > Actions
#                     içine TMDB_API_KEY adında bir secret ekle.
API_KEY = os.environ.get("TMDB_API_KEY")
if not API_KEY:
    sys.exit(
        "HATA: TMDB_API_KEY ortam değişkeni bulunamadı.\n"
        "Yerelde çalıştırmak için: export TMDB_API_KEY=\"anahtarınız\"\n"
        "GitHub Actions kullanıyorsanız repo Settings > Secrets and "
        "variables > Actions bölümünden TMDB_API_KEY secret'ını ekleyin."
    )

# Tür ID eşlemeleri de ortam değişkeninden (JSON string) okunur, koda GÖMÜLMEZ.
# Beklenen format: {"28": "Aksiyon", "12": "Macera", ...}
# Yerelde: export MOVIE_GENRES_JSON='{"28":"Aksiyon","12":"Macera", ...}'
# GitHub Actions'ta: MOVIE_GENRES_JSON ve TV_GENRES_JSON adında iki ayrı
#                     secret ekleyin (değerleri aşağıdaki varsayılanlarla aynı olabilir,
#                     önemli olan bunların repoda düz metin olarak görünmemesi).
_DEFAULT_MOVIE_GENRES_HELP = (
    '{"28":"Aksiyon","12":"Macera","16":"Animasyon","35":"Komedi","80":"Suç",'
    '"99":"Belgesel","18":"Dram","10751":"Aile","14":"Fantastik","36":"Tarih",'
    '"27":"Korku","10402":"Müzik","9648":"Gizem","10749":"Romantik","878":"Bilim Kurgu",'
    '"53":"Gerilim","10752":"Savaş","37":"Western"}'
)
_DEFAULT_TV_GENRES_HELP = (
    '{"10759":"Aksiyon","16":"Animasyon","35":"Komedi","80":"Suç","99":"Belgesel",'
    '"18":"Dram","10751":"Aile","10762":"Çocuk","9648":"Gizem","10763":"Haber",'
    '"10764":"Reality","10765":"Bilim Kurgu","10766":"Pembe Dizi","10767":"Talk Show",'
    '"10768":"Savaş","37":"Western"}'
)


def _load_genre_map(env_var, help_json):
    raw = os.environ.get(env_var)
    if not raw:
        sys.exit(
            f"HATA: {env_var} ortam değişkeni bulunamadı.\n"
            f"Yerelde çalıştırmak için, örnek:\n"
            f"export {env_var}='{help_json}'\n"
            f"GitHub Actions kullanıyorsanız repo Settings > Secrets and "
            f"variables > Actions bölümünden {env_var} secret'ını ekleyin."
        )
    try:
        parsed = json.loads(raw)
        return {int(k): v for k, v in parsed.items()}
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        sys.exit(f"HATA: {env_var} geçerli bir JSON değil: {e}")


if not os.path.exists('filmler'):
    os.mkdir('filmler')

VIDMODY_URL = "https://vidmody.com/vs"

# Tür ID'leri ve Türkçe isimleri (Film - TMDB movie genre id'leri) — secret'tan okunur
MOVIE_GENRES = _load_genre_map("MOVIE_GENRES_JSON", _DEFAULT_MOVIE_GENRES_HELP)

# Tür ID'leri ve Türkçe isimleri (Dizi - TMDB tv genre id'leri, movie'den farklıdır) — secret'tan okunur
TV_GENRES = _load_genre_map("TV_GENRES_JSON", _DEFAULT_TV_GENRES_HELP)

GENRE_ICONS = {
    "Aksiyon": "💥", "Komedi": "😂", "Dram": "🎭", "Korku": "👻",
    "Bilim Kurgu": "🚀", "Romantik": "💕", "Macera": "🗺️", "Suç": "🔫",
    "Gerilim": "🔪", "Animasyon": "🐭", "Aile": "👨‍👩‍👧", "Fantastik": "🧙",
    "Tarih": "📜", "Savaş": "⚔️", "Çocuk": "🧒", "Reality": "📺",
    "Pembe Dizi": "🌹", "Talk Show": "🎙️", "Western": "🤠", "Belgesel": "🎥",
    "Gizem": "🕵️", "Müzik": "🎵", "Haber": "📰"
}

# ---------------------------------------------------------------------------
# Ortak yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def tmdb_get(path, params=None):
    """TMDB API'ye GET isteği atar, hata durumunda None döner."""
    base = f"https://api.themoviedb.org/3/{path}"
    p = {"api_key": API_KEY, "language": "tr"}
    if params:
        p.update(params)
    try:
        response = requests.get(base, params=p, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def get_genres(media_type, tmdb_id):
    """Film ya da dizi için tür bilgisini döner."""
    data = tmdb_get(f"{media_type}/{tmdb_id}")
    if not data:
        return {"genres": ["Diğer"], "mainGenre": "Diğer"}
    genre_names = [g["name"] for g in data.get("genres", [])]
    main_genre = genre_names[0] if genre_names else "Diğer"
    return {"genres": genre_names, "mainGenre": main_genre}


def get_imdb_id(media_type, tmdb_id):
    """Film ya da dizi için IMDb id'sini döner."""
    data = tmdb_get(f"{media_type}/{tmdb_id}/external_ids")
    if not data:
        return None
    return data.get("imdb_id")


def check_link(url):
    """Linkin gerçekten erişilebilir olup olmadığını kontrol eder.

    NOT: Bazı kaynak siteler 'içerik bulunamadı' durumunda da HTTP 200
    dönebilir. Bu kontrol yalnızca linkin sunucu tarafından erişilebilir
    olduğunu doğrular, içeriğin gerçekten mevcut olduğunu garanti etmez.
    """
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except Exception:
        return False


def build_poster(path):
    return f"https://image.tmdb.org/t/p/w500{path}" if path else ""


# ---------------------------------------------------------------------------
# Film tarama
# ---------------------------------------------------------------------------

def scrape_movies():
    """
    Filmleri tarar ve üç gruba ayırır:
      - Yeşilçam: original_language == 'tr' ve yıl < 1990
      - Türk filmleri: original_language == 'tr' ve yıl >= 1990 (veya bilinmiyor)
      - Yabancı dublaj filmler: original_language != 'tr'
        (vidmody linkinin TR dublaj sağladığı varsayımıyla; bu doğrulanmış
        bir 'dublaj var' bilgisi değil, kaynağın genel yayın politikasına
        dayanan bir varsayımdır.)
    """
    print("\n🎬 FİLMLER TARANIYOR (Yeşilçam + Türk + Yabancı Dublaj)...\n")

    yesilcam_movies = []
    turkish_movies = []
    foreign_movies = []
    processed_ids = set()

    def process_movie(movie, year_override=None):
        tmdb_id = movie["id"]
        if tmdb_id in processed_ids:
            return
        original_lang = movie.get("original_language", "")

        # 1990 öncesi filmleri atla (yalnızca yabancı dublaj tarafı için;
        # Türk filmlerinde tarih sınırı yok, çünkü 1990 öncesi olanlar Yeşilçam grubuna gider)
        release_date = movie.get("release_date", "")
        year_text = year_override
        is_yesilcam = False
        if year_text is None:
            if release_date:
                year_text = release_date.split("-")[0]
                if original_lang != "tr" and int(year_text) < 1990:
                    return
                if original_lang == "tr" and int(year_text) < 1990:
                    is_yesilcam = True
            else:
                year_text = "Bilinmiyor"

        imdb_id = get_imdb_id("movie", tmdb_id)
        if not imdb_id:
            return
        link = f"{VIDMODY_URL}/{imdb_id}"
        if not check_link(link):
            return

        genre_info = get_genres("movie", tmdb_id)
        entry = {
            "id": tmdb_id,
            "title": movie.get("title", ""),
            "year": year_text,
            "link": link,
            "poster": build_poster(movie.get("poster_path")),
            "rating": movie.get("vote_average", 0),
            "mainGenre": genre_info["mainGenre"],
            "allGenres": genre_info["genres"],
        }
        processed_ids.add(tmdb_id)

        if is_yesilcam:
            yesilcam_movies.append(entry)
            print(f"   🎞️ ✓ {entry['title']} ({year_text}) ⭐ {entry['rating']}")
        elif original_lang == "tr":
            turkish_movies.append(entry)
            print(f"   🇹🇷 ✓ {entry['title']} ({year_text}) ⭐ {entry['rating']}")
        else:
            foreign_movies.append(entry)
            print(f"   🌍 ✓ {entry['title']} ({year_text}) ⭐ {entry['rating']}")

        time.sleep(0.03)

    # 1. VİZYONDAKİ FİLMLER (her iki dilden de olabilir)
    print("🆕 Vizyondaki filmler taranıyor...")
    for page in range(1, 6):
        data = tmdb_get("movie/now_playing", {"page": page})
        if not data or not data.get("results"):
            break
        for movie in data["results"]:
            process_movie(movie, year_override="Vizyonda")

    # 2. TÜRK FİLMLERİ (1990 sonrası) — popülerliğe göre, dil filtresiyle
    print("\n🇹🇷 Türk filmleri taranıyor...")
    page = 1
    total_tr = 0
    while page <= 20:
        data = tmdb_get("discover/movie", {
            "with_original_language": "tr",
            "sort_by": "popularity.desc",
            "vote_count.gte": 10,
            "primary_release_date.gte": "1990-01-01",
            "page": page,
        })
        if not data or not data.get("results"):
            break
        for movie in data["results"]:
            before = len(turkish_movies)
            process_movie(movie)
            if len(turkish_movies) > before:
                total_tr += 1
        page += 1
    print(f"   Türk filmleri: {total_tr} film eklendi")

    # 2b. YEŞİLÇAM (1990 öncesi Türk filmleri) — yıla göre azalan sırayla,
    # düşük oy eşiğiyle (eski filmlerin TMDB'de az oyu olabilir)
    print("\n🎞️ Yeşilçam filmleri taranıyor...")
    page = 1
    total_yesilcam = 0
    while page <= 30:
        data = tmdb_get("discover/movie", {
            "with_original_language": "tr",
            "sort_by": "primary_release_date.desc",
            "vote_count.gte": 1,
            "primary_release_date.lte": "1989-12-31",
            "page": page,
        })
        if not data or not data.get("results"):
            break
        for movie in data["results"]:
            before = len(yesilcam_movies)
            process_movie(movie)
            if len(yesilcam_movies) > before:
                total_yesilcam += 1
        page += 1
    print(f"   Yeşilçam: {total_yesilcam} film eklendi")

    # 3. YABANCI FİLMLER (TÜRLERE GÖRE) — dublaj varsayımıyla
    for genre_id, genre_name in MOVIE_GENRES.items():
        print(f"\n🎭 {genre_name} (yabancı) filmleri taranıyor...")
        page = 1
        total_added = 0
        while page <= 10 and total_added < 150:
            data = tmdb_get("discover/movie", {
                "sort_by": "popularity.desc",
                "with_genres": genre_id,
                "vote_count.gte": 100,
                "without_original_language": "tr",
                "page": page,
            })
            if not data or not data.get("results"):
                break
            for movie in data["results"]:
                before = len(foreign_movies)
                process_movie(movie)
                if len(foreign_movies) > before:
                    total_added += 1
            page += 1
        print(f"   {genre_name}: {total_added} film eklendi")

    print(f"\n📊 Toplam: {len(yesilcam_movies)} Yeşilçam, {len(turkish_movies)} Türk filmi, "
          f"{len(foreign_movies)} yabancı dublaj film")
    return yesilcam_movies, turkish_movies, foreign_movies


# ---------------------------------------------------------------------------
# Dizi tarama
# ---------------------------------------------------------------------------

def scrape_series():
    """
    Dizileri tarar ve iki gruba ayırır:
      - Türk dizileri: original_language == 'tr'
      - Yabancı dublaj diziler: original_language != 'tr'

    NOT: vidmody.com'un dizi/bölüm URL yapısı doğrulanamadı. Bu fonksiyon
    her dizi için TEK BİR link üretir (dizinin ana IMDb id'sine dayalı,
    filmlerle aynı /vs/{imdb_id} formatında). Eğer vidmody dizilerde
    sezon/bölüm bazlı farklı bir URL yapısı kullanıyorsa (örn.
    /vs/{imdb_id}-{sezon}-{bolum}), bu linkler check_link() kontrolünden
    geçemeyecek ve otomatik olarak elenecektir. Doğru format elde
    edildiğinde bu fonksiyon kolayca güncellenebilir.
    """
    print("\n📺 DİZİLER TARANIYOR (Türk + Yabancı Dublaj)...\n")

    turkish_series = []
    foreign_series = []
    processed_ids = set()

    def process_show(show):
        tmdb_id = show["id"]
        if tmdb_id in processed_ids:
            return
        original_lang = show.get("original_language", "")

        first_air = show.get("first_air_date", "")
        year_text = first_air.split("-")[0] if first_air else "Bilinmiyor"
        if original_lang != "tr" and year_text != "Bilinmiyor" and int(year_text) < 1990:
            return

        imdb_id = get_imdb_id("tv", tmdb_id)
        if not imdb_id:
            return
        link = f"{VIDMODY_URL}/{imdb_id}"
        if not check_link(link):
            return

        genre_info = get_genres("tv", tmdb_id)
        entry = {
            "id": tmdb_id,
            "title": show.get("name", ""),
            "year": year_text,
            "link": link,
            "poster": build_poster(show.get("poster_path")),
            "rating": show.get("vote_average", 0),
            "mainGenre": genre_info["mainGenre"],
            "allGenres": genre_info["genres"],
        }
        processed_ids.add(tmdb_id)

        if original_lang == "tr":
            turkish_series.append(entry)
            print(f"   🇹🇷 ✓ {entry['title']} ({year_text}) ⭐ {entry['rating']}")
        else:
            foreign_series.append(entry)
            print(f"   🌍 ✓ {entry['title']} ({year_text}) ⭐ {entry['rating']}")

        time.sleep(0.03)

    # 1. TÜRK DİZİLERİ
    print("🇹🇷 Türk dizileri taranıyor...")
    page = 1
    total_tr = 0
    while page <= 20:
        data = tmdb_get("discover/tv", {
            "with_original_language": "tr",
            "sort_by": "popularity.desc",
            "vote_count.gte": 10,
            "page": page,
        })
        if not data or not data.get("results"):
            break
        for show in data["results"]:
            before = len(turkish_series)
            process_show(show)
            if len(turkish_series) > before:
                total_tr += 1
        page += 1
    print(f"   Türk dizileri: {total_tr} dizi eklendi")

    # 2. YABANCI DİZİLER (TÜRLERE GÖRE) — dublaj varsayımıyla
    for genre_id, genre_name in TV_GENRES.items():
        print(f"\n🎭 {genre_name} (yabancı) dizileri taranıyor...")
        page = 1
        total_added = 0
        while page <= 10 and total_added < 150:
            data = tmdb_get("discover/tv", {
                "sort_by": "popularity.desc",
                "with_genres": genre_id,
                "vote_count.gte": 50,
                "without_original_language": "tr",
                "page": page,
            })
            if not data or not data.get("results"):
                break
            for show in data["results"]:
                before = len(foreign_series)
                process_show(show)
                if len(foreign_series) > before:
                    total_added += 1
            page += 1
        print(f"   {genre_name}: {total_added} dizi eklendi")

    print(f"\n📊 Toplam: {len(turkish_series)} Türk dizisi, {len(foreign_series)} yabancı dublaj dizi")
    return turkish_series, foreign_series


# ---------------------------------------------------------------------------
# M3U oluşturma
# ---------------------------------------------------------------------------

def write_group(m3u_parts, items, group_title, group_prefix_icon="🎬", sort_by="rating"):
    """Tek bir gruba (örn. 'Türk Filmleri') ait M3U bloğunu türlere göre bölerek yazar.

    sort_by: 'rating' (varsayılan, puana göre azalan) veya 'year' (yıla göre azalan,
    Yeşilçam gibi eski filmlerin puanı genelde eksik/düşük olduğu için).
    """
    if not items:
        return

    by_genre = {}
    for item in items:
        by_genre.setdefault(item["mainGenre"], []).append(item)

    sorted_genres = sorted(by_genre.keys(), key=lambda g: len(by_genre[g]), reverse=True)

    for genre in sorted_genres:
        genre_items = by_genre[genre]
        if sort_by == "year":
            def year_key(x):
                try:
                    return int(x["year"])
                except (ValueError, TypeError):
                    return 0
            genre_items.sort(key=year_key, reverse=True)
        else:
            genre_items.sort(key=lambda x: x["rating"], reverse=True)

        icon = GENRE_ICONS.get(genre, group_prefix_icon)
        full_group = f"{group_title} - {genre}"
        m3u_parts.append(f"# {icon} {full_group} ({len(genre_items)} adet)\n")

        for it in genre_items:
            year_info = f" ({it['year']})" if it["year"] not in ("Bilinmiyor",) else ""
            m3u_parts.append(
                f'#EXTINF:-1 group-title="{full_group}" tvg-logo="{it["poster"]}", '
                f'{it["title"]}{year_info} ⭐ {it["rating"]}\n'
            )
            m3u_parts.append(f"{it['link']}\n")
        m3u_parts.append("\n")


def build_m3u(yesilcam_movies, turkish_movies, foreign_movies, turkish_series, foreign_series):
    total = (len(yesilcam_movies) + len(turkish_movies) + len(foreign_movies)
             + len(turkish_series) + len(foreign_series))

    parts = []
    parts.append("#EXTM3U\n")
    parts.append("# Film & Dizi Arşivi - Türk ve Türkçe Dublaj İçerikler\n")
    parts.append(f"# Oluşturma: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
    parts.append(f"# Toplam: {total} içerik "
                  f"({len(yesilcam_movies)} Yeşilçam, {len(turkish_movies)} Türk film, "
                  f"{len(foreign_movies)} yabancı dublaj film, "
                  f"{len(turkish_series)} Türk dizi, {len(foreign_series)} yabancı dublaj dizi)\n")
    parts.append("# ⭐ Rating: IMDb/TMDB puanı\n\n")

    # Vizyondaki filmler ayrı bir bölüm olarak en üstte (hem Türk hem yabancı içinden)
    vizyon = [m for m in (turkish_movies + foreign_movies) if m["year"] == "Vizyonda"]
    if vizyon:
        vizyon.sort(key=lambda x: x["rating"], reverse=True)
        parts.append(f"# 🆕 VİZYONDAKİLER ({len(vizyon)} adet)\n")
        for m in vizyon:
            parts.append(
                f'#EXTINF:-1 group-title="Vizyondakiler" tvg-logo="{m["poster"]}", '
                f'{m["title"]} ⭐ {m["rating"]}\n'
            )
            parts.append(f"{m['link']}\n")
        parts.append("\n")

    non_vizyon_tr_movies = [m for m in turkish_movies if m["year"] != "Vizyonda"]
    non_vizyon_foreign_movies = [m for m in foreign_movies if m["year"] != "Vizyonda"]

    write_group(parts, yesilcam_movies, "Yeşilçam", "🎞️", sort_by="year")
    write_group(parts, non_vizyon_tr_movies, "Türk Filmleri", "🇹🇷")
    write_group(parts, non_vizyon_foreign_movies, "Yabancı Dublaj Filmler", "🌍")
    write_group(parts, turkish_series, "Türk Dizileri", "🇹🇷")
    write_group(parts, foreign_series, "Yabancı Dublaj Diziler", "🌍")

    with open("filmler/films.m3u", "w", encoding="utf-8") as f:
        f.write("".join(parts))

    print("\n✅ TAMAMLANDI!")
    print(f"📊 Toplam içerik: {total}")
    print(f"   🎞️ Yeşilçam: {len(yesilcam_movies)}")
    print(f"   🇹🇷 Türk film: {len(turkish_movies)}")
    print(f"   🌍 Yabancı dublaj film: {len(foreign_movies)}")
    print(f"   🇹🇷 Türk dizi: {len(turkish_series)}")
    print(f"   🌍 Yabancı dublaj dizi: {len(foreign_series)}")
    print("💾 Kaydedildi: filmler/films.m3u")


def scrape():
    yesilcam_movies, turkish_movies, foreign_movies = scrape_movies()
    turkish_series, foreign_series = scrape_series()
    build_m3u(yesilcam_movies, turkish_movies, foreign_movies, turkish_series, foreign_series)


if __name__ == "__main__":
    scrape()
