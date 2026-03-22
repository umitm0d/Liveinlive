#!/bin/bash

# --- AYARLAR ---
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# GitHub repo bilgisi (Actions ortamında otomatik gelir)
REPO="${GITHUB_REPOSITORY}"   # örn: kullanici/repo-adi

# Playlist klasörünü hazırla
mkdir -p playlist
rm -f playlist/*.m3u8

echo ">>> Kanallar taranıyor..."

cat link.json | jq -c '.[]' | while read -r i; do
    name=$(echo "$i" | jq -r '.name')
    target_url=$(echo "$i" | jq -r '.url')

    echo ">>> $name işleniyor..."

    # yt-dlp ile HLS manifest URL'yi çek
    raw_manifest=$(yt-dlp \
        --no-warnings \
        --get-url \
        -f "best[protocol=m3u8_native]/best" \
        "$target_url" 2>/dev/null \
        | head -n 1 \
        | tr -d '\r\n')

    if [ -n "$raw_manifest" ] && [[ "$raw_manifest" == http* ]]; then
        cat <<EOF > "playlist/${name}.m3u8"
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=1280x720
$raw_manifest
EOF
        echo "   [OK] $name yazıldı."
    else
        echo "   [!] $name için manifest bulunamadı, atlanıyor."
    fi

    sleep 1
done

# --- ANA PLAYLIST OLUŞTUR ---
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
