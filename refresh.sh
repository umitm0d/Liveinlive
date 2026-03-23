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

    # hls_variant linkini al
    variant_url=$(echo "$page" \
        | grep -o '"hlsManifestUrl":"[^"]*"' \
        | head -1 \
        | sed 's/"hlsManifestUrl":"//;s/"$//' \
        | sed 's/\\u0026/\&/g' \
        | tr -d '\r\n')

    echo "   [VARIANT] ${variant_url:0:80}..."

    if [ -z "$variant_url" ]; then
        echo "   [!] $name için variant URL bulunamadı."
        continue
    fi

    # hls_variant içeriğini çek → hls_playlist linklerini listele → en iyi kaliteyi al
    playlist_url=$(curl -s --max-time 15 \
        -H "User-Agent: $UA" \
        "$variant_url" \
        | grep "^https://manifest.googlevideo.com/api/manifest/hls_playlist" \
        | head -1 \
        | tr -d '\r\n')

    echo "   [PLAYLIST] ${playlist_url:0:80}..."

    if [ -n "$playlist_url" ] && [[ "$playlist_url" == http* ]]; then
        printf '#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720\n%s\n' "$playlist_url" > "playlist/${name}.m3u8"
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
