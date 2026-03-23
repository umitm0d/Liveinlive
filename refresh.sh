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

cat link.json | jq -c '.[]' | while read -r i; do
    name=$(echo "$i" | jq -r '.name')
    target_url=$(echo "$i" | jq -r '.url')
    video_id=$(echo "$target_url" | grep -oP '(?<=/live/|[?&]v=)[a-zA-Z0-9_-]{11}' | head -1)

    echo ">>> $name ($video_id) işleniyor..."

    page=$(curl -s --max-time 30 \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36" \
        -H "Accept-Language: tr-TR,tr;q=0.9" \
        -H "Cookie: $COOKIE_STR" \
        "https://www.youtube.com/watch?v=${video_id}")

    # Sayfada geçen tüm googlevideo linklerini göster
    echo "   [ALL LINKS]:"
    echo "$page" | grep -o 'https://manifest.googlevideo.com[^"\\]*' | head -5

    # hls_playlist linkini çek
    raw_manifest=$(echo "$page" \
        | grep -o 'https://manifest\.googlevideo\.com/api/manifest/hls_playlist/[^"\\]*' \
        | head -1 \
        | sed 's/\\u0026/\&/g;s/\\//g' \
        | tr -d '\r\n')

    # Bulamazsa hls_variant
    if [ -z "$raw_manifest" ]; then
        echo "   [!] hls_playlist bulunamadı, hls_variant deneniyor..."
        raw_manifest=$(echo "$page" \
            | grep -o '"hlsManifestUrl":"[^"]*"' \
            | head -1 \
            | sed 's/"hlsManifestUrl":"//;s/"$//' \
            | sed 's/\\u0026/\&/g' \
            | tr -d '\r\n')
    fi

    echo "   [RESULT] $raw_manifest" | head -c 200
    echo ""

    if [ -n "$raw_manifest" ] && [[ "$raw_manifest" == http* ]]; then
        printf '#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720\n%s\n' "$raw_manifest" > "playlist/${name}.m3u8"
        echo "   [OK] $name yazıldı."
    else
        echo "   [!] $name için URL alınamadı."
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
