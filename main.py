
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
import requests
import json

app = FastAPI()

# Make sure this matches your exact Render app address
HOST_URL = "https://cnc-fta1.onrender.com"

# The same API/repository structures utilized by the extensions
# Contains thousands of live stream mappings without Cloudflare blocks
CHANNELS_SOURCE_URL = "https://raw.githubusercontent.com/NivinCNC/CNCVerse-Cloud-Stream-Extension/main/live_tv_channels.json"

def get_channel_map():
    """Fetches the actual raw channel list directly from the source data repository"""
    try:
        # If the file is inside the repo, we pull it cleanly without scraping html
        response = requests.get(CHANNELS_SOURCE_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Failed to fetch source database: {e}")
    
    # Static backup map in case GitHub or the repository path changes
    return {
        "star-sports-1": {"name": "Star Sports 1 Hindi", "stream_url": "https://pubads.g.doubleclick.net/gampad/live/ads?iu=/21775744923/external/single_ad_samples&ciu_szs=300x250&cust_params=sample_ct%3Dlinear&gdfp_req=1&env=vp&output=vast&unviewed_position_start=1&correlator="}, # Test stream
        "sony-ten-1": {"name": "Sony Sports Ten 1", "stream_url": ""},
    }

@app.get("/", response_class=PlainTextResponse)
def home_status():
    return "Proxy Operational. Use /playlist.m3u inside your IPTV player."

@app.get("/playlist.m3u", response_class=PlainTextResponse)
def generate_playlist():
    channels = get_channel_map()
    
    m3u_content = "#EXTM3U\n"
    
    # Parse through the source list
    for key, data in channels.items():
        name = data.get("name", key.replace('-', ' ').title())
        group = data.get("category", "Live TV")
        logo = data.get("logo", f"https://img.logo.dev/{key}.png?token=public")
        
        m3u_content += f'#EXTINF:-1 tvg-id="{key}" tvg-logo="{logo}" group-title="{group}",{name}\n'
        m3u_content += f'{HOST_URL}/live/{key}\n'
        
    return m3u_content

@app.get("/live/{channel_id}")
def stream_redirect(channel_id: str):
    channels = get_channel_map()
    
    if channel_id not in channels:
        raise HTTPException(status_code=404, detail="Channel not found in current directory")
        
    # Get stream URL from data mapping
    target_stream = channels[channel_id].get("stream_url")
    
    # If the stream utilizes an external dynamic resolver link, resolve it on-the-fly
    if "watch.php" in target_stream or "embed" in target_stream:
        try:
            # Add custom header spoofing a mobile user agent
            res = requests.get(target_stream, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10)"}, timeout=5)
            import re
            match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', res.text)
            if match:
                target_stream = match.group(1).replace('\\', '')
        except Exception:
            pass

    if not target_stream:
        raise HTTPException(status_code=503, detail="Stream source offline")
        
    return RedirectResponse(url=target_stream)
