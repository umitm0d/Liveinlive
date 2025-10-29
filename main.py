import streamlink
import sys
import os 
import json
import traceback

def info_to_text(stream_info, url):
    text = '#EXT-X-STREAM-INF:'
    if stream_info.program_id:
        text = text + 'PROGRAM-ID=' + str(stream_info.program_id) + ','
    if stream_info.bandwidth:
        text = text + 'BANDWIDTH=' + str(stream_info.bandwidth) + ','
    if stream_info.codecs:
        text = text + 'CODECS="'
        codecs = stream_info.codecs
        for i in range(0, len(codecs)):
            text = text + codecs[i]
            if len(codecs) - 1 != i:
                text = text + ','
        text = text + '",'
    if stream_info.resolution and stream_info.resolution.width:
        text = text + 'RESOLUTION=' + str(stream_info.resolution.width) + 'x' + str(stream_info.resolution.height) 

    text = text + "\n" + url + "\n"
    return text

def create_master_playlist(playlists, multivariant):
    """Ana master playlist oluştur"""
    master_text = '#EXTM3U\n'
    
    if multivariant.version:
        master_text += f'#EXT-X-VERSION:{multivariant.version}\n'
    
    # Çözünürlüğe göre sırala (yüksekten düşüğe)
    sorted_playlists = sorted(
        [p for p in playlists if hasattr(p.stream_info, 'resolution') and p.stream_info.resolution],
        key=lambda x: (x.stream_info.resolution.height if x.stream_info.resolution else 0, 
                      x.stream_info.bandwidth if x.stream_info.bandwidth else 0),
        reverse=True
    )
    
    for playlist in sorted_playlists:
        if (hasattr(playlist.stream_info, 'video') and 
            playlist.stream_info.video != "audio_only" and
            playlist.stream_info.resolution):
            master_text += info_to_text(playlist.stream_info, playlist.uri)
    
    return master_text

def create_best_playlist(playlists, multivariant):
    """En iyi kalite için playlist oluştur"""
    best_text = '#EXTM3U\n'
    
    if multivariant.version:
        best_text += f'#EXT-X-VERSION:{multivariant.version}\n'
    
    # En yüksek çözünürlüklü stream'i bul
    best_playlist = None
    max_resolution = 0
    
    for playlist in playlists:
        if (hasattr(playlist.stream_info, 'video') and 
            playlist.stream_info.video != "audio_only" and
            playlist.stream_info.resolution):
            resolution = playlist.stream_info.resolution.height
            if resolution > max_resolution:
                max_resolution = resolution
                best_playlist = playlist
    
    if best_playlist:
        best_text += info_to_text(best_playlist.stream_info, best_playlist.uri)
    
    return best_text

def create_final_m3u_playlist(processed_channels, repo_base_url, master_folder_path):
    """Tüm kanalları içeren tek bir M3U playlist oluştur"""
    m3u_content = '#EXTM3U\n'
    
    for channel in processed_channels:
        slug = channel["slug"]
        name = channel["name"]
        
        # M3U8 dosyasının URL'sini oluştur
        m3u8_url = f"{repo_base_url}{master_folder_path}/{slug}.m3u8"
        
        # M3U formatında kanal bilgisi
        m3u_content += f'#EXTINF:-1 tvg-id="{slug}" tvg-name="{name}",{name}\n'
        m3u_content += f'{m3u8_url}\n'
    
    return m3u_content

