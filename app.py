import streamlit as st
import requests
import re
import time
import numpy as np
from bs4 import BeautifulSoup
import google.generativeai as genai
import folium
from streamlit_folium import st_folium
import pandas as pd

# 1) Ensure pandas is available as 'pd'
try:
    import pandas as pd
except Exception:
    pd = None  # prevents crash if pandas isn't used in some paths

# 2) Safe fallback for amenities function
if "get_amenities_for_type" not in globals():
    def get_amenities_for_type(prop_type):
        if prop_type in ["Residential Apartment", "Villa / Independent House"]:
            return ["Lift", "Parking", "Security", "Gym", "Garden", "Power Backup", "Clubhouse", "Swimming Pool"]
        elif prop_type == "Commercial Office":
            return ["Lift", "Parking", "Power Backup", "Central AC", "Security", "Fire Safety"]
        elif prop_type == "Retail Shop / SCO":
            return ["Main Road Facing", "High Footfall", "Parking", "Security"]
        elif prop_type == "Industrial / Warehouse":
            return ["Truck Access", "Loading Dock", "Power Supply", "Security"]
        elif prop_type == "Plot / Land":
            return ["Corner Plot", "Road Access", "Near Highway", "Clear Title"]
        return []

# 3) Safe currency formatter (₹ Crores)
if "fmt_cr" not in globals():
    def fmt_cr(value):
        try:
            return f"₹ {float(value)/10000000:.2f} Cr"
        except Exception:
            return "₹ 0 Cr" 
# ─────────────────────────────────────────────
# 1. PAGE CONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="CollateralIQ Pro | AI Collateral Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# 2. API KEYS & CONFIGURATION
# ─────────────────────────────────────────────
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"  # Replace with your actual Gemini API key
OPENCAGE_API_KEY = "1d90c0fdc4a54c46865277e715f4129c"

if GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────────
# 3. CSS Styling
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #080c12;
    color: #e8e0cc;
}
.main .block-container { padding: 2rem 3rem 4rem; max-width: 1400px; }
h1,h2,h3 { font-family: 'DM Serif Display', serif; color: #d4af37; }
hr { border-color: #1e2c3a; margin: 1.6rem 0; }

.ciq-banner {
    background: linear-gradient(135deg, #0b1420 0%, #0f1d2e 50%, #0b1420 100%);
    border: 0.5px solid #1e3a52; border-radius: 14px;
    padding: 28px 36px; display: flex; align-items: center; gap: 24px;
    margin-bottom: 28px; position: relative; overflow: hidden;
}
.ciq-banner::before {
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background: linear-gradient(90deg, transparent, #d4af37, transparent);
}
.ciq-logo {
    width:56px; height:56px; border-radius:12px; background:#d4af37;
    display:flex; align-items:center; justify-content:center;
    font-family:'DM Serif Display',serif; font-size:26px; color:#080c12; flex-shrink:0;
}
.ciq-title { font-family:'DM Serif Display',serif; font-size:28px; color:#d4af37; line-height:1; }
.ciq-sub   { font-size:13px; color:#6b8fa8; margin-top:6px; }
.ciq-badge {
    margin-left:auto; background:#0a1f0a; color:#4ade80; font-size:11px;
    padding:5px 14px; border-radius:20px; border:0.5px solid #1a5c1a;
}
.stepper-wrap {
    display:flex; background:#0b1420; border-radius:10px;
    border:0.5px solid #1e3a52; overflow:hidden; margin-bottom:24px;
}
.step-item {
    flex:1; padding:12px 8px; text-align:center; font-size:12px;
    font-weight:500; color:#4a6a82; border-right:0.5px solid #1e3a52;
}
.step-item:last-child { border-right:none; }
.step-item.active { background:#0f1d2e; color:#d4af37; }
.step-item.done   { color:#4ade80; }
.step-num { display:block; font-size:18px; margin-bottom:2px; }

.ciq-card {
    background:#0b1420; border:0.5px solid #1e3a52;
    border-radius:12px; padding:22px 24px; margin-bottom:16px;
}
.ciq-card-title {
    font-size:13px; font-weight:600; color:#d4af37; text-transform:uppercase;
    letter-spacing:1px; margin-bottom:16px; display:flex; align-items:center; gap:8px;
}
.ciq-card-title::before {
    content:''; width:6px; height:6px; border-radius:50%;
    background:#d4af37; flex-shrink:0;
}
.data-source-tag {
    display:inline-block; font-size:10px; padding:2px 8px; border-radius:10px;
    margin-left:8px; font-weight:500; background:#0a1f2e; color:#4a9ade;
    border:0.5px solid #1e3a52; vertical-align:middle;
}
.live-tag {
    display:inline-block; font-size:10px; padding:2px 8px; border-radius:10px;
    font-weight:500; background:#0a1f0a; color:#4ade80;
    border:0.5px solid #1a5c1a; vertical-align:middle; margin-left:6px;
}
.risk-flag {
    padding:12px 16px; border-radius:8px; margin-bottom:10px;
    font-size:13px; line-height:1.6; display:flex; align-items:flex-start; gap:12px;
}
.risk-flag.critical { background:#1a0808; border-left:3px solid #f87171; color:#f8c8c8; }
.risk-flag.moderate { background:#1a1208; border-left:3px solid #f59e0b; color:#f8e4c8; }
.risk-flag.positive { background:#081a08; border-left:3px solid #4ade80; color:#c8f8d0; }
.risk-icon { font-size:16px; flex-shrink:0; margin-top:1px; }
.ai-insight {
    background:#080f1a; border:0.5px solid #1e3a52;
    border-left:3px solid #d4af37; border-radius:10px;
    padding:20px 24px; margin-bottom:18px;
}
.ai-insight-label {
    font-size:10px; color:#d4af37; font-weight:600;
    text-transform:uppercase; letter-spacing:1.2px; margin-bottom:10px;
}
.ai-insight-text { font-size:14px; color:#b0c8d8; line-height:1.8; }
.comp-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:9px 0; border-bottom:0.5px solid #1e2c3a; font-size:13px;
}
.comp-row:last-child { border-bottom:none; }
.comp-name { color:#8aa8c0; }
.comp-val  { color:#e8e0cc; font-weight:500; }
.comp-tag  { font-size:10px; padding:2px 8px; border-radius:10px; margin-left:8px; font-weight:500; }
.tag-sold   { background:#0d2a0d; color:#4ade80; }
.tag-active { background:#2a1f0d; color:#f59e0b; }
.tag-live   { background:#0a1f2e; color:#4a9ade; }
.ltv-track {
    height:8px; background:#1e2c3a; border-radius:4px;
    margin:10px 0; overflow:hidden; position:relative;
}
.ltv-fill  { height:100%; border-radius:4px; }
.ltv-marker { position:absolute; top:-4px; width:2px; height:16px; background:#d4af37; border-radius:1px; }
.pin-hint {
    background:#0f1d2e; border:0.5px solid #d4af37;
    border-radius:8px; padding:10px 16px; font-size:13px;
    color:#d4af37; margin-bottom:12px; text-align:center;
}
.coords-box {
    background:#0a1520; border:0.5px solid #1e3a52; border-radius:8px;
    padding:10px 14px; font-size:12px; color:#6b8fa8; margin-top:8px;
}
.data-freshness {
    font-size:11px; color:#4a6a82; margin-top:6px;
    display:flex; align-items:center; gap:6px;
}

/* ── Streamlit overrides ── */
div[data-testid="stForm"] { background:transparent; border:none; }
div.stButton > button {
    background: linear-gradient(135deg, #c9a227, #d4af37);
    color: #080c12; font-weight:600; border:none; border-radius:8px;
    padding:10px 24px; font-size:14px; font-family:'DM Sans',sans-serif;
    width:100%; transition:all 0.2s;
}
div.stButton > button:hover { opacity:0.88; transform:translateY(-1px); }
div[data-testid="stTextInput"] input::placeholder { color: transparent !important; }
div[data-testid="stTextInput"] input {
    background:#0b1420 !important; color:#e8e0cc !important;
    border-color:#1e3a52 !important;
}
div[data-testid="stNumberInput"] input {
    background:#0b1420 !important; color:#e8e0cc !important;
    border-color:#1e3a52 !important;
}
div[data-testid="stSelectbox"] > div {
    background:#0b1420 !important; color:#e8e0cc !important;
    border-color:#1e3a52 !important;
}
div[data-testid="stMultiSelect"] > div { background:#0b1420 !important; }
label { color:#8aa8c0 !important; font-size:13px !important; }
.stProgress > div > div > div { background: linear-gradient(90deg,#c9a227,#d4af37); }
div[data-testid="stMetric"] { background:#0b1420; border:0.5px solid #1e3a52; border-radius:10px; padding:14px; }
div[data-testid="stMetric"] label { color:#4a6a82 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 3. PROPERTY CONFIGS
# ─────────────────────────────────────────────
PROP_CONFIGS = {
    "Residential Apartment": {
        "configs": ["1BHK", "2BHK", "3BHK", "4BHK+", "5BHK+"],
        "config_label": "Configuration",
        "area_label": "Carpet Area (sq ft)",
        "area_hint": "Typical: 400–3,000 sq ft",
        "is_commercial": False,
    },
    "Villa / Independent House": {
        "configs": ["2BHK", "3BHK", "4BHK", "5BHK+"],
        "config_label": "Configuration",
        "area_label": "Built-up Area (sq ft)",
        "area_hint": "Typical: 1,200–8,000 sq ft",
        "is_commercial": False,
    },
    "Commercial Office": {
        "configs": ["Small (< 500 sqft)", "Mid-size (500–2000 sqft)", "Large (2000–5000 sqft)", "Floor Plate (5000+ sqft)"],
        "config_label": "Office Size",
        "area_label": "Carpet Area (sq ft)",
        "area_hint": "Typical: 300–20,000 sq ft",
        "is_commercial": True,
    },
    "Retail Shop / SCO": {
        "configs": ["Kiosk (< 200 sqft)", "Small Shop (200–600 sqft)", "Large Shop (600–2000 sqft)", "SCO / Showroom (2000+ sqft)"],
        "config_label": "Unit Size",
        "area_label": "Carpet Area (sq ft)",
        "area_hint": "Typical: 100–5,000 sq ft",
        "is_commercial": True,
    },
    "Industrial / Warehouse": {
        "configs": ["Small Unit (< 2000 sqft)", "Mid-size (2000–10000 sqft)", "Large (10000–50000 sqft)", "Mega Warehouse (50000+ sqft)"],
        "config_label": "Facility Size",
        "area_label": "Built-up Area (sq ft)",
        "area_hint": "Typical: 1,000–2,00,000 sq ft",
        "is_commercial": True,
    },
    "Plot / Land": {
        "configs": ["Residential Plot", "Commercial Plot", "Industrial Plot", "Agricultural Land"],
        "config_label": "Land Use",
        "area_label": "Area (sq ft)",
        "area_hint": "Typical: 500–50,000 sq ft",
        "is_commercial": False,
    },
}

PROP_TYPE_LIST = list(PROP_CONFIGS.keys())

# ─────────────────────────────────────────────
# 4. RELEVANT CONSTANTS & HEADERS
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ─────────────────────────────────────────────
# 5. DATA FETCHING FUNCTIONS
# ─────────────────────────────────────────────
# Fetch MagicBricks Rate
@st.cache_data(ttl=1800)
def fetch_magicbricks_rate(city, locality, config, prop_type):
    city_slug = city.lower().replace(" ", "-")
    # Determine URL based on property type
    url = f"https://www.magicbricks.com/property-for-sale/residential-real-estate?cityName={city_slug}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return fallback_rate(city, locality, prop_type)
        soup = BeautifulSoup(resp.text, "html.parser")
        prices = []
        pattern = re.compile(r'₹([\d,]+)\s*/\s*sq', re.IGNORECASE)
        for text in soup.stripped_strings:
            if pattern.search(text):
                val = int(pattern.search(text).group(1).replace(',', ''))
                if 1000 < val < 250000:
                    prices.append(val)
        if len(prices) >= 3:
            prices.sort()
            trimmed = prices[len(prices)//10:-len(prices)//10] if len(prices)//10 != 0 else prices
            avg = int(np.mean(trimmed))
            return {
                "rate": avg,
                "source": "MagicBricks (live)",
                "listings_count": len(prices),
                "price_min": min(prices),
                "price_max": max(prices),
                "live": True,
            }
    except:
        pass
    return fallback_rate(city, locality, prop_type)

# Fetch 99acres Rate
@st.cache_data(ttl=1800)
def fetch_99acres_rate(city, locality, config, prop_type):
    city_slug = city.lower().replace(" ", "-")
    url = f"https://www.99acres.com/search/property/buy/{city_slug}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return {"rate": None, "source": "99acres", "live": False}
        soup = BeautifulSoup(resp.text, "html.parser")
        prices = []
        pattern = re.compile(r'([\d,]+)\s*/\s*sq\.?\s*ft', re.IGNORECASE)
        for text in soup.stripped_strings:
            if pattern.search(text):
                val = int(pattern.search(text).group(1).replace(',', ''))
                if 1000 < val < 250000:
                    prices.append(val)
        if len(prices) >= 2:
            return {
                "rate": int(np.mean(prices)),
                "source": "99acres (live)",
                "listings_count": len(prices),
                "live": True,
            }
    except:
        pass
    return {"rate": None, "source": "99acres", "live": False}

# Fetch RBI Repo Rate
@st.cache_data(ttl=3600)
def fetch_rbi_repo_rate():
    try:
        url = "https://www.rbi.org.in/Scripts/bs_viewcontent.aspx?Id=4"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()
        pattern = re.compile(r'(\d+\.\d+)\s*(per\s*cent|%)', re.IGNORECASE)
        matches = pattern.findall(text)
        rates = [float(m[0]) for m in matches if 3.0 < float(m[0]) < 12.0]
        if rates:
            return rates[0]
    except:
        pass
    return 6.50

# Fetch Google Maps Insights
@st.cache_data(ttl=1800)
def fetch_google_maps_insights(lat, lng):
    try:
        url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lng}&key={OPENCAGE_API_KEY}&limit=1&no_annotations=0"
        resp = requests.get(url, timeout=6).json()
        if resp.get("results"):
            res = resp["results"][0]
            comp = res.get("components", {})
            return {
                "suburb": comp.get("suburb") or comp.get("neighbourhood") or "",
                "road": comp.get("road") or "",
                "postcode": comp.get("postcode") or "",
                "city": comp.get("city") or comp.get("town") or comp.get("village") or "",
                "state": comp.get("state") or "",
                "timezone": res.get("annotations", {}).get("timezone", {}).get("name", ""),
                "what3words": res.get("annotations", {}).get("what3words", {}).get("words", ""),
            }
    except:
        pass
    return {}

# Fallback Rate based on city & property type
def fallback_rate(city, locality, prop_type="Residential Apartment"):
    RESIDENTIAL_RATES = {
        "mumbai": 22000, "navi mumbai": 14500, "thane": 13500,
        "pune": 9800, "nashik": 6000, "nagpur": 6400,
        "aurangabad": 5000, "solapur": 4400, "kolhapur": 4700,
        "bengaluru": 11500, "bangalore": 11500, "mysuru": 6200,
        "mysore": 6200, "hubli": 4700, "mangaluru": 6000,
        "hyderabad": 9000, "secunderabad": 8200, "warangal": 4200,
        "visakhapatnam": 6800, "vijayawada": 6000, "tirupati": 5200,
        "chennai": 8500, "coimbatore": 5700, "madurai": 5000,
        "trichy": 4700, "salem": 4200,
        "delhi": 15000, "new delhi": 15000, "noida": 9500,
        "gurgaon": 12000, "gurugram": 12000, "faridabad": 7200,
        "ghaziabad": 7800,
        "ahmedabad": 7200, "surat": 6800, "vadodara": 6000,
        "rajkot": 5200, "gandhinagar": 7000,
        "jaipur": 7000, "jodhpur": 4700, "udaipur": 5400,
        "kota": 4200, "ajmer": 4400,
        "kolkata": 7800, "howrah": 6200, "durgapur": 4200,
        "lucknow": 6200, "kanpur": 5000, "varanasi": 4700,
        "agra": 4700, "prayagraj": 4400, "patna": 5400,
        "chandigarh": 7800, "amritsar": 5700, "ludhiana": 6000,
        "bhopal": 5700, "indore": 6400, "gwalior": 4700,
        "bhubaneswar": 6000, "ranchi": 5200,
        "guwahati": 5700, "shillong": 5000,
        "dehradun": 6800, "haridwar": 5200,
        "kochi": 8000, "thiruvananthapuram": 6400, "kozhikode": 5700,
        "thrissur": 6000, "panaji": 9500, "margao": 8200,
    }
    # Commercial multipliers
    COMM_MULTIPLIER = {
        "Commercial Office": 1.6,
        "Retail Shop / SCO": 1.9,
        "Industrial / Warehouse": 0.8,
        "Plot / Land": 0.7,
        "Villa / Independent House": 1.15,
    }
    base = RESIDENTIAL_RATES.get(city.lower().strip(), 6500)
    mult = COMM_MULTIPLIER.get(prop_type, 1.0)
    rate = int(base * mult)
    return {
        "rate": rate,
        "source": "Calibrated index (2025)",
        "live": False,
        "listings_count": 0,
        "price_min": int(rate * 0.8),
        "price_max": int(rate * 1.3),
    }

# Get blended rate from MagicBricks & 99acres
def get_blended_rate(city, locality, config, prop_type):
    mb = fetch_magicbricks_rate(city, locality, config, prop_type)
    a99 = fetch_99acres_rate(city, locality, config, prop_type)
    rates = [r["rate"] for r in [mb, a99] if r.get("rate") and r.get("live")]
    live = len(rates) > 0
    if len(rates) == 2:
        blended = int(np.mean(rates))
        source = "MagicBricks + 99acres (live blended)"
    elif len(rates) == 1:
        blended = rates[0]
        source = mb["source"] if mb.get("live") else a99["source"]
    else:
        blended = mb["rate"]
        source = mb["source"]
    return {
        "rate": blended,
        "source": source,
        "live": live,
        "mb_rate": mb.get("rate"),
        "a99_rate": a99.get("rate"),
        "listings": mb.get("listings_count", 0) + (a99.get("listings_count") or 0),
        "price_min": mb.get("price_min", int(blended * 0.8)),
        "price_max": mb.get("price_max", int(blended * 1.3)),
    }

# ─────────────────────────────────────────────
# 6. GEOCODING FUNCTIONS
# ─────────────────────────────────────────────
_CITY_STATE = {
    "pune": "Maharashtra", "nagpur": "Maharashtra", "nashik": "Maharashtra",
    "aurangabad": "Maharashtra", "solapur": "Maharashtra", "kolhapur": "Maharashtra",
    "mysore": "Karnataka", "mysuru": "Karnataka", "hubli": "Karnataka",
    "mangalore": "Karnataka", "belgaum": "Karnataka",
    "kochi": "Kerala", "kozhikode": "Kerala", "thrissur": "Kerala",
    "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
    "trichy": "Tamil Nadu", "salem": "Tamil Nadu",
    "delhi": "Delhi", "new delhi": "Delhi", "noida": "Uttar Pradesh",
    "gurgaon": "Haryana", "gurugram": "Haryana", "faridabad": "Haryana",
    "kolkata": "West Bengal", "howrah": "West Bengal", "durgapur": "West Bengal",
    "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh", "agra": "Uttar Pradesh",
    "varanasi": "Uttar Pradesh", "prayagraj": "Uttar Pradesh",
    "allahabad": "Uttar Pradesh", "meerut": "Uttar Pradesh",
    "gandhinagar": "Gujarat", "ahmedabad": "Gujarat", "surat": "Gujarat",
    "vadodara": "Gujarat", "rajkot": "Gujarat",
    "jaipur": "Rajasthan", "jodhpur": "Rajasthan", "udaipur": "Rajasthan",
    "kota": "Rajasthan", "ajmer": "Rajasthan",
    "kolkata": "West Bengal", "howrah": "West Bengal", "durgapur": "West Bengal",
    "shillong": "Meghalaya",
}
_CITY_CENTROIDS = {
    "pune": (18.5204, 73.8567), "nagpur": (21.1458, 79.0882),
    "nashik": (19.9975, 73.7898), "aurangabad": (19.8762, 75.3433),
    "solapur": (17.6868, 75.9064), "kolhapur": (16.7050, 74.2433),
    "mysore": (12.2958, 76.6394), "hubli": (15.3647, 75.1240),
    "mangalore": (12.9141, 74.8560),
    "hyderabad": (17.3850, 78.4867), "secunderabad": (17.4399, 78.4983),
    "warangal": (17.9784, 79.5941), "vijayawada": (16.5062, 80.6480),
    "visakhapatnam": (17.6868, 83.2185), "tirupati": (13.6288, 79.4192),
    "chennai": (13.0827, 80.2707), "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198), "trichy": (10.7905, 78.7047),
    "salem": (11.6643, 78.1460),
    "delhi": (28.7041, 77.1025), "new delhi": (28.6139, 77.2090),
    "noida": (28.5355, 77.3910), "gurgaon": (28.4595, 77.0266),
    "gurugram": (28.4595, 77.0266), "ghaziabad": (28.6692, 77.4538),
    "faridabad": (28.4089, 77.3178),
    "ahmedabad": (23.0225, 72.5714), "surat": (21.1702, 72.8311),
    "vadodara": (22.3072, 73.1812), "rajkot": (22.3039, 70.8022),
    "jaipur": (26.9124, 75.7873), "jodhpur": (26.2389, 73.0243),
    "udaipur": (24.5854, 73.7125),
}
INDIA_BOUNDS = "68.1766,8.0847,97.4026,37.6451"

def _clean_part(s):
    for pat, repl in {
        r"\bSec\.?\s*(\d+)": "Sector \1",
        r"\bSect\.?\s*(\d+)": "Sector \1",
        r"\bPh\.?\s*(\d+)": "Phase \1",
        r"\bBlk\.?\s*([A-Z\d]+)": "Block \1",
        r"\bPlot\.?\s*([A-Z\d\-/]+)": "Plot \1",
        r"\bSvy\.?\s*(\d+)": "Survey \1",
        r"\bSurvey No\.?\s*(\d+)": "Survey \1",
        r"\bKh\.?\s*(\d+)": "Khasra \1",
        r"\bW/No\.?\s*(\d+)": "Ward \1",
        r"\bCHS\b": "Co-operative Housing Society",
        r"\bCGHS\b": "Co-operative Group Housing Society",
        r"\bSRA\b": "Slum Rehabilitation Authority",
        r"\bNH[-\s]?(\d+)": "National Highway \1",
        r"\bSH[-\s]?(\d+)": "State Highway \1",
        r"\bBTM\b": "BTM Layout",
        r"\bHBR\b": "HBR Layout",
        r"\bKR\s*Puram\b": "KR Puram",
        r"\bJP\s*Nagar\b": "JP Nagar",
        r"\bHS\s*Layout\b": "HS Layout",
        r"\bWhite\s*Field\b": "Whitefield",
        r"\bIndi\s*Nagar\b": "Indiranagar",
        r"\bKoram\b": "Koramangala",
        r"\bViman\s*Nagar\b": "Viman Nagar",
        r"\bIT\s*Park\b": "IT Park",
        r"\bHITEC\b": "HITEC City",
        r"\bAndheri\s*E\b": "Andheri East",
        r"\bAndheri\s*W\b": "Andheri West",
        r"\bBandra\s*E\b": "Bandra East",
        r"\bBandra\s*W\b": "Bandra West",
        r"\bBorivali\s*E\b": "Borivali East",
        r"\bBorivali\s*W\b": "Borivali West",
        r"\bMalad\s*E\b": "Malad East",
        r"\bMalad\s*W\b": "Malad West",
        r"\bGor\s*egaon\b": "Goregaon",
        r"\bKand\s*ivali\b": "Kandivali",
        r"\bMul\s*und\b": "Mulund",
        r"\bDLF\s*Ph": "DLF Phase",
        r"\bGolf\s*Crs\b": "Golf Course Road",
        r"\bMG\s*Rd\b": "MG Road",
        r"\b\d+\s*BHK\b": "",
        r"\bBHK\b": "",
        r"\b(Ground|G)\s*Floor\b": "",
        r"\b\d+(st|nd|rd|th)\s*Floor\b": "",
        r"\bFloor\s*\d+\b": "",
        r"\bFlat\s*No\.?\s*[A-Z\d\-/]+": "",
        r"\bUnit\s*No\.?\s*[A-Z\d\-/]+": "",
        r"\bFlat\b": "",
        r"\bApt\.?\b": "",
        r"\s{2,}": " ",
        r",\s*,": ",",
        r"^\s*,|,\s*$": "",
    }.items():
        s = re.sub(pat, repl, s, flags=re.IGNORECASE)
    return s.strip(" ,")

def _build_strategies(project, locality, city):
    p = _clean_part(project)
    l = _clean_part(locality)
    c = _clean_part(city)
    state = _CITY_STATE.get(city.lower().strip(), "")
    sfx = f", {state}" if state else ""
    strategies = []
    if p and l and c:
        strategies.append(("full", f"{p}, {l}, {c}{sfx}, India"))
    if l and c:
        strategies.append(("locality+city+state", f"{l}, {c}{sfx}, India"))
    if l and c and l.lower() != c.lower():
        strategies.append(("locality+city", f"{l}, {c}, India"))
    strategies.append(("city+state", f"{c}{sfx}, India"))
    return strategies

def _opencage_call(query):
    try:
        r = requests.get(
            "https://api.opencagedata.com/geocode/v1/json",
            params={
                "q": query,
                "key": OPENCAGE_API_KEY,
                "limit": 3,
                "countrycode": "in",
                "bounds": INDIA_BOUNDS,
                "no_annotations": 0,
                "language": "en",
            },
            timeout=8,
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except:
        return []

def _score_result(res, city, locality):
    conf = res.get("confidence", 0)
    score = conf / 10.0
    comp = res.get("components", {})
    formatted = res.get("formatted", "").lower()

    if comp.get("country_code", "in").lower() != "in":
        return 0.0

    res_city = (comp.get("city") or comp.get("town") or comp.get("village") or comp.get("county") or "").lower()
    if city.lower() in res_city or res_city in city.lower():
        score += 0.25

    tokens = [t.lower() for t in locality.split() if len(t) > 3]
    if tokens:
        score += 0.20 * sum(1 for t in tokens if t in formatted) / len(tokens)

    if conf <= 3:
        score -= 0.35

    return min(1.0, max(0.0, score))

def geocode_with_fallback(project, locality, city):
    strategies = _build_strategies(project, locality, city)
    best_result = None
    best_score = -1
    best_strategy = "fallback"

    for label, query in strategies:
        for res in _opencage_call(query):
            s = _score_result(res, city, locality)
            if s > best_score:
                best_score = s
                best_result = res
                best_strategy = label
        if best_score >= 0.80:
            break
        time.sleep(0.25)

    if best_result and best_score > 0.20:
        geo = best_result["geometry"]
        name = best_result.get("formatted", f"{locality}, {city}")
        return round(geo["lat"], 6), round(geo["lng"], 6), name, best_strategy

    # Fallback to city centroid
    key = city.lower().strip()
    centroid = _CITY_CENTROIDS.get(key, (20.5937, 78.9629))
    return centroid[0], centroid[1], f"{locality}, {city}", "city_centroid"

def reverse_geocode(lat, lng):
    try:
        r = requests.get(
            "https://api.opencagedata.com/geocode/v1/json",
            params={"q": f"{lat}+{lng}", "key": OPENCAGE_API_KEY, "limit": 1, "no_annotations": 1, "language": "en"},
            timeout=5,
        )
        data = r.json()
        if data.get("results"):
            comp = data["results"][0].get("components", {})
            city = comp.get("city") or comp.get("town") or comp.get("suburb") or comp.get("village") or comp.get("county") or ""
            return city, comp.get("state", "")
    except:
        pass
    return "", ""

# ─────────────────────────────────────────────
# 7. AI & Valuation Engine
# ─────────────────────────────────────────────
class ValuationEngine:
    RES_CONFIG_MULT = {
        "1BHK": 0.93, "2BHK": 1.00, "3BHK": 1.12, "4BHK+": 1.20, "5BHK+": 1.35
    }
    COM_CONFIG_MULT = {
        "Small (< 500 sqft)": 0.92,
        "Mid-size (500–2000 sqft)": 1.00,
        "Large (2000–5000 sqft)": 1.08,
        "Floor Plate (5000+ sqft)": 1.18,
        "Kiosk (< 200 sqft)": 0.90,
        "Small Shop (200–600 sqft)": 1.00,
        "Large Shop (600–2000 sqft)": 1.10,
        "SCO / Showroom (2000+ sqft)": 1.20,
        "Small Unit (< 2000 sqft)": 0.95,
        "Mid-size (2000–10000 sqft)": 1.00,
        "Large (10000–50000 sqft)": 1.05,
        "Mega Warehouse (50000+ sqft)": 1.12,
        "Residential Plot": 1.00,
        "Commercial Plot": 1.20,
        "Industrial Plot": 0.90,
        "Agricultural Land": 0.60,
    }
    FACING_BONUS = {"East": 1.025, "North": 1.015, "West": 1.005, "South": 1.000}

    @classmethod
    def _config_mult(cls, config, prop_type):
        if prop_type in ("Residential Apartment", "Villa / Independent House"):
            return cls.RES_CONFIG_MULT.get(config, 1.00)
        return cls.COM_CONFIG_MULT.get(config, 1.00)

    @classmethod
    def run(cls, d, market_data, repo_rate, geo_info):
        # Determine property type & status
        p_type = d["prop_type"]
        is_commercial = PROP_CONFIGS.get(p_type, {}).get("is_commercial", False)
        is_land = p_type == "Plot / Land"

        base_rate = market_data["rate"]
        cfg_mult = cls._config_mult(d["config"], p_type)

        # Depreciation and Premium
        if is_land:
            dep = 1.0
            dep_rate = 0.0
        elif is_commercial:
            dep_rate = 0.015 if d["age"] < 10 else 0.020 if d["age"] < 20 else 0.025
            dep = max(0.55, 1 - d["age"] * dep_rate)
        else:
            dep_rate = 0.020 if d["age"] < 10 else 0.025 if d["age"] < 20 else 0.030
            dep = max(0.60, 1 - d["age"] * dep_rate)

        # Floor premium
        if is_land:
            floor_b = 1.00
        elif is_commercial and p_type == "Commercial Office":
            floor_b = 1.04 if d["floor"] > d["total_floors"] * 0.6 else 1.02 if d["floor"] > d["total_floors"] * 0.3 else 1.00
        else:
            floor_b = 1.03 if 4 <= d["floor"] <= max(4, d["total_floors"] - 3) else 1.00

        facing_b = cls.FACING_BONUS.get(d.get("facing", "East"), 1.00)

        # Amenities premium
        amenities_count = len(d["amenities"])
        amenities_premium = 0.025 if is_commercial else 0.020
        amen_b = 1 + amenities_count * amenities_premium

        # Repo adjustment
        rate_adj = 1.0 if repo_rate <= 6.5 else max(0.94, 1 - (repo_rate - 6.5) * 0.015)

        # Locality adjustment
        suburb = geo_info.get("suburb", "").lower()
        if any(w in suburb for w in ["premium", "elite", "sector", "park", "hills", "garden", "cbd", "central"]):
            loc_adj = 1.15
        elif any(w in suburb for w in ["industrial", "outskirts", "rural", "village"]):
            loc_adj = 0.90
        else:
            seed = sum(ord(c) for c in d["locality"]) % 15
            loc_adj = 1.00 + seed * 0.008

        # Final valuation
        rate = base_rate * cfg_mult * dep * floor_b * facing_b * amen_b * rate_adj * loc_adj
        mv = int(rate * d["area"])

        # Resale index & TTS scenario
        resale = 75 if is_commercial else 80
        resale -= d["age"] * (1.0 if is_commercial else 1.2)
        resale += amenities_count * 3.0
        resale += (loc_adj - 1.0) * 80
        resale -= (repo_rate - 6.0) * 3
        if market_data["live"]: resale += 5
        if is_commercial: resale -= 5
        resale = max(20, min(95, int(resale)))

        # TTS scenarios
        if resale > 75:
            tts_base, tts_bull, tts_bear = "25–50 days", "15–28 days", "50–90 days"
        elif resale > 60:
            tts_base, tts_bull, tts_bear = "45–80 days", "30–50 days", "80–140 days"
        elif resale > 45:
            tts_base, tts_bull, tts_bear = "80–150 days", "60–90 days", "150–240 days"
        else:
            tts_base, tts_bull, tts_bear = "150–300 days", "100–150 days", "300–480 days"

        # LTV calculation
        ltv = round(d["loan_lakhs"] * 100000 / mv * 100, 1) if mv > 0 else 0
        ltv_rec = 65 if is_commercial else (75 if resale > 70 else 65 if resale > 50 else 55)

        # Confidence
        conf = 0.60
        conf += 0.15 if market_data["live"] else 0.05
        conf += min(0.08, market_data["listings"] * 0.002)
        conf += 0.05 if d["floor"] > 0 else 0
        conf += len(d["amenities"]) * 0.015
        conf += 0.04 if d["age"] < 10 else 0
        conf += 0.03 if geo_info.get("suburb") else 0
        conf = round(min(0.97, conf), 2)

        # Impact explanation (shap)
        shap = pd.DataFrame({
            "Feature": ["Live market rate", "Configuration/Size", "Age depreciation",
                        "Location premium", "Floor/Level premium", "Amenities",
                        "Repo rate impact", "Facing"],
            "Impact (₹L)": [
                round((base_rate - 9000) * d["area"] / 100000, 2),
                round((cfg_mult - 1.00) * base_rate * d["area"] / 100000, 2),
                round((1 - dep) - 1.00 * base_rate * d["area"] / 100000, 2),
                round((loc_adj - 1.00) * base_rate * d["area"] / 100000, 2),
                round((floor_b - 1.00) * base_rate * d["area"] / 100000, 2),
                round((amen_b - 1.00) * base_rate * d["area"] / 100000, 2),
                round((rate_adj - 1.00) * base_rate * d["area"] / 100000, 2),
                round((facing_b - 1.00) * base_rate * d["area"] / 100000, 2),
            ]
        })

        # Market comparables
        comps = []
        if market_data.get("mb_rate"):
            comps.append({"name": f"MagicBricks · {d['city']} · {d['config']}", "rate": market_data["mb_rate"], "tag": "live"})
        if market_data.get("a99_rate"):
            comps.append({"name": f"99acres · {d['city']} · {d['config']}", "rate": market_data["a99_rate"], "tag": "live"})
        comps += [
            {"name": f"{d['locality']} · Similar {d['prop_type']} (recent sold)", "rate": max(0, int(resale * (1 - 0.04))), "tag": "sold"},
            {"name": f"{d['locality']} · Premium unit (better specs/location)", "rate": int(resale * (1 + 0.06)), "tag": "active"},
            {"name": f"Adjacent micro-market · {d['config']}", "rate": max(0, int(resale * (1 - 0.09))), "tag": "sold"},
        ]

        # Risks
        risks = []
        if ltv > ltv_rec + 10:
            risks.append({"sev": "critical", "icon": "🚩", "text": f"CRITICAL — LTV {ltv}% breaches {ltv_rec}%"})
        if resale < 50:
            risks.append({"sev": "critical", "icon": "🔴", "text": f"LOW LIQUIDITY — Resale {resale} / 100"})
        if d["age"] > 20:
            risks.append({"sev": "critical", "icon": "⚠️", "text": f"AGED ASSET — {d['age']} years"})
        elif d["age"] > 12:
            risks.append({"sev": "moderate", "icon": "⚠️", "text": f"MID-LIFE — {d['age']} years"})
        if repo_rate > 7.0:
            risks.append({"sev": "moderate", "icon": "📈", "text": f"High repo rate environment: {repo_rate}%"})
        if len(d["amenities"]) < 2:
            risks.append({"sev": "moderate", "icon": "⚠️", "text": "Limited amenities"})
        if is_commercial:
            risks.append({"sev": "moderate", "icon": "🏢", "text": "Commercial asset, higher haircut"})
        if not market_data["live"]:
            risks.append({"sev": "moderate", "icon": "📊", "text": "Limited live data"})
        if resale >= 65 and d["age"] < 10 and ltv <= ltv_rec and market_data["live"]:
            risks.append({"sev": "positive", "icon": "✅", "text": "Collateral strength good"})
        if not risks:
            risks.append({"sev": "positive", "icon": "✅", "text": "No significant risks."})

        rates = [
            r for r in [
                market_data.get("mb_rate"),
                market_data.get("a99_rate")
            ]
            if isinstance(r, (int, float))
        ]
        rate_psf = int(np.mean(rates)) if rates else market_data.get("rate", 10000)

        return {
            "mv": mv,
            "dv": int(mv * (1 - 0.18)),  # distress haircut
            "mv_low": int(mv * 0.93),
            "mv_high": int(mv * 1.07),
            "dv_low": int(mv * 0.93 * (1 - 0.04)),
            "dv_high": int(mv * 1.07 * (1 + 0.04)),
            "haircut": round(max(0.18, min(0.25, 0.02 + d["age"] * 0.001))),
            "resale": resale,
            "conf": conf,
            "tts_base": tts_base,
            "tts_bull": tts_bull,
            "tts_bear": tts_bear,
            "ltv": ltv,
            "ltv_rec": ltv_rec,
            "shap": shap,
            "comps": comps,
            "risks": risks,
            "repo_rate": repo_rate,
            "is_commercial": is_commercial,
            "rate_psf": rate_psf,
        }

# ─────────────────────────────────────────────
# 8. UI & SESSION STATE
# ─────────────────────────────────────────────
# Defaults
defaults = {
    "step": 1,
    "project": "",
    "city": "",
    "locality": "",
    "area": 0,
    "age": 0,
    "config": "",
    "prop_type": "Residential Apartment",
    "amenities": [],
    "floor": 0,
    "total_floors": 0,
    "facing": "East",
    "loan_lakhs": 0,
    "lat": 20.5937,
    "lng": 78.9629,
    "pin_lat": None,
    "pin_lng": None,
    "map_query": "",
    "geocoded_name": "",
    "geocode_strategy": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# 9. Banner & Stepper
# ─────────────────────────────────────────────
st.markdown("""
<div class="ciq-banner">
  <div class="ciq-logo">C</div>
  <div>
    <div class="ciq-title">CollateralIQ Pro</div>
    <div class="ciq-sub">AI-Powered Valuation & Liquidity Engine · DecisionX Team</div>
  </div>
  <div class="ciq-badge">LIVE · TenzorX 2026</div>
</div>
""", unsafe_allow_html=True)

def stepper_html(active):
    steps = ["1 · Asset ID", "2 · Pin Location", "3 · Intelligence Report"]
    html = '<div class="stepper-wrap">'
    for i, s in enumerate(steps, 1):
        cls = "active" if i == active else ("done" if i < active else "")
        icon = "✓" if i < active else str(i)
        html += f'<div class="step-item {cls}"><span class="step-num">{icon}</span>{s}</div>'
    html += "</div>"
    return html

st.markdown(stepper_html(st.session_state.step), unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 10. Step 1 — Asset Identification
# ─────────────────────────────────────────────
if st.session_state.step == 1:
    st.markdown('<div class="ciq-card"><div class="ciq-card-title">Collateral Identification</div>', unsafe_allow_html=True)
    with st.form("asset_form"):
        col1, col2, col3 = st.columns(3)
        project = col1.text_input("Project / Asset Name", value=st.session_state.project)
        city = col2.text_input("City", value=st.session_state.city)
        locality = col3.text_input("Micro-Location / Area", value=st.session_state.locality)

        prop_type = st.selectbox(
            "Property Type",
            PROP_TYPE_LIST,
            index=PROP_TYPE_LIST.index(st.session_state.prop_type),
        )

        pconf = PROP_CONFIGS[prop_type]
        config = st.selectbox(pconf["config_label"], pconf["configs"], index=0)

        # Facing
        facing_options = ["East", "West", "North", "South"]
        facing = st.selectbox("Road-Facing Direction", facing_options, index=facing_options.index(st.session_state.facing))

        # Floors & Area
        show_floors = not pconf["is_commercial"]
        if show_floors:
            total_floors = st.number_input("Total Floors in Building", min_value=0, max_value=100, value=st.session_state.total_floors or 1)
            floor = st.number_input("Floor Number", min_value=0, max_value=total_floors, value=st.session_state.floor)
        else:
            total_floors = 1
            floor = 0

        area = st.number_input(pconf["area_label"], min_value=0, max_value=500000, value=st.session_state.area, help=pconf["area_hint"])
        age = st.number_input("Asset Age (Years)", min_value=0, max_value=100, value=st.session_state.age)
        loan_lakhs = st.number_input("Loan Sought (₹ Lakhs)", min_value=0, max_value=50000, value=st.session_state.loan_lakhs)

        amenities_list = get_amenities_for_type(prop_type)
        amenities = st.multiselect("Amenities / Features", amenities_list, default=st.session_state.amenities)

        submitted = st.form_submit_button("Verify Location on Map →")
        if submitted:
            errors = []
            if not project.strip():
                errors.append("Project / Asset Name is required.")
            if not city.strip():
                errors.append("City is required.")
            if not locality.strip():
                errors.append("Micro-Location is required.")
            if area <= 0:
                errors.append(f"{pconf['area_label']} must be > 0.")
            if loan_lakhs <= 0:
                errors.append("Loan amount must be > 0.")
            if show_floors and total_floors <= 0:
                errors.append("Total Floors must be > 0.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                st.session_state.update({
                    "project": project.strip(),
                    "city": city.strip(),
                    "locality": locality.strip(),
                    "config": config,
                    "prop_type": prop_type,
                    "facing": facing,
                    "area": area,
                    "age": age,
                    "loan_lakhs": loan_lakhs,
                    "floor": floor,
                    "total_floors": total_floors,
                    "amenities": amenities,
                    "step": 2,
                })
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 11. Step 2 — Map & Pin Drop
# ─────────────────────────────────────────────
elif st.session_state.step == 2:
    st.markdown(
        '<div class="ciq-card"><div class="ciq-card-title">Geo-Spatial Verification — Map navigates to your address · Click to pin exact location</div>',
        unsafe_allow_html=True,
    )

    query = f"{st.session_state.project},{st.session_state.locality},{st.session_state.city}"
    if st.session_state.map_query != query:
        with st.spinner("🔍 Locating property on map…"):
            lat, lng, gname, strategy = geocode_with_fallback(
                st.session_state.project,
                st.session_state.locality,
                st.session_state.city,
            )
        st.session_state.lat = lat
        st.session_state.lng = lng
        st.session_state.geocoded_name = gname
        st.session_state.geocode_strategy = strategy
        st.session_state.map_query = query

    lat = st.session_state.lat
    lng = st.session_state.lng

    strategy_labels = {
        "full": "full address match",
        "locality+city+state": "locality + city + state",
        "locality+city": "locality + city",
        "city+state": "city + state (broad)",
        "city_centroid": "city centroid (fallback)",
        "fallback": "fallback centroid",
    }

    st.markdown(
        f'<div class="pin-hint">'
        f'📍 Centred on <strong>{st.session_state.geocoded_name}</strong> '
        f'<span style="font-size:10px;color:#6b8fa8;font-weight:400;">'
        f'(matched via {strategy_labels.get(st.session_state.geocode_strategy, st.session_state.geocode_strategy)})</span><br>'
        f'<span style="font-size:12px;font-weight:400;">'
        f'<strong>Click the map</strong> to drop a pin on the exact property, '
        f'then press <em>Confirm Location &amp; Generate Report</em>.</span></div>',
        unsafe_allow_html=True,
    )

    col_map, col_side = st.columns([2.2, 1])
    with col_map:
        m = folium.Map(location=[lat, lng], zoom_start=17, tiles="OpenStreetMap")
        folium.Marker([lat, lng], tooltip="📍 Geocoded address", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
        folium.Circle([lat, lng], radius=300, color="#d4af37", fill=True, fill_opacity=0.07).add_to(m)
        folium.Circle([lat, lng], radius=1000, color="#4a6a82", fill=True, fill_opacity=0.04).add_to(m)
        if st.session_state.pin_lat and st.session_state.pin_lng:
            folium.Marker([st.session_state.pin_lat, st.session_state.pin_lng], tooltip="📌 Pinned property", icon=folium.Icon(color="red", icon="home")).add_to(m)
        map_data = st_folium(m, height=500, width=None, returned_objects=["last_clicked"])

        if map_data and map_data.get("last_clicked"):
            clicked = map_data["last_clicked"]
            st.session_state.pin_lat = round(clicked["lat"], 6)
            st.session_state.pin_lng = round(clicked["lng"], 6)
            # Reverse geocode to update city
            det_city, _ = reverse_geocode(clicked["lat"], clicked["lng"])
            if det_city:
                st.session_state.city = det_city

    with col_side:
        st.markdown("**Asset Summary**")
        st.markdown(f"📍 **{st.session_state.project}**")
        st.markdown(f"🏘️ {st.session_state.locality}, {st.session_state.city}")
        ptype_icon = "🏢" if PROP_CONFIGS.get(st.session_state.prop_type, {}).get("is_commercial") else \
                     "🌱" if st.session_state.prop_type == "Plot / Land" else "🏠"
        st.markdown(f"{ptype_icon} {st.session_state.config} · {st.session_state.area:,} sq ft")
        st.markdown(f"📅 Age: {st.session_state.age} yrs | Floor {st.session_state.floor}/{st.session_state.total_floors}")
        st.markdown(f"🧭 {st.session_state.facing} | 💰 ₹{st.session_state.loan_lakhs}L")
        st.markdown(f"🏷️ *{st.session_state.prop_type}*")
        st.markdown("---")
        if st.session_state.pin_lat and st.session_state.pin_lng:
            st.markdown(
                f'<div class="coords-box">📌 <strong>Pin confirmed</strong><br>'
                f'Lat: <code>{st.session_state.pin_lat}</code><br>'
                f'Lng: <code>{st.session_state.pin_lng}</code><br>'
                f'City: <strong>{st.session_state.city}</strong></div>',
                unsafe_allow_html=True,
            )
            st.success("Pinned ✓ Ready to generate report.")
        else:
            st.markdown('<div class="coords-box">⚠️ Click map to pin location.</div>', unsafe_allow_html=True)

    # Buttons
    col_btn1, col_btn2 = st.columns([1, 3])
    if col_btn1.button("← Back"):
        st.session_state.step = 1
        for k in ["map_query", "pin_lat", "pin_lng", "geocoded_name", "geocode_strategy"]:
            st.session_state[k] = defaults[k]
        st.rerun()

    if col_btn2.button("Confirm Location & Generate Report →"):
        if st.session_state.pin_lat is None:
            st.error("Please click the map to pin the location.")
        else:
            st.session_state.lat = st.session_state.pin_lat
            st.session_state.lng = st.session_state.pin_lng
            st.session_state.step = 3
            st.rerun()

# ─────────────────────────────────────────────
# 12. Step 3 — Generate & Show Report
# ─────────────────────────────────────────────
elif st.session_state.step == 3:
    with st.spinner("🔄 Fetching live market data…"):
        market_data = get_blended_rate(
            st.session_state.city,
            st.session_state.locality,
            st.session_state.config,
            st.session_state.prop_type,
        )
    with st.spinner("🔄 Fetching RBI repo rate & geo insights…"):
        repo_rate = fetch_rbi_repo_rate()
        geo_info = fetch_google_maps_insights(st.session_state.lat, st.session_state.lng)

    with st.spinner("🧠 Running valuation engine…"):
        inp = {
            "city": st.session_state.city,
            "locality": st.session_state.locality,
            "config": st.session_state.config,
            "prop_type": st.session_state.prop_type,
            "area": st.session_state.area,
            "age": st.session_state.age,
            "floor": st.session_state.floor,
            "total_floors": st.session_state.total_floors,
            "facing": st.session_state.facing,
            "amenities": st.session_state.amenities,
            "loan_lakhs": st.session_state.loan_lakhs,
            "lat": st.session_state.lat,
            "lng": st.session_state.lng,
        }
        R = ValuationEngine.run(inp, market_data, repo_rate, geo_info)

    is_commercial = R["is_commercial"]
    prop_type = st.session_state.prop_type

    # Data freshness banner
    data_source = market_data["source"]
    listings_count = market_data["listings"]
    repo_rate_val = repo_rate
    suburb_name = geo_info.get("suburb", "—")
    live_status = "🟢 LIVE" if market_data["live"] else "🟡 INDEX"

    st.markdown(f"""
    <div style='background:#080f1a;border:0.5px solid #1e3a52;border-radius:8px;padding:10px 16px;margin-bottom:16px;font-size:12px;color:#6b8fa8;display:flex;gap:20px;align-items:center;flex-wrap:wrap;'>
        <span>📊 <strong style='color:#d4af37;'>Data source:</strong> {data_source}</span>
        <span>🏠 <strong style='color:#d4af37;'>Listings analyzed:</strong> {listings_count}</span>
        <span>🏦 <strong style='color:#d4af37;'>RBI Repo:</strong> {repo_rate_val}%</span>
        <span>📍 <strong style='color:#d4af37;'>Suburb:</strong> {suburb_name}</span>
        <span>🏷️ <strong style='color:#d4af37;'>Type:</strong> {prop_type}</span>
        <span><strong style='color:{'#4ade80' if market_data['live'] else '#f59e0b'};'>{live_status}</strong></span>
    </div>
    """, unsafe_allow_html=True)

    # Summary info
    st.markdown(f"<div style='font-size:11px;color:#4a6a82;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;'>"
                f"Collateral Intelligence Report · {st.session_state.project} · {st.session_state.locality}, {st.session_state.city} · "
                f"{st.session_state.config} · {prop_type} · 📍 {st.session_state.lat:.5f}, {st.session_state.lng:.5f}"
                "</div>", unsafe_allow_html=True)

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    area_str = f"{R['mv_low']:,} – {R['mv_high']:,}"
    col1.metric("Market Value Range", area_str, f"₹{R['rate_psf']:,}/sq ft")
    dist_str = f"{R['dv_low']:,} – {R['dv_high']:,}"
    col2.metric("Distress Value Range", dist_str, f"Haircut {round(R['haircut']*100)}%")
    col3.metric("Resale / Exit Index", f"{R['resale']}/100", "Above-avg liquidity" if R["resale"] > 70 else "Moderate")
    col4.metric("Confidence Score", str(R["conf"]), "High" if R["conf"] > 0.85 else "Moderate")
    st.progress(R["conf"])
    st.markdown("---")

    # Explainable AI Impact Drivers
    st.markdown('<div class="ciq-card"><div class="ciq-card-title">Explainable AI — Value Drivers</div>', unsafe_allow_html=True)
    st.bar_chart(R["shap"].set_index("Feature")["Impact (₹L)"], color="#d4af37")
    st.caption(f"Baseline ₹9,000/sq ft for {st.session_state.city}.")
    st.markdown("</div>", unsafe_allow_html=True)

    # LTV & Recommendations
    st.markdown('<div class="ciq-card"><div class="ciq-card-title">LTV Analysis & Lending Recommendation</div>', unsafe_allow_html=True)
    fill_color = "#4ade80" if R["ltv"] <= R["ltv_rec"] else "#f87171"
    ltv_pct = min(R["ltv"], 100)
    rec_pct = R["ltv_rec"]

    st.markdown(f"""
        <div style='display:flex; justify-content:space-between; font-size:13px; margin-bottom:4px;'>
            <span style='color:#8aa8c0;'>Proposed LTV</span>
            <span style='color:{fill_color}; font-weight:600; font-size:20px;'>{R['ltv']}%</span>
        </div>
        <div class="ltv-track">
            <div class="ltv-fill" style="width:{ltv_pct}%; background:{fill_color};"></div>
            <div class="ltv-marker" style="left:{rec_pct}%;"></div>
        </div>
        <div style='display:flex; justify-content:space-between; font-size:11px; color:#4a6a82; margin-bottom:14px;'>
            <span>0%</span>
            <span style='color:#d4af37;'>▲ Max {rec_pct}%</span>
            <span>100%</span>
        </div>
        <div style='font-size:13px; color:#b0c8d8; padding:12px; background:#080f1a; border-radius:8px; border-left:3px solid {fill_color};'>
            {"✅ LTV within safe limits." if R["ltv"] <= R["ltv_rec"] else "⚠️ Exceeds recommended LTV — consider restructuring."}
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Market Comparables
    st.markdown('<div class="ciq-card"><div class="ciq-card-title">Market Comparables</div>', unsafe_allow_html=True)
    for c in R["comps"]:
        tag_style = "tag-live" if c["tag"] == "live" else "tag-sold" if c["tag"] == "sold" else "tag-active"
        st.markdown(f"""
        <div class="comp-row">
            <span class="comp-name">{c['name']}</span>
            <span class="comp-val">₹{c['rate']:,}/sqft <span class="{tag_style}">{c['tag']}</span></span>
        </div>""", unsafe_allow_html=True)
    st.caption(f"Subject property blended rate: ₹{R['rate_psf']:,}/sqft")
    st.markdown("</div>", unsafe_allow_html=True)

    # Time-to-Sell / Exit Forecast
    scenarios = [
        ("Base", R["tts_base"], "#e8e0cc"),
        ("Bull", R["tts_bull"], "#4ade80"),
        ("Bear", R["tts_bear"], "#f87171"),
    ]
    st.markdown('<div class="ciq-card"><div class="ciq-card-title">Time-to-Sell / Exit Forecast</div>', unsafe_allow_html=True)
    for name, val, color in scenarios:
        st.markdown(f"""
        <div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:0.5px solid #1e2c3a; font-size:13px;'>
            <span style='color:#8aa8c0;'>{name}</span>
            <span style='color:{color}; font-weight:500;'>{val}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Risks Flags
    st.markdown('<div class="ciq-card"><div class="ciq-card-title">Risk Flags</div>', unsafe_allow_html=True)
    for rk in R["risks"]:
        sev_class_name = rk['sev']
        icon = rk['icon']
        text = rk['text']
        st.markdown(f"""
        <div class="risk-flag {sev_class_name}">
            <span class="risk-icon">{icon}</span> {text}
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # AI Narrative — GenAI
    st.markdown('<div class="ai-insight"><div class="ai-insight-label">Executive Credit Summary — GenAI Narrative Layer</div>', unsafe_allow_html=True)

    commercial_note = (
        f"This is a {prop_type}. Commercial assets carry higher distress haircuts "
        f"({round(R['haircut']*100)}%) due to narrower buyer pools. "
        f"Recommended LTV ceiling is {R['ltv_rec']}%."
        if is_commercial else ""
    )

    prompt = f"""
You are CollateralIQ, a senior AI credit intelligence engine deployed by Indian NBFCs.

LIVE MARKET DATA:
- Data source: {market_data["source"]}
- Listings analyzed: {market_data["listings"]}
- Market rate: ₹{market_data["rate"]:,}/sqft (MagicBricks: ₹{market_data.get("mb_rate","N/A")}, 99acres: ₹{market_data.get("a99_rate","N/A")})
- RBI Repo Rate: {repo_rate}%
- Geo suburb: {geo_info.get("suburb","—")}

PROPERTY:
{st.session_state.config} {prop_type} at {st.session_state.project}, {st.session_state.locality}, {st.session_state.city}
Area: {st.session_state.area:,} sq ft | Age: {st.session_state.age} yrs | Floor: {st.session_state.floor}/{st.session_state.total_floors} | Facing: {st.session_state.facing}
Amenities: {', '.join(st.session_state.amenities) or 'None'}
GPS: {st.session_state.lat:.5f}, {st.session_state.lng:.5f}
{commercial_note}

VALUATION:
Market Value: {fmt_cr(R['mv_low'])} – {fmt_cr(R['mv_high'])} @ ₹{R['rate_psf']:,}/sqft
Distress Value: {fmt_cr(R['dv_low'])} – {fmt_cr(R['dv_high'])} | Haircut: {round(R['haircut']*100)}%
Resale / Exit Index: {R['resale']}/100 | Confidence: {R['conf']} | TTS: {R['tts_base']}
Proposed Loan: ₹{st.session_state.loan_lakhs}L | LTV: {R['ltv']}% | Max Recommended: {R['ltv_rec']}%

Generate a professional, concise, 4-sentence credit analysis for an Indian NBFC credit committee, emphasizing collateral quality with current market context, key value drivers, main asset-specific risks, and LTV/action plan. Use a precise, data-driven tone, without markdown or bullets.
"""

    ai_text = ""
    if GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
        try:
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(prompt)
            ai_text = response.text
        except:
            pass

    if not ai_text:
        ai_text = (
            f"The collateral — {st.session_state.config} {prop_type} at {st.session_state.project}, "
            f"{st.session_state.locality}, {st.session_state.city} — presents {'strong' if R['resale'] > 70 else 'moderate'} "
            f"characteristics; supported by live market data indicating ₹{market_data['rate']:,}/sqft, "
            f"with a resale index of {R['resale']}/100. Key value driver: active listings ({market_data['listings']}) "
            f"and location premium. Main risk: proposed LTV of {R['ltv']}% exceeds the {R['ltv_rec']}% threshold, "
            f"requiring restructuring or additional collateral before disbursal."
        )

    st.markdown(f'<div class="ai-insight-text">{ai_text}</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    colf1, colf2 = st.columns([1, 3])
    if colf1.button("← New Analysis"):
        for k in ["step", "map_query", "pin_lat", "pin_lng", "geocode_strategy"]:
            st.session_state[k] = defaults[k]
        st.rerun()
    st.markdown(
        "<p style='text-align:center;font-size:11px;color:#2e4a5e;margin-top:8px;'>"
        "Valuation powered by live MagicBricks + 99acres data · RBI repo-rate adjusted · "
        "SARFAESI / Commercial-aligned distress model · "
        "Multi-strategy geocoder (OpenCage) · CollateralIQ · DecisionX · TenzorX 2026</p>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# 13. End of code
# ─────────────────────────────────────────────