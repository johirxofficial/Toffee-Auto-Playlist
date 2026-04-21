import json
import requests
import re
import os
from datetime import datetime
import pytz

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
CONFIG = {
    "json_file": "toffee_playlist.json",
    "m3u_file": "toffee_playlist.m3u",

    # use working channel id
    "master_channel_id": "LnlKhJkBcqxnFHJBU8GM",

    # use browser user-agent (important)
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",

    "token": os.getenv("TOFFEE_BEARER_TOKEN"),
}


# ────────────────────────────────────────────────
# TOKEN CHECK
# ────────────────────────────────────────────────
if not CONFIG["token"]:
    print("❌ Missing TOFFEE_BEARER_TOKEN")
    exit(1)


# ────────────────────────────────────────────────
# TIME
# ────────────────────────────────────────────────
def now_dhaka():
    return datetime.now(
        pytz.timezone("Asia/Dhaka")
    ).strftime("%Y-%m-%d %H:%M:%S")


# ────────────────────────────────────────────────
# SESSION HEADERS
# ────────────────────────────────────────────────
def build_headers():
    return {
        "accept": "*/*",
        "accept-language": "en-BD,en;q=0.9",
        "authorization": f"Bearer {CONFIG['token']}",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": "https://toffeelive.com",
        "pragma": "no-cache",
        "referer": "https://toffeelive.com/",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": CONFIG["user_agent"],
    }


# ────────────────────────────────────────────────
# GET COOKIE
# ────────────────────────────────────────────────
def fetch_fresh_cookie():
    url = f"https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/web/playback/{CONFIG['master_channel_id']}"

    try:
        r = requests.post(
            url,
            json={},
            headers=build_headers(),
            timeout=15
        )

        r.raise_for_status()

        cookie_raw = r.headers.get("Set-Cookie", "")

        match = re.search(
            r"Edge-Cache-Cookie=([^;]+)",
            cookie_raw
        )

        if match:
            cookie = f"Edge-Cache-Cookie={match.group(1)}"
            print(f"[{now_dhaka()}] Cookie refreshed")
            return cookie

        print(f"[{now_dhaka()}] Cookie missing")
        return None

    except Exception as e:
        print(f"[{now_dhaka()}] Cookie fetch failed → {e}")
        return None


# ────────────────────────────────────────────────
# LOAD JSON
# ────────────────────────────────────────────────
def load_channels():
    path = CONFIG["json_file"]

    if not os.path.exists(path):
        print(f"[{now_dhaka()}] Missing {path}")
        return None, []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        channels = data.get("channels", [])
    else:
        channels = data

    return data, channels


# ────────────────────────────────────────────────
# SAVE JSON
# ────────────────────────────────────────────────
def save_json(original, channels):
    if isinstance(original, dict):
        original["channels"] = channels
        original["last_updated"] = now_dhaka()
        data = original
    else:
        data = channels

    with open(CONFIG["json_file"], "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


# ────────────────────────────────────────────────
# INTRO ENTRY
# ────────────────────────────────────────────────
def add_intro(channels):
    intro_id = "intro"

    channels = [
        x for x in channels
        if x.get("id") != intro_id
    ]

    channels.insert(0, {
        "id": "intro",
        "category_name": "Intro",
        "name": "credit: johirxofficial",
        "logo": "https://johirxofficial.github.io/logos/IMG_20260221_143301.png",
        "link": "https://cdn.pixabay.com/video/2023/11/11/188742-883619742_large.mp4"
    })

    return channels


# ────────────────────────────────────────────────
# UPDATE COOKIE
# ────────────────────────────────────────────────
def apply_cookie(channels, cookie):
    count = 0

    for ch in channels:
        if ch.get("id") != "intro" and ch.get("link"):
            ch["cookie"] = cookie
            count += 1

    return count


# ────────────────────────────────────────────────
# BUILD M3U
# ────────────────────────────────────────────────
def generate_m3u(channels):
    with open(CONFIG["m3u_file"], "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write('#EXT-X-SESSION-KEY:METHOD=AES-128,URI="fake"\n\n')

        for ch in channels:
            link = ch.get("link")
            if not link:
                continue

            name = ch.get("name", "Unknown")
            logo = ch.get("logo", "")
            group = ch.get("category_name", "TV")
            cid = ch.get("id", "")

            f.write(
                f'#EXTINF:-1 tvg-id="{cid}" tvg-logo="{logo}" group-title="{group}",{name}\n'
            )

            f.write(
                f'#EXTVLCOPT:http-user-agent={CONFIG["user_agent"]}\n'
            )

            if cid != "intro":
                if ch.get("cookie"):
                    f.write(
                        f'#EXTVLCOPT:http-cookie={ch["cookie"]}\n'
                    )

            f.write(link + "\n\n")


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────
def main():
    print(f"[{now_dhaka()}] Starting update")

    cookie = fetch_fresh_cookie()

    if not cookie:
        print(f"[{now_dhaka()}] Cannot continue")
        return

    original, channels = load_channels()

    if original is None:
        return

    channels = add_intro(channels)

    total = apply_cookie(channels, cookie)

    save_json(original, channels)

    print(f"[{now_dhaka()}] JSON updated ({total} channels)")

    generate_m3u(channels)

    print(f"[{now_dhaka()}] M3U generated")
    print(f"[{now_dhaka()}] Done")


if __name__ == "__main__":
    main()
