#!/bin/bash

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/runner/.local/bin"

REPO="${GITHUB_REPOSITORY}"

mkdir -p playlist
rm -f playlist/*.m3u8

echo ">>> Kanallar taranıyor..."

cat link.json | jq -c '.[]' | while read -r i; do
    name=$(echo "$i" | jq -r '.name')
    target_url=$(echo "$i" | jq -r '.url')

    echo ">>> $name işleniyor..."

    # yt-dlp ile tüm format URL'lerini al, ilk http olanı seç
    raw_manifest=$(yt-dlp \
        --no-warnings \
        --get-url \
        -f "best" \
        "$target_url" 2>&1)

    echo "   [DEBUG] yt-dlp çıktısı: $raw_manifest"

    raw_manifest=$(echo "$raw_manifest" | grep "^http" | head -n 1 | tr -d '\r\n')

    if [ -n "$raw_manifest" ]; then
        cat <<EOF > "playlist/${name}.m3u8"
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720
$raw_manifest
EOF
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
