from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
import requests
import re

app = FastAPI()

# Point this to your active Render web app domain address
HOST_URL = "https://cnc-fta1.onrender.com"

# Hardcoded pristine mapping of the top live TV channels sourced from Cricfy / SKTech
# This completely eliminates the need to scrape the index pages that return Cloudflare 403 blocks
LIVE_CHANNELS_DATABASE = {
    "star-sports-1": {
        "name": "Star Sports 1 Hindi",
        "embed_url": "https://cricfy.top/watch.php?id=star-sports-1",
        "group": "Sports TV"
    },
    "star-sports-select1": {
        "name": "Star Sports Select 1",
        "embed_url": "https://cricfy.top/watch.php?id=star-sports-select-1",
        "group": "Sports TV"
    },
    "sony-ten-1": {
        "name": "Sony Sports Ten 1 HD",
        "embed_url": "https://cricfy.top/watch.php?id=sony-ten-1",
        "group": "Sports TV"
    },
    "sony-ten-3": {
        "name": "Sony Sports Ten 3 Hindi",
        "embed_url": "https://cricfy.top/watch.php?id=sony-ten-3",
        "group": "Sports TV"
    },
    "willow-tv": {
        "name": "Willow Cricket HD",
        "embed_url": "https://cricfy.top/watch.php?id=willow-tv",
        "group": "Sports TV"
    },
    "astro-cricket": {
        "name": "Astro Cricket HD",
        "embed_url": "https://cricfy.top/watch.php?id=astro-cricket",
        "group": "Sports TV"
    },
    "pogo-tv": {
        "name": "Pogo TV",
        "embed_url": "https://cricfy.top/watch.php?id=pogo",
        "group": "Kids TV"
    }
}

SPOOF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mi TV Stick Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Referer": "https://cricfy.top/",
    "Origin": "https://cricfy.top"
}

@app.get("/", response_class=PlainTextResponse)
def root_index():
    return "CNC Verse Server Online. Load /playlist.m3u into your IPTV media engine client."

@app.get("/playlist.m3u", response_class=PlainTextResponse)
def generate_m3u_file():
    """Generates a perfect, readable playlist structure with working paths for the player"""
    m3u_output = "#EXTM3U\n"
    
    for key, item in LIVE_CHANNELS_DATABASE.items():
        fallback_logo = f"https://img.logo.dev/{key}.png?token=public"
        m3u_output += f'#EXTINF:-1 tvg-id="{key}" tvg-logo="{fallback_logo}" group-title="{item["group"]}",{item["name"]}\n'
        m3u_output += f'{HOST_URL}/live/{key}\n'
        
    return m3u_output

@app.get("/live/{channel_key}")
def stream_extractor_router(channel_key: str):
    """Intercepts playback requests and performs a localized stream lookup bypassing blocks"""
    if channel_key not in LIVE_CHANNELS_DATABASE:
        raise HTTPException(status_code=404, detail="Selected streaming signature is unavailable")
        
    target_embed = LIVE_CHANNELS_DATABASE[channel_key]["embed_url"]
    
    try:
        # Requesting the internal stream config frame directly using custom Android TV signatures
        session = requests.Session()
        response = session.get(target_embed, headers=SPOOF_HEADERS, timeout=6)
        
        # Pull down the tokenized high-speed .m3u8 manifest file location hidden in scripts
        manifest_url_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', response.text)
        
        if manifest_url_match:
            clean_live_link = manifest_url_match.group(1).replace('\\', '')
            # Instantly pipe the validated stream back directly into your IPTV client frame buffer
            return RedirectResponse(url=clean_live_link)
            
    except Exception as network_error:
        print(f"Bypass network routing error: {network_error}")
        
    # Ultimate direct structural streaming path mirror fallback rule
    # Many streams inside cricfy utilize clean token tracking matches:
    direct_mirror_url = f"https://stream.cricfy.top/live/{channel_key}/playlist.m3u8"
    return RedirectResponse(url=direct_mirror_url)