def main():
    print("=== Starting stream processing ===")
    
    # Loading config file
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    print(f"Loading config from: {config_file}")
    
    try:
        with open(config_file, "r", encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ ERROR loading config file: {e}")
        sys.exit(1)

    # Getting output options and creating folders
    folder_name = config["output"]["folder"]
    best_folder_name = config["output"]["bestFolder"]
    master_folder_name = config["output"]["masterFolder"]
    current_dir = os.getcwd()
    root_folder = os.path.join(current_dir, folder_name)
    best_folder = os.path.join(root_folder, best_folder_name)
    master_folder_path = os.path.join(root_folder, master_folder_name) if master_folder_name else root_folder
    
    print(f"Creating folders:")
    print(f"  Root: {root_folder}")
    print(f"  Best: {best_folder}")
    print(f"  Master: {master_folder_path}")
    
    os.makedirs(best_folder, exist_ok=True)
    os.makedirs(master_folder_path, exist_ok=True)

    channels = config["channels"]
    print(f"\n=== Processing {len(channels)} channels ===\n")
    
    success_count = 0
    fail_count = 0
    processed_channels = []

    for idx, channel in enumerate(channels, 1):
        slug = channel.get("slug", "unknown")
        url = channel.get("url", "")
        name = channel.get("name", slug)
        
        print(f"[{idx}/{len(channels)}] Processing: {name}")
        print(f"  URL: {url}")
        
        master_file_path = os.path.join(master_folder_path, f"{slug}.m3u8")
        best_file_path = os.path.join(best_folder, f"{slug}.m3u8")
        
        try:
            # Get streams and playlists
            streams = streamlink.streams(url)
            
            if not streams:
                print(f"  ⚠️  No streams found for {slug}")
                fail_count += 1
                continue
                
            if 'best' not in streams:
                print(f"  ⚠️  No 'best' stream found for {slug}")
                print(f"  Available streams: {list(streams.keys())}")
                fail_count += 1
                continue
            
            best_stream = streams['best']
            if not hasattr(best_stream, 'multivariant') or not best_stream.multivariant.playlists:
                print(f"  ⚠️  No multivariant playlists found for {slug}")
                fail_count += 1
                continue
            
            playlists = best_stream.multivariant.playlists

            # Create playlists
            master_text = create_master_playlist(playlists, best_stream.multivariant)
            best_text = create_best_playlist(playlists, best_stream.multivariant)

            # HTTPS -> HTTP for cinergroup plugin
            if url.startswith("http://"):
                try:
                    plugin_name, plugin_type, given_url = streamlink.session.Streamlink().resolve_url(url)
                    if plugin_name == "cinergroup":
                        master_text = master_text.replace("https://", "http://")
                        best_text = best_text.replace("https://", "http://")
                except:
                    pass

            # File operations
            if master_text.strip() and len(master_text.strip()) > len('#EXTM3U\n'):
                with open(master_file_path, "w+", encoding='utf-8') as master_file:
                    master_file.write(master_text)

                with open(best_file_path, "w+", encoding='utf-8') as best_file:
                    best_file.write(best_text)
                
                print(f"  ✅ Success - Files created")
                success_count += 1
                processed_channels.append({
                    "slug": slug,
                    "name": name,
                    "master_file": f"{slug}.m3u8"
                })
            else:
                print(f"  ⚠️  No valid content generated for {slug}")
                # Clean up any existing files
                for file_path in [master_file_path, best_file_path]:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                fail_count += 1
                
        except Exception as e:
            print(f"  ❌ ERROR processing {slug}: {str(e)}")
            print(f"  {traceback.format_exc()}")
            
            # Clean up on error
            for file_path in [master_file_path, best_file_path]:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            fail_count += 1
    
    # Create final M3U playlist with all channels
    if processed_channels:
        print(f"\n=== Creating final M3U playlist ===")
        
        # GitHub raw URL base - BURAYI KENDİ BİLGİLERİNİZLE DEĞİŞTİRİN
        github_username = "umitm0d"
        repo_name = "Liveinlive"
        branch_name = "main"
        
        repo_base_url = f"https://raw.githubusercontent.com/{github_username}/{repo_name}/{branch_name}/"
        
        # Master folder path for URLs
        master_url_path = f"{folder_name}"
        if master_folder_name:
            master_url_path += f"/{master_folder_name}"
        
        final_m3u_content = create_final_m3u_playlist(processed_channels, repo_base_url, master_url_path)
        
        # Final M3U dosyasını ana dizine kaydet
        final_m3u_path = os.path.join(current_dir, "playlist.m3u")
        with open(final_m3u_path, "w+", encoding='utf-8') as f:
            f.write(final_m3u_content)
        
        print(f"✅ Final playlist created: {final_m3u_path}")
        
        # Ayrıca streams klasörüne de kopyala
        final_m3u_in_streams = os.path.join(root_folder, "playlist.m3u")
        with open(final_m3u_in_streams, "w+", encoding='utf-8') as f:
            f.write(final_m3u_content)
        
        print(f"✅ Final playlist copied to: {final_m3u_in_streams}")
        
        # Show example URLs
        print(f"\n📋 Example M3U8 URLs in final playlist:")
        for channel in processed_channels[:3]:  # Show first 3 as examples
            slug = channel["slug"]
            m3u8_url = f"{repo_base_url}{master_url_path}/{slug}.m3u8"
            print(f"  {channel['name']}: {m3u8_url}")
        
        print(f"\n🔗 Your final M3U playlist URL will be:")
        final_playlist_url = f"{repo_base_url}playlist.m3u"
        print(f"  {final_playlist_url}")
    
    print(f"\n=== Summary ===")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"Total: {len(channels)}")

if __name__=="__main__": 
    main()
