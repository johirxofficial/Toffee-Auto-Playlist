import json
import requests
import re
import os
from datetime import datetime
import pytz

# ========================= CONFIGURATION =========================
CONFIG = {
    "json_file": "toffee_playlist.json",
    "m3u_file": "toffee_playlist.m3u",
    "master_id": "5cwRnZUBtpl-Sbt7wWrN",      # Premium example: &TV HD
    "user_agent": "okhttp/4.11.0",
    "token": os.getenv("TOFFEE_BEARER_TOKEN"),
}

# Security Check - Prevent running without secret
if not CONFIG.get("token") or len(CONFIG["token"]) < 100:
    print("❌ CRITICAL ERROR: TOFFEE_BEARER_TOKEN secret is missing!")
    print("   Go to: Settings → Secrets and variables → Actions")
    exit(1)

def get_dhaka_time():
    """Return current time in Dhaka timezone"""
    tz = pytz.timezone('Asia/Dhaka')
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

def get_master_cookie():
    """Fetch fresh Edge-Cache-Cookie from Toffee API"""
    url = f"https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/web/playback/{CONFIG['master_id']}"
    
    headers = {
        "Authority": "entitlement-prod.services.toffeelive.com",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CONFIG['token']}",
        "User-Agent": CONFIG['user_agent'],
        "Origin": "https://toffeelive.com"
    }

    try:
        response = requests.post(url, json={}, headers=headers, timeout=15)
        response.raise_for_status()

        set_cookie = response.headers.get('Set-Cookie', '')
        match = re.search(r'Edge-Cache-Cookie=([^;]+)', set_cookie)

        if match:
            print(f"[{get_dhaka_time()}] ✅ Fresh Master Cookie Generated Successfully")
            return f"Edge-Cache-Cookie={match.group(1)}"
        else:
            print(f"[{get_dhaka_time()}] ⚠️ Cookie not found in response headers")
            return None

    except Exception as e:
        print(f"[{get_dhaka_time()}] ❌ API Request Failed: {e}")
        return None

def update_playlist():
    print(f"[{get_dhaka_time()}] 🚀 Starting Toffee Auto Updater...")

    # Get fresh cookie
    cookie = get_master_cookie()
    if not cookie:
        print(f"[{get_dhaka_time()}] ❌ Critical Error: Could not generate cookie. Aborting.")
        return

    # Load channels from JSON
    if not os.path.exists(CONFIG['json_file']):
        print(f"[{get_dhaka_time()}] ❌ {CONFIG['json_file']} not found!")
        return

    with open(CONFIG['json_file'], 'r', encoding='utf-8') as f:
        data = json.load(f)

    channels = data if isinstance(data, list) else data.get('channels', [])

    # Add Intro/Credit Channel at the very top
    intro_channel = {
        "id": "intro",
        "category_name": "Intro",
        "name": "intro",
        "logo": "https://assets-prod.services.toffeelive.com/f_png,w_300,q_85/5cwRnZUBtpl-Sbt7wWrN/posters/08617b27-2af1-4035-bcc3-d054ce42ca4b.png",
        "link": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/1080/Big_Buck_Bunny_1080_10s_5MB.mp4"
        # own credit/intro MP4
    }

    # Prevent duplicate intro
    channels = [ch for ch in channels if ch.get("name") != "intro"]
    channels.insert(0, intro_channel)

    # Inject cookie into all real channels (except intro)
    updated_count = 0
    for ch in channels:
        if ch.get('link') and ch.get("name") != "intro":
            ch['cookie'] = cookie
            updated_count += 1

    # Save updated JSON
    if isinstance(data, dict):
        data['last_updated'] = get_dhaka_time()
        data['channels'] = channels
        final_data = data
    else:
        final_data = channels

    with open(CONFIG['json_file'], 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)

    print(f"[{get_dhaka_time()}] 📊 JSON Updated ({updated_count} channels + Intro)")

    # Generate M3U Playlist
    with open(CONFIG['m3u_file'], 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write('#EXT-X-SESSION-KEY:METHOD=AES-128,URI="fake"\n\n')
        
        for ch in channels:
            if not ch.get('link'):
                continue
                
            name = ch.get('name', 'Unknown')
            group = ch.get('category_name', 'TV')
            logo = ch.get('logo', '')
            tvid = ch.get('id', '')
            
            f.write(f'#EXTINF:-1 group-title="{group}" tvg-id="{tvid}" tvg-logo="{logo}", {name}\n')
            f.write(f'#EXTVLCOPT:http-user-agent={CONFIG["user_agent"]}\n')
            
            if ch.get('cookie') and ch.get("name") != "intro":
                f.write(f'#EXTVLCOPT:http-cookie={ch["cookie"]}\n')
            
            f.write(f'{ch["link"]}\n\n')

    print(f"[{get_dhaka_time()}] 🎥 M3U Playlist Generated Successfully")
    print(f"[{get_dhaka_time()}] 🎉 All Done! Intro channel added at the top.")

if __name__ == "__main__":
    update_playlist()
