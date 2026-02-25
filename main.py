import json
import requests
import re
import os
from datetime import datetime
import pytz


# ────────────────────────────────────────────────
#  CONFIGURATION
# ────────────────────────────────────────────────
CONFIG = {
    "json_file": "toffee_playlist.json",
    "m3u_file": "toffee_playlist.m3u",
    "master_channel_id": "5cwRnZUBtpl-Sbt7wWrN",   # used only to get cookie
    "user_agent": "okhttp/4.11.0",
    "token": os.getenv("TOFFEE_BEARER_TOKEN"),
}


# Security guardrail
if not CONFIG.get("token") or len(CONFIG["token"]) < 80:
    print("❌ Missing or invalid TOFFEE_BEARER_TOKEN environment variable")
    exit(1)


def now_dhaka():
    return datetime.now(pytz.timezone('Asia/Dhaka')).strftime('%Y-%m-%d %H:%M:%S')


def fetch_fresh_cookie():
    url = f"https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/web/playback/{CONFIG['master_channel_id']}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CONFIG['token']}",
        "User-Agent": CONFIG['user_agent'],
        "Origin": "https://toffeelive.com"
    }

    try:
        r = requests.post(url, json={}, headers=headers, timeout=12)
        r.raise_for_status()

        cookie_str = re.search(r'Edge-Cache-Cookie=([^;]+)', r.headers.get('Set-Cookie', ''))
        if cookie_str:
            print(f"[{now_dhaka()}]   Cookie refreshed")
            return f"Edge-Cache-Cookie={cookie_str.group(1)}"

        print(f"[{now_dhaka()}]   No Edge-Cache-Cookie in response")
        return None

    except Exception as e:
        print(f"[{now_dhaka()}]   Cookie fetch failed → {e}")
        return None


def main():
    print(f"[{now_dhaka()}]   Starting update")

    cookie = fetch_fresh_cookie()
    if not cookie:
        print(f"[{now_dhaka()}]   Cannot proceed without cookie")
        return

    path = CONFIG["json_file"]
    if not os.path.isfile(path):
        print(f"[{now_dhaka()}]   Missing file: {path}")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Normalize to list of channels
    channels = data if isinstance(data, list) else data.get("channels", [])

    # ────────────────────────────────────────────────
    #   Intro / credit handling – ID is fixed
    # ────────────────────────────────────────────────
    INTRO_ID = "intro"   # THIS IS THE ONLY FIXED VALUE

    # Remove any previous entry with the same ID
    channels = [ch for ch in channels if ch.get("id") != INTRO_ID]

    # You can change name / logo / link here anytime – only id stays fixed
    intro_entry = {
        "id": INTRO_ID,
        "category_name": "Intro",
        "name": "credit: johirxofficial",                           # ← এখানে যা খুশি লিখতে পারেন
        "logo": "https://johirxofficial.github.io/logos/IMG_20260221_143301.png",  # ← এখানেও পরিবর্তন সম্ভব
        "link": "https://cdn.pixabay.com/video/2023/11/11/188742-883619742_large.mp4"
    }

    # Insert at position 0
    channels.insert(0, intro_entry)

    # ────────────────────────────────────────────────
    #   Update cookie on all real channels
    # ────────────────────────────────────────────────
    updated_count = 0
    for ch in channels:
        if ch.get("id") != INTRO_ID and ch.get("link"):
            ch["cookie"] = cookie
            updated_count += 1

    # ────────────────────────────────────────────────
    #   Save back (preserve original structure if it was dict)
    # ────────────────────────────────────────────────
    if isinstance(data, dict):
        data["last_updated"] = now_dhaka()
        data["channels"] = channels
        to_save = data
    else:
        to_save = channels

    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_save, f, indent=2, ensure_ascii=False)

    print(f"[{now_dhaka()}]   JSON updated ({updated_count} channels + intro)")

    # ────────────────────────────────────────────────
    #   Generate M3U
    # ────────────────────────────────────────────────
    m3u_path = CONFIG["m3u_file"]
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write('#EXT-X-SESSION-KEY:METHOD=AES-128,URI="fake"\n\n')

        for ch in channels:
            if not ch.get("link"):
                continue

            name  = ch.get("name",  "Unknown")
            group = ch.get("category_name", "TV")
            logo  = ch.get("logo", "")
            tvid  = ch.get("id", "")

            f.write(f'#EXTINF:-1 group-title="{group}" tvg-id="{tvid}" tvg-logo="{logo}", {name}\n')
            f.write(f'#EXTVLCOPT:http-user-agent={CONFIG["user_agent"]}\n')

            # intro channel never gets cookie
            if ch.get("id") != INTRO_ID and ch.get("cookie"):
                f.write(f'#EXTVLCOPT:http-cookie={ch["cookie"]}\n')

            f.write(f'{ch["link"]}\n\n')

    print(f"[{now_dhaka()}]  🎥 M3U generated → {m3u_path}")
    print(f"[{now_dhaka()}]  ✅ Done")


if __name__ == "__main__":
    main()
