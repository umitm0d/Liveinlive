#!/bin/bash

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/runner/.local/bin"

REPO="${GITHUB_REPOSITORY}"
WORKER_URL="https://you.umitm0dlive.workers.dev"

mkdir -p playlist

echo ">>> playlist.m3u oluşturuluyor..."
echo "#EXTM3U" > playlist/playlist.m3u

cat link.json | jq -c '.[]' | while read -r i; do
    name=$(echo "$i" | jq -r '.name')
    target_url=$(echo "$i" | jq -r '.url')
    video_id=$(echo "$target_url" | grep -oP '(?<=/live/|[?&]v=)[a-zA-Z0-9_-]{11}' | head -1)

    echo ">>> $name ($video_id) ekleniyor..."

    echo "#EXTINF:-1,${name}" >> playlist/playlist.m3u
    echo "${WORKER_URL}/live/${video_id}" >> playlist/playlist.m3u
done

echo ">>> Tamamlandı."
