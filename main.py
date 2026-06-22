from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
import requests
import base64

app = FastAPI()

# Make sure to update this with your exact Render app URL
HOST_URL = "https://cnc-fta1.onrender.com"

# The hidden API endpoints discovered inside the SKTech provider code
API_BASE_URL = "https://sktech786.xyz/sktech" 
HEADERS = {
    "User-Agent": "okhttp/3.12.1",  # Emulates Android system networking
    "Connection": "Keep-Alive"
}

def fetch_sktech_channels():
    """Fetches the real live channel database directly from the provider's API backend"""
    channels = {}
    try:
        # Replicating the request context from the Kotlin provider init
        url = f"{API_BASE_URL}/live_tv.php"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # If the response array is nested, we normalize it
            items = data if isinstance(data, list) else data.get("live_tv", [])
            
            for item in items:
                # Adjust keys based on typical PHP live TV API schemas
                ch_id = str(item.get("id") or item.get("ch_id"))
                ch_name = item.get("name") or item.get("title")
                stream_url = item.get("stream_url") or item.get("url")
                logo = item.get("logo") or item.get("image", "")
                group = item.get("category", "Live TV")
                
                if ch_id and stream_url:
                    channels[ch_id] = {
                        "name": ch_name,
                        "stream_url": stream_url,
                        "logo": logo,
                        "group": group
                    }
    except Exception as e:
        print(f"Error reading SKTech API endpoint: {e}")
        
    return channels

@app.get("/", response_class=PlainTextResponse)
def home_status():
    return "CNC Verse IPTV Proxy: Operational. Load /playlist.m3u into your application."

@app.get("/playlist.m3u", response_class=PlainTextResponse)
def generate_playlist():
    active_channels = fetch_sktech_channels()
    
    if not active_channels:
        # Stable backup array so your player never breaks completely
        return "#EXTM3U\n#EXTINF:-1 group-title=\"Error\",No Active Channels Fetched. Verify Server Connection.\nhttp://localhost/error.mp4"

    m3u_content = "#EXTM3U\n"
    for ch_id, ch_info in active_channels.items():
        logo = ch_info["logo"] if ch_info["logo"] else f"https://img.logo.dev/{ch_id}.png?token=public"
        m3u_content += f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{ch_info["group"]}",{ch_info["name"]}\n'
        m3u_content += f'{HOST_URL}/live/{ch_id}\n'
        
    return m3u_content

@app.get("/live/{channel_id}")
def stream_redirect(channel_id: str):
    active_channels = fetch_sktech_channels()
    
    if channel_id not in active_channels:
        raise HTTPException(status_code=404, detail="Requested channel signature not found")
        
    raw_stream_url = active_channels[channel_id]["stream_url"]
    
    # Decryption Layer: SKTech frequently encodes stream strings using standard Base64 
    # to protect links from standard scrapers. We decode it seamlessly on the fly.
    try:
        if raw_stream_url.startswith("aHR0c"): # Base64 signature identifier for 'http'
            raw_stream_url = base64.b64decode(raw_stream_url).decode('utf-8')
    except Exception:
        pass # If not base64 encoded, pass through as a raw string
        
    # Check if the URL points to an embed wrapper instead of a direct video stream
    if "watch.php" in raw_stream_url or "embed" in raw_stream_url:
        try:
            res = requests.get(raw_stream_url, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10)"}, timeout=5)
            import re
            match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', res.text)
            if match:
                raw_stream_url = match.group(1).replace('\\', '')
        except Exception:
            pass

    return RedirectResponse(url=raw_stream_url)
