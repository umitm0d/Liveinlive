#!/bin/bash

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/runner/.local/bin"

REPO="${GITHUB_REPOSITORY}"
COOKIES_FILE="cookies.txt"

mkdir -p playlist
rm -f playlist/*.m3u8

echo ">>> Kanallar taranıyor..."

get_cookie_value() {
    grep -P "\t$1\t" "$COOKIES_FILE" 2>/dev/null | tail -1 | awk '{print $NF}'
}

SAPISID=$(get_cookie_value "SAPISID")
HSID=$(get_cookie_value "HSID")
SID=$(get_cookie_value "SID")
SSID=$(get_cookie_value "SSID")
APISID=$(get_cookie_value "APISID")

COOKIE_STR="SAPISID=${SAPISID}; HSID=${HSID}; SID=${SID}; SSID=${SSID}; APISID=${APISID}"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"

cat link.json | jq -c '.[]' | while read -r i; do
    name=$(echo "$i" | jq -r '.name')
    target_url=$(echo "$i" | jq -r '.url')
    video_id=$(echo "$target_url" | grep -oP '(?<=/live/|[?&]v=)[a-zA-Z0-9_-]{11}' | head -1)

    echo ">>> $name ($video_id) işleniyor..."

    page=$(curl -s --max-time 30 \
        -H "User-Agent: $UA" \
        -H "Accept-Language: tr-TR,tr;q=0.9" \
        -H "Cookie: $COOKIE_STR" \
        "https://www.youtube.com/watch?v=${video_id}")

    variant_url=$(echo "$page" \
        | grep -o '"hlsManifestUrl":"[^"]*"' \
        | head -1 \
        | sed 's/"hlsManifestUrl":"//;s/"$//' \
        | sed 's/\\u0026/\&/g' \
        | tr -d '\r\n')

    if [ -z "$variant_url" ]; then
        echo "   [!] $name için variant URL bulunamadı."
        sleep 2
        continue
    fi

    # hls_variant içeriğini çek, en yüksek itag'li hls_playlist linkini al
    variant_content=$(curl -s --max-time 15 -H "User-Agent: $UA" "$variant_url")

    # itag değerlerine göre kalite sırası: 96=1080p, 95=720p, 94=480p, 93=360p, 92=240p, 91=144p
    playlist_url=""
    for itag in 96 95 94 93 92 91; do
        playlist_url=$(echo "$variant_content" \
            | grep "hls_playlist" \
            | grep "itag/${itag}/" \
            | head -1 \
            | tr -d '\r\n')
        if [ -n "$playlist_url" ]; then
            echo "   [QUALITY] itag=${itag} seçildi"
            break
        fi
    done

    # Bulamazsa ilk hls_playlist'i al
    if [ -z "$playlist_url" ]; then
        playlist_url=$(echo "$variant_content" \
            | grep "^https://manifest.googlevideo.com/api/manifest/hls_playlist" \
            | head -1 \
            | tr -d '\r\n')
    fi

    echo "   [PLAYLIST] ${playlist_url:0:80}..."

    if [ -n "$playlist_url" ] && [[ "$playlist_url" == http* ]]; then
        {
            echo "#EXTM3U"
            echo "#EXT-X-VERSION:3"
            echo "#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720"
            echo "$playlist_url"
        } > "playlist/${name}.m3u8"
        echo "   [OK] $name yazıldı."
    else
        echo "   [!] $name için hls_playlist alınamadı."
    fi

    sleep 2
done

echo ">>> playlist.m3u oluşturuluyor..."
echo "#EXTM3U" > playlist/playlist.m3u

for file in playlist/*.m3u8; do
    [ -s "$file" ] || continue
    fname=$(basename "$file" .m3u8)
    if grep -q "^http" "$file"; then
        echo "#EXTINF:-1,$fname" >> playlist/playlist.m3u
        echo "https://raw.githubusercontent.com/${REPO}/main/playlist/${fname}.m3u8?t=$(date +%s)" >> playlist/playlist.m3u
    fi
done

echo ">>> Tamamlandı."
