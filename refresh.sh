#!/bin/bash

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/runner/.local/bin"

REPO="${GITHUB_REPOSITORY}"
COOKIES_FILE="cookies.txt"

mkdir -p playlist
rm -f playlist/*.m3u8

echo ">>> Kanallar taranıyor..."

# Cookie'den SAPISID ve HSID değerlerini çek (auth için)
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

    # Video ID'yi URL'den çıkar
    video_id=$(echo "$target_url" | grep -oP '(?<=/live/|[?&]v=)[a-zA-Z0-9_-]{11}' | head -1)

    echo ">>> $name ($video_id) işleniyor..."

    # YouTube sayfasından hlsManifestUrl çek
    raw_manifest=$(curl -s --max-time 30 \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36" \
        -H "Accept-Language: tr-TR,tr;q=0.9" \
        -H "Cookie: $COOKIE_STR" \
        "https://www.youtube.com/watch?v=${video_id}" \
        | grep -o '"hlsManifestUrl":"[^"]*"' \
        | head -1 \
        | sed 's/"hlsManifestUrl":"//;s/"$//' \
        | sed 's/\\u0026/\&/g' \
        | tr -d '\r\n')

    echo "   [DEBUG] manifest: $raw_manifest"

    if [ -n "$raw_manifest" ] && [[ "$raw_manifest" == http* ]]; then
        cat <<EOF > "playlist/${name}.m3u8"
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720
$raw_manifest
EOF
        echo "   [OK] $name yazıldı."
    else
        echo "   [!] $name için HLS URL bulunamadı."
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
