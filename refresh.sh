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

    # YouTube sayfasını çek, googlevideo manifest linkini bul
    raw_manifest=$(curl -s --max-time 30 \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
        "$target_url" \
        | grep -o "https://manifest.googlevideo.com[^\"'\\\\]*" \
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

    if grep -q "googlevideo" "$file"; then
        echo "#EXTINF:-1,$fname" >> playlist/playlist.m3u
        echo "https://raw.githubusercontent.com/${REPO}/main/playlist/${fname}.m3u8?t=$(date +%s)" >> playlist/playlist.m3u
    fi
done

echo ">>> Tamamlandı."
