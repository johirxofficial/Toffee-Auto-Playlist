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

# Security check – prevent running without the secret
if not CONFIG.get("token") or len(CONFIG["token"]) < 100:
    print("❌ CRITICAL ERROR: TOFFEE_BEARER_TOKEN secret is missing or invalid!")
    print("   → Repository Settings → Secrets and variables → Actions")
    exit(1)


def get_dhaka_time():
    """Return current time in Asia/Dhaka timezone"""
    tz = pytz.timezone('Asia/Dhaka')
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')


def get_master_cookie():
    """Request fresh Edge-Cache-Cookie from Toffee entitlement API"""
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

        set_cookie_header = response.headers.get('Set-Cookie', '')
        match = re.search(r'Edge-Cache-Cookie=([^;]+)', set_cookie_header)

        if match:
            print(f"[{get_dhaka_time()}] ✅ Fresh Master Cookie generated")
            return f"Edge-Cache-Cookie={match.group(1)}"

        print(f"[{get_dhaka_time()}] ⚠️  Edge-Cache-Cookie not found in Set-Cookie header")
        return None

    except requests.exceptions.RequestException as e:
        print(f"[{get_dhaka_time()}] ❌ API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"    Status: {e.response.status_code}")
            print(f"    Response preview: {e.response.text[:400]}")
        return None


def update_playlist():
    print(f"[{get_dhaka_time()}] 🚀 Starting Toffee playlist updater...")

    cookie = get_master_cookie()
    if not cookie:
        print(f"[{get_dhaka_time()}] ❌ Could not obtain valid cookie → aborting")
        return

    # Load existing channels
    if not os.path.exists(CONFIG['json_file']):
        print(f"[{get_dhaka_time()}] ❌ File not found: {CONFIG['json_file']}")
        return

    with open(CONFIG['json_file'], 'r', encoding='utf-8') as f:
        data = json.load(f)

    channels = data if isinstance(data, list) else data.get('channels', [])

    # ────────────────────────────────────────────────
    #   INTRO / CREDIT CHANNEL – strong duplicate removal
    # ────────────────────────────────────────────────
    intro_channel = {
        "id": "intro",
        "category_name": "Intro",
        "name": "credit: johirxofficial",
        "logo": "https://johirxofficial.github.io/logos/IMG_20260221_143301.png",
        "link": "https://cdn.pixabay.com/video/2023/11/11/188742-883619742_large.mp4"
        # No cookie field here → intro does not need Toffee cookie
    }

    # Remove ALL previous intro-like entries (multiple safety checks)
    channels = [
        ch for ch in channels
        if not (
            ch.get("id") == "intro"
            or ch.get("name") == "credit: johirxofficial"
            or ch.get("link") == "https://cdn.pixabay.com/video/2023/11/11/188742-883619742_large.mp4"
        )
    ]

    # Insert intro at the very beginning
    channels.insert(0, intro_channel)

    # Apply fresh cookie to all real channels (skip intro)
    updated_count = 0
    for ch in channels:
        if ch.get('link') and ch.get("id") != "intro":
            ch['cookie'] = cookie
            updated_count += 1

    # Prepare final structure
    if isinstance(data, dict):
        data['last_updated'] = get_dhaka_time()
        data['channels'] = channels
        final_data = data
    else:
        final_data = channels

    # Save updated JSON
    with open(CONFIG['json_file'], 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)

    print(f"[{get_dhaka_time()}] 📊 JSON updated  ({updated_count} channels + 1 intro)")

    # ────────────────────────────────────────────────
    #   Generate M3U playlist
    # ────────────────────────────────────────────────
    with open(CONFIG['m3u_file'], 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write('#EXT-X-SESSION-KEY:METHOD=AES-128,URI="fake"\n\n')

        for ch in channels:
            if not ch.get('link'):
                continue

            name  = ch.get('name',  'Unknown')
            group = ch.get('category_name', 'TV')
            logo  = ch.get('logo', '')
            tvid  = ch.get('id', '')

            f.write(f'#EXTINF:-1 group-title="{group}" tvg-id="{tvid}" tvg-logo="{logo}", {name}\n')
            f.write(f'#EXTVLCOPT:http-user-agent={CONFIG["user_agent"]}\n')

            # Only real channels get the cookie line
            if ch.get('cookie') and ch.get("id") != "intro":
                f.write(f'#EXTVLCOPT:http-cookie={ch["cookie"]}\n')

            f.write(f'{ch["link"]}\n\n')

    print(f"[{get_dhaka_time()}] 🎥 M3U playlist generated")
    print(f"[{get_dhaka_time()}] 🎉 Finished successfully")


if __name__ == "__main__":
    update_playlist()
