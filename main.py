from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI()

# A mock dictionary of channels. You will update the scraping logic inside get_live_url 
# based on the target site the extension scrapes.
CHANNELS = {
    "1": {"name": "Star Sports 1", "logo": "https://example.com/ss1.png", "group": "Sports"},
    "2": {"name": "Sony Sports Ten 1", "logo": "https://example.com/sony1.png", "group": "Sports"},
}

def get_live_url(channel_id):
    """
    This mimics the logic inside NivinCNC's Kotlin provider.
    It scrapes the target web player, extracts the tokenized stream URL, and returns it.
    """
    try:
        # Example for a generic web streaming scraper:
        # Replace this URL with the actual streaming source domain used by the extension
        target_url = f"https://example-stream-provider.to/embed/{channel_id}" 
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        response = requests.get(target_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the master playlist links inside the scripts (m3u8)
        script_text = "".join([script.text for script in soup.find_all("script")])
        match = re.search(r'(https://.*?\.m3u8\?token=[a-zA-Z0-9]+)', script_text)
        
        if match:
            return match.group(1)
        
        # Fallback/Alternative extraction rules can go here
        raise Exception("Stream link not found in page source.")
    except Exception as e:
        print(f"Error scraping channel {channel_id}: {e}")
        return None

@app.get("/playlist.m3u", response_class=PlainTextResponse)
def generate_playlist():
    """Dynamically generates the M3U playlist pointing back to Render endpoints"""
    host_url = "https://your-subdomain.onrender.com" # Render will give you this URL
    
    m3u_content = "#EXTM3U\n"
    for ch_id, ch_info in CHANNELS.items():
        m3u_content += f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{ch_info["logo"]}" group-title="{ch_info["group"]}",{ch_info["name"]}\n'
        m3u_content += f'{host_url}/live/{ch_id}\n'
        
    return m3u_content

@app.get("/live/{channel_id}")
def stream_redirect(channel_id: str):
    """When a channel is clicked, it gets the fresh URL and redirects your player to it"""
    if channel_id not in CHANNELS:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    live_stream_url = get_live_url(channel_id)
    if not live_stream_url:
        raise HTTPException(status_code=503, detail="Live stream currently unavailable")
        
    # Redirects the IPTV app directly to the newly scraped, active .m3u8 link
    return RedirectResponse(url=live_stream_url)
