from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI()

# CHANGE THESE: Set these to the actual active domains/mirrors used by the providers
BASE_STREAM_URL = "https://cricfy.top"  # Example stream host domain
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mi TV Stick) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Referer": BASE_STREAM_URL
}

def fetch_live_channels():
    """
    Scrapes the main landing page of the provider to extract 
    all currently active live channels and their internal IDs.
    """
    channels = {}
    try:
        response = requests.get(BASE_STREAM_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for anchor tags or stream player links (Adapts to typical web layouts)
        # Often channels are inside links matching "/watch.php?id=" or "play.html?ch="
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Pattern matching for web player IDs (e.g., watch.php?id=star-sports)
            match = re.search(r'(?:id|ch|stream)=([a-zA-Z0-9_-]+)', href)
            if match:
                ch_id = match.group(1)
                ch_name = a_tag.get_text(strip=True) or ch_id.replace('-', ' ').title()
                
                # Filter out duplicate variations or structural links
                if ch_id not in channels and len(ch_id) > 2:
                    channels[ch_id] = {
                        "name": ch_name,
                        "logo": f"https://img.logo.dev/{ch_id}.png?token=public", # Fallback logo generator
                        "group": "Live TV"
                    }
    except Exception as e:
        print(f"Error indexing live directory: {e}")
    
    return channels

def extract_m3u8_stream(channel_id):
    """
    Simulates the extension's extraction rules.
    It hits the specific player embed page, searches the JavaScript payload,
    and isolates the active tokenized streaming link.
    """
    try:
        # Build target url based on how the platform serves embeds
        player_url = f"{BASE_STREAM_URL}/watch.php?id={channel_id}"
        
        session = requests.Session()
        response = session.get(player_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check inside script blocks where source configurations are handled
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Regex patterns to locate hidden stream sources (eval expressions or source declarations)
                match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', script.string)
                if match:
                    cleaned_url = match.group(1).replace('\\', '') # Clean escape characters if hidden in JSON
                    return cleaned_url
                    
        # Check for standard iframe embed variations
        iframe = soup.find('iframe', src=True)
        if iframe:
            iframe_response = session.get(iframe['src'], headers={"Referer": player_url}, timeout=10)
            match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', iframe_response.text)
            if match:
                return match.group(1).replace('\\', '')

    except Exception as e:
        print(f"Extraction failed for channel {channel_id}: {e}")
    return None

@app.get("/playlist.m3u", response_class=PlainTextResponse)
def generate_playlist():
    """Generates the live configuration dynamically based on what is active on the server"""
    # Replace with your actual Render web service address
    host_url = "https://your-subdomain.onrender.com" 
    
    active_channels = fetch_live_channels()
    
    if not active_channels:
        # Fallback if scraping directory completely fails so your playlist isn't blank
        return "#EXTM3U\n#EXTINF:-1 group-title=\"Error\",Directory Failed. Check Server Logs\nhttp://localhost/error.mp4"

    m3u_content = "#EXTM3U\n"
    for ch_id, ch_info in active_channels.items():
        m3u_content += f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{ch_info["logo"]}" group-title="{ch_info["group"]}",{ch_info["name"]}\n'
        m3u_content += f'{host_url}/live/{ch_id}\n'
        
    return m3u_content

@app.get("/live/{channel_id}")
def stream_redirect(channel_id: str):
    """Intercepts the play request, pulls a fresh working token, and hands it off to your IPTV app"""
    stream_link = extract_m3u8_stream(channel_id)
    if not stream_link:
        raise HTTPException(status_code=503, detail="Stream token expired or source offline")
        
    return RedirectResponse(url=stream_link)
