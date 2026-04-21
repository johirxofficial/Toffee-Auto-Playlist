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

    # Token from GitHub Secret
    "token": os.getenv("TOFFEE_BEARER_TOKEN", "").strip(),

    # Browser UA
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",

    # Cookie source IDs
    "live_cookie_id": "LnlKhJkBcqxnFHJBU8GM",
    "default_cookie_id": "PiL635oBEef-9-uV2uCe",
}

# ────────────────────────────────────────────────
# CHECK TOKEN
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
# HEADERS
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
# FETCH COOKIE BY CHANNEL ID
# ────────────────────────────────────────────────
def fetch_cookie(channel_id):
    url = f"https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/web/playback/{channel_id}"

    try:
        r = requests.post(
            url,
            json={},
            headers=build_headers(),
            timeout=15
        )

        r.raise_for_status()

        raw = r.headers.get("Set-Cookie", "")

        match = re.search(
            r"Edge-Cache-Cookie=([^;]+)",
            raw
        )

        if match:
            return f"Edge-Cache-Cookie={match.group(1)}"

        return None

    except Exception as e:
        print(f"[{now_dhaka()}] Cookie fail ({channel_id}) → {e}")
        return None


# ────────────────────────────────────────────────
# LOAD JSON
# ────────────────────────────────────────────────
def load_json():
    if not os.path.isfile(CONFIG["json_file"]):
        print("❌ Missing toffee_playlist.json")
        exit(1)

    with open(CONFIG["json_file"], "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        channels = data.get("channels", [])
    else:
        channels = data

    return data, channels


# ────────────────────────────────────────────────
# INTRO ENTRY
# ────────────────────────────────────────────────
def insert_intro(channels):
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
# APPLY COOKIES
# Live category = live cookie
# others = default cookie
# ────────────────────────────────────────────────
def apply_cookies(channels, live_cookie, default_cookie):
    count = 0

    for ch in channels:
        if ch.get("id") == "intro":
            continue

        if not ch.get("link"):
            continue

        category = str(
            ch.get("category_name", "")
        ).strip().lower()

        if category == "live":
            ch["cookie"] = live_cookie
        else:
            ch["cookie"] = default_cookie

        count += 1

    return count


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
# GENERATE M3U
# ────────────────────────────────────────────────
def generate_m3u(channels):
    with open(CONFIG["m3u_file"], "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write('#EXT-X-SESSION-KEY:METHOD=AES-128,URI="fake"\n\n')

        for ch in channels:
            link = ch.get("link")
            if not link:
                continue

            cid = ch.get("id", "")
            name = ch.get("name", "Unknown")
            logo = ch.get("logo", "")
            group = ch.get("category_name", "TV")

            f.write(
                f'#EXTINF:-1 tvg-id="{cid}" tvg-logo="{logo}" group-title="{group}",{name}\n'
            )

            f.write(
                f'#EXTVLCOPT:http-user-agent={CONFIG["user_agent"]}\n'
            )

            if cid != "intro":
                cookie = ch.get("cookie")
                if cookie:
                    f.write(
                        f'#EXTVLCOPT:http-cookie={cookie}\n'
                    )

            f.write(link + "\n\n")


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────
def main():
    print(f"[{now_dhaka()}] Starting update")

    # Fetch both cookies
    live_cookie = fetch_cookie(CONFIG["live_cookie_id"])
    default_cookie = fetch_cookie(CONFIG["default_cookie_id"])

    if not live_cookie:
        print("❌ Live cookie failed")
        return

    if not default_cookie:
        print("❌ Default cookie failed")
        return

    print(f"[{now_dhaka()}] Cookies refreshed")

    data, channels = load_json()

    channels = insert_intro(channels)

    total = apply_cookies(
        channels,
        live_cookie,
        default_cookie
    )

    save_json(data, channels)

    print(f"[{now_dhaka()}] JSON updated ({total} channels)")

    generate_m3u(channels)

    print(f"[{now_dhaka()}] M3U generated")
    print(f"[{now_dhaka()}] Done")


if __name__ == "__main__":
    main()
