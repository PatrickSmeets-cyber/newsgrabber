import feedparser
import json
import os
import re
import random
import urllib.request
import urllib.parse
import uuid
import time
from datetime import datetime
import zoneinfo
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="google.genai")

from google import genai

# 1. TIJDZONE & UUR-CHECK (05:00 t/m 20:00 CET/CEST)
tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
now = datetime.now(tz)
current_hour = now.hour

print(f"Huidige tijd: {now.strftime('%Y-%m-%d %H:%M:%S')} (Uur: {current_hour})")

if not (5 <= current_hour <= 20):
    print("⏳ Buiten de actieve uren (05:00 - 20:00 uur). Geen update uitgevoerd.")
    exit(0)

last_updated = now.strftime("%d-%m-%Y om %H:%M uur")
today_str = now.strftime("%Y-%m-%d")
build_id = str(uuid.uuid4())[:8]

# 2. GEMINI CLIENT INITIALISEREN
api_key = os.environ.get("AI_API_KEY", "").strip()
ai_status = "Niet actief (geen API key)"
client = None

if api_key:
    try:
        client = genai.Client(api_key=api_key)
        ai_status = "Actief (Gemini 3.6 Flash)"
    except Exception as e:
        ai_status = f"Fout bij starten: {e}"

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 3. UITGEBREIDE FEEDS MET LANDCODERING (NL, EN, DE)
FEEDS = {
    "Wereld": [
        {"url": "https://feeds.nos.nl/nosnieuwsbuitenland", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.nu.nl/rss/Buitenland", "country": "NL", "flag": "🇳🇱"},
        {"url": "http://feeds.bbci.co.uk/news/world/rss.xml", "country": "GB", "flag": "🇬🇧"},
        {"url": "https://www.tagesschau.de/xml/rss2/", "country": "DE", "flag": "🇩🇪"},
        {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.aljazeera.com/xml/rss/all.xml", "country": "QA", "flag": "🇶🇦"},
        {"url": "https://rss.dw.com/rdf/rss-en-world", "country": "DE", "flag": "🇩🇪"},
        {"url": "https://www.lemonde.fr/en/rss/une.xml", "country": "FR", "flag": "🇫🇷"},
        {"url": "https://www.theguardian.com/world/rss", "country": "GB", "flag": "🇬🇧"}
    ],
    "Europa": [
        {"url": "https://feeds.nos.nl/nosnieuwseuropa", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.bnr.nl/rss/nieuws", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.politico.eu/feed/", "country": "EU", "flag": "🇪🇺"},
        {"url": "https://www.euronews.com/rss?format=xml", "country": "EU", "flag": "🇪🇺"},
        {"url": "https://www.spiegel.de/europa/index.rss", "country": "DE", "flag": "🇩🇪"},
        {"url": "https://www.bbc.com/news/world/europe/rss.xml", "country": "GB", "flag": "🇬🇧"},
        {"url": "https://www.lemonde.fr/europe/rss_full.xml", "country": "FR", "flag": "🇫🇷"},
        {"url": "https://www.irishtimes.com/crawled/rss/world/europe.xml", "country": "IE", "flag": "🇮🇪"},
        {"url": "https://www.brusselsjournal.com/rss.xml", "country": "BE", "flag": "🇧🇪"},
        {"url": "https://www.euractiv.com/feed/", "country": "EU", "flag": "🇪🇺"}
    ],
    "Nederland": [
        {"url": "https://feeds.nos.nl/nosnieuwsbinnenland", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.rtlnieuws.nl/rss.xml", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.nu.nl/rss/Binnenland", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.trouw.nl/binnenland/rss.xml", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.volkskrant.nl/nieuws-achtergrond/rss.xml", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.parool.nl/nederland/rss.xml", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.ad.nl/binnenland/rss.xml", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.telegraaf.nl/rss", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.nrc.nl/rss/", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.metrotime.be/nl/rss.xml", "country": "BE", "flag": "🇧🇪"}
    ],
    "Midden-Limburg": [
        {"url": "https://www.weertdegekste.nl/feed/", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.nederweert24.nl/feed/", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.l1nieuws.nl/rss/nieuws", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.limburger.nl/rss", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.middenlimburgactueel.nl/feed/", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.weert.nl/rss", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.roermond.nl/rss", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.1limburg.nl/rss", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.vilt.be/rss", "country": "BE", "flag": "🇧🇪"},
        {"url": "https://www.vvd-weert.nl/feed/", "country": "NL", "flag": "🇳🇱"}
    ],
    "Wiskunde & Wetenschap": [
        {"url": "https://www.nu.nl/rss/Wetenschap", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://feeds.nos.nl/nosnieuwswetenschap", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.sciencedaily.com/rss/all.xml", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.spektrum.de/alias/rss/spektrum-de-rss-feed/996406", "country": "DE", "flag": "🇩🇪"},
        {"url": "https://www.nature.com/nature.rss", "country": "GB", "flag": "🇬🇧"},
        {"url": "https://www.newscientist.com/feed/home/", "country": "GB", "flag": "🇬🇧"},
        {"url": "https://phys.org/rss-feed/", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.scientificamerican.com/feed/", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.kennislink.nl/feed/", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.quantamagazine.org/feed/", "country": "US", "flag": "🇺🇸"}
    ],
    "Technologie": [
        {"url": "https://www.bright.nl/rss", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.nu.nl/rss/Tech", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://feeds.arstechnica.com/arstechnica/index", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.heise.de/rss/heise-atom.xml", "country": "DE", "flag": "🇩🇪"},
        {"url": "https://tweakers.net/feeds/nieuws.xml", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.theverge.com/rss/index.xml", "country": "US", "flag": "🇺🇸"},
        {"url": "https://wired.com/feed/rss", "country": "US", "flag": "🇺🇸"},
        {"url": "https://techcrunch.com/feed/", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.golem.de/rss.php?feed=RSS2.0", "country": "DE", "flag": "🇩🇪"},
        {"url": "https://www.zdnet.com/news/rss.xml", "country": "US", "flag": "🇺🇸"}
    ],
    "Sport": [
        {"url": "https://feeds.nos.nl/nossport", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.nu.nl/rss/Sport", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.espn.com/espn/rss/news", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.kicker.de/news.rss", "country": "DE", "flag": "🇩🇪"},
        {"url": "https://www.voetbalzone.nl/rss/nieuws.xml", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.sportnieuws.nl/rss", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.bbc.com/sport/rss.xml", "country": "GB", "flag": "🇬🇧"},
        {"url": "https://www.skysports.com/rss/12040", "country": "GB", "flag": "🇬🇧"},
        {"url": "https://www.marca.com/en/rss/index.xml", "country": "ES", "flag": "🇪🇸"},
        {"url": "https://www.laola1.at/de/rss/", "country": "AT", "flag": "🇦🇹"}
    ],
    "Fitness & Resistance Training": [
        {"url": "https://www.fit.nl/feed", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.menshealth.com/nl/rss/all.xml/", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.menshealth.com/rss/all.xml/", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.ironman.com/news/rss", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.bodybuilding.com/rss/articles", "country": "US", "flag": "🇺🇸"},
        {"url": "https://startingstrength.com/feed", "country": "US", "flag": "🇺🇸"},
        {"url": "https://generationsiron.com/feed/", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.strongerbyscience.com/feed/", "country": "US", "flag": "🇺🇸"},
        {"url": "https://breakmuscle.com/feed/", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.t-nation.com/feed/", "country": "US", "flag": "🇺🇸"}
    ],
    "Humor & Luchtig": [
        {"url": "https://speld.nl/feed/", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.nu.nl/rss/Opmerkelijk", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.theonion.com/rss", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.postillon.com/feeds/posts/default?alt=rss", "country": "DE", "flag": "🇩🇪"},
        {"url": "https://www.humo.be/rss", "country": "BE", "flag": "🇧🇪"},
        {"url": "https://www.clickhole.com/feed/", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.duffelblog.com/feed", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.babylonbee.com/feed", "country": "US", "flag": "🇺🇸"},
        {"url": "https://www.vandaaginside.nl/rss.xml", "country": "NL", "flag": "🇳🇱"},
        {"url": "https://www.fok.nl/rss/nieuws", "country": "NL", "flag": "🇳🇱"}
    ]
}

# 4. WEERSVERWACHTING LOKAAL WEERT (INCL. WIND, NEERSLAG EN ONE-LINER)
weather_html_summary = "Weergegevens niet beschikbaar."

def kmh_to_bft(kmh):
    if kmh < 2: return 0
    elif kmh <= 5: return 1
    elif kmh <= 11: return 2
    elif kmh <= 19: return 3
    elif kmh <= 28: return 4
    elif kmh <= 38: return 5
    elif kmh <= 49: return 6
    elif kmh <= 61: return 7
    elif kmh <= 74: return 8
    elif kmh <= 88: return 9
    elif kmh <= 102: return 10
    elif kmh <= 117: return 11
    else: return 12

def weather_code_to_desc(code):
    codes = {
        0: "Helder en zonnig", 1: "Vrijwel helder", 2: "Licht bewolkt", 3: "Bewolkt",
        45: "Mistig", 48: "Rijpnevel", 51: "Lichte motregen", 53: "Motregen", 55: "Dichte motregen",
        61: "Lichte regen", 63: "Matige regen", 65: "Zware regen", 71: "Lichte sneeuw",
        73: "Matige sneeuw", 75: "Zware sneeuw", 80: "Lichte buien", 81: "Matige buien",
        82: "Hevige buien", 95: "Onweersbui"
    }
    return codes.get(code, "Wisselvallig weer")

try:
    url_w = "https://api.open-meteo.com/v1/forecast?latitude=51.2517&longitude=5.7068&current_weather=true&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode&timezone=Europe%2FAmsterdam"
    req_w = urllib.request.Request(url_w, headers=HEADERS)
    w_data = json.loads(urllib.request.urlopen(req_w, timeout=5).read())
    
    cur_temp = round(w_data['current_weather']['temperature'])
    cur_wind = round(w_data['current_weather']['windspeed'])
    cur_bft = kmh_to_bft(cur_wind)
    cur_code = w_data['current_weather']['weathercode']
    
    daily_dates = w_data['daily']['time']
    daily_max = w_data['daily']['temperature_2m_max']
    daily_min = w_data['daily']['temperature_2m_min']
    daily_precip = w_data['daily']['precipitation_sum']
    daily_wind = w_data['daily']['windspeed_10m_max']
    
    cur_today_precip = daily_precip[0] if len(daily_precip) > 0 else 0.0
    weather_desc = weather_code_to_desc(cur_code)
    
    one_liner = f"Vandaag in Weert: {weather_desc.lower()} met hoogstens {round(daily_max[0])}°C, {cur_bft} Bft wind en {cur_today_precip}mm neerslag."
    
    days_html = ""
    for idx in range(min(7, len(daily_dates))):
        d_obj = datetime.strptime(daily_dates[idx], "%Y-%m-%d")
        day_name = d_obj.strftime("%a")
        d_max = round(daily_max[idx])
        d_min = round(daily_min[idx])
        d_rain = round(daily_precip[idx], 1)
        d_bft = kmh_to_bft(daily_wind[idx])
        
        days_html += f"""
        <div style='text-align:center; padding: 4px 2px; background: rgba(255,255,255,0.03); border-radius:6px;'>
            <span style='color:#90e0ef; font-size:0.75rem; font-weight:bold;'>{day_name}</span><br>
            <b style='font-size:0.85rem;'>{d_max}°</b> <small style='color:#cbd5e1;'>{d_min}°</small><br>
            <span style='font-size:0.7rem; color:#4cc9f0;'>💧 {d_rain}m</span><br>
            <span style='font-size:0.7rem; color:#cbd5e1;'>💨 {d_bft}Bft</span>
        </div>
        """
        
    weather_html_summary = f"""
    <div style='margin-bottom:8px;'>
        <b>📍 Weert nu: {cur_temp}°C</b> <span style='font-size:0.8rem; color:#caf0f8;'>({weather_desc})</span>
        <br><small style='color:#cbd5e1;'>Wind: {cur_wind} km/h ({cur_bft} Bft) | Neerslag vandaag: {cur_today_precip} mm</small>
    </div>
    <div style='font-size:0.8rem; color:#00b4d8; font-style:italic; margin-bottom:10px; padding:4px 8px; background:rgba(0,180,216,0.1); border-radius:6px;'>
        💬 {one_liner}
    </div>
    <div style='display:grid; grid-template-columns: repeat(7, 1fr); gap:4px;'>
        {days_html}
    </div>
    """
except Exception as e:
    print(f"Weerfout: {e}")

# 5. SPREUK EN TIP
daily_quote = "De enige constante in het leven is verandering."
daily_quote_author = "Heraclitus"
daily_tip = "Neem elk uur even 2 minuten afstand van je scherm om je ogen rust te geven."

if client:
    try:
        prompt_extras = (
            "Bedenk voor vandaag (in het Nederlands):\n"
            "1. Een inspirerende quote inclusief auteur.\n"
            "2. Een unieke, praktische dagelijkse tip op het gebied van productiviteit, fitness of gezondheid.\n"
            "Geef antwoord exact als JSON: {\"quote\": \"...\", \"auteur\": \"...\", \"tip\": \"...\"}"
        )
        res_extras = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt_extras,
            config={'response_mime_type': 'application/json', 'tools': []}
        )
        data_extras = json.loads(res_extras.text.strip())
        daily_quote = data_extras.get("quote", daily_quote)
        daily_quote_author = data_extras.get("auteur", daily_quote_author)
        daily_tip = data_extras.get("tip", daily_tip)
    except Exception as err:
        print(f"⚠️ Fout bij genereren Spreuk/Tip: {err}")

def clean_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'### (.*?)\n', r'<h4 style="color:#00b4d8; margin-top:15px; margin-bottom:5px;">\1</h4>', text)
    text = re.sub(r'\* (.*?)\n', r'• \1<br>', text)
    return text.replace("\n", "<br>")

def strip_tags(text):
    return re.sub('<[^<]+?>', '', text)

def extract_domain_name(url):
    try:
        domain = urllib.parse.urlparse(url).netloc
        domain = domain.replace('www.', '').split('.')[0]
        return domain.capitalize()
    except Exception:
        return "Bron"

def get_guaranteed_image(item_id):
    """ Genereert een gegarandeerde, unieke foto via Picsum Photos """
    return f"https://picsum.photos/seed/{item_id}/800/600"

def extract_feed_image(entry, item_id):
    if 'media_content' in entry and entry.media_content:
        for media in entry.media_content:
            if 'url' in media and media['url'].startswith('http'):
                return media['url']
    if 'enclosures' in entry and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image') and enc.get('href', '').startswith('http'):
                return enc.get('href')
    
    desc = entry.get('summary', '') or entry.get('description', '')
    img_match = re.search(r'<img [^>]*src=["\'](https?://[^"\']+)["\']', desc)
    if img_match:
        return img_match.group(1)
        
    return get_guaranteed_image(item_id)

# 6. FEEDS VERZAMELEN MET STRIKTE SCHEIDING EN ONTDUBBELING
all_headlines_with_sources = []
ticker_headlines = []
feed_results = {}
seen_titles = set()

for cat, feed_list in FEEDS.items():
    pool_items = []
    for f_info in feed_list:
        url = f_info["url"]
        country = f_info["country"]
        flag = f_info["flag"]
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            if feed.entries:
                for entry in feed.entries:
                    clean_t = re.sub(r'[^\w\s]', '', entry.title.lower()).strip()
                    if clean_t not in seen_titles:
                        seen_titles.add(clean_t)
                        entry['country_code'] = country
                        entry['country_flag'] = flag
                        entry['category'] = cat  # Borg strikte categorisering
                        pool_items.append(entry)
                        
                        # Bewaar headline voor ticker-tape
                        ticker_headlines.append({
                            "title": entry.title,
                            "flag": flag,
                            "country": country,
                            "source": extract_domain_name(entry.get("link", ""))
                        })
        except Exception as err:
            print(f"Feed fout {url}: {err}")
            
    random.shuffle(pool_items)
    feed_results[cat] = pool_items
    for entry in pool_items[:4]:
        all_headlines_with_sources.append({
            "title": entry.title,
            "link": entry.get("link", ""),
            "category": cat
        })

# Selecteer de 30 meest recente unieke headlines voor de ticker-tape
recent_ticker_items = ticker_headlines[:30]
ticker_items_html = ""
for t_item in recent_ticker_items:
    ticker_items_html += f'<span class="ticker-item"><span class="ticker-flag">{t_item["flag"]} {t_item["country"]}</span> <b>{t_item["source"]}:</b> {t_item["title"]}</span>'

# 7. OPINIESTUK GENEREREN OF CACHE LADEN
OPINION_CACHE_FILE = "opinion_cache.json"
opinion_data = None

if os.path.exists(OPINION_CACHE_FILE):
    try:
        with open(OPINION_CACHE_FILE, "r", encoding="utf-8") as f:
            cached = json.load(f)
            if cached.get("date") == today_str:
                opinion_data = cached.get("data")
                print("ℹ️ Opiniestuk van vandaag geladen uit cache.")
    except Exception as e:
        print(f"Cache leesfout: {e}")

if not opinion_data and client and all_headlines_with_sources:
    try:
        sample = random.sample(all_headlines_with_sources, min(len(all_headlines_with_sources), 12))
        prompt = (
            f"Gebruik de volgende actuele nieuwsheadlines:\n"
            f"{json.dumps(sample, ensure_ascii=False)}\n\n"
            f"Opdracht:\n"
            f"1. Kies het meest maatschappelijk relevante onderwerp.\n"
            f"2. Schrijf een sterk achtergrond- en opinieartikel in het Nederlands.\n"
            f"3. Geef een nauwkeurige Nederlandse caption die aansluit bij de foto.\n"
            f"4. Geef een betrouwbaarheidsindicator als percentage (0-100%) op basis van feiten, plus toelichting.\n\n"
            f"Geef antwoord als JSON:\n"
            f"{{\n"
            f'  "titel": "Pakkende Nederlandse titel",\n'
            f'  "samenvatting": "Korte samenvatting in 2 zinnen in het Nederlands",\n'
            f'  "inhoud": "### Kerninzichten\\n* [Punt 1]\\n* [Punt 2]\\n\\n### Diepgaande Analyse\\n[Tekst]\\n\\n### Conclusie\\n[Conclusie]",\n'
            f'  "image_caption": "Gedetailleerde Nederlandse beschrijving van het visuele beeld",\n'
            f'  "reliability_score": 88,\n'
            f'  "reliability_reason": "Gebaseerd op meervoudige geverifieerde bronnen."\n'
            f"}}"
        )
        res = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json', 'tools': []}
        )
        data = json.loads(res.text.strip())
        
        opinion_data = {
            "titel": data.get("titel", "Actueel Maatschappelijk Debat"),
            "samenvatting": data.get("samenvatting", ""),
            "inhoud": clean_markdown(data.get("inhoud", "")),
            "image_caption": data.get("image_caption", "Sfeerbeeld van het maatschappelijk debat"),
            "reliability_score": data.get("reliability_score", 85),
            "reliability_reason": data.get("reliability_reason", "Meervoudig geverifieerde bronnen."),
            "img": get_guaranteed_image("opinion_today_1")
        }
        with open(OPINION_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"date": today_str, "data": opinion_data}, f, ensure_ascii=False)
        print(f"✅ Nieuw AI Opiniestuk gegenereerd: {opinion_data['titel']}")
    except Exception as err:
        print(f"❌ AI Opinie Fout: {err}")
        opinion_data = {
            "titel": "Maatschappelijk Dossier",
            "samenvatting": "Kon geen nieuw dossier genereren.",
            "inhoud": f"Fout bij genereren: {err}",
            "image_caption": "Nieuwsoverzicht van de dag",
            "reliability_score": 50,
            "reliability_reason": "Onvoldoende data voor verificatie.",
            "img": get_guaranteed_image("fallback_op")
        }

# 8. REGULIERE ARTIKELEN VERZAMELEN
modal_data = {}
article_id = 0

article_id += 1
modal_data[str(article_id)] = {
    "title": opinion_data["titel"],
    "category": "Dagelijks Opinie-Dossier",
    "img": opinion_data["img"],
    "caption": opinion_data["image_caption"],
    "ai_summary": opinion_data["samenvatting"],
    "full_text": opinion_data["inhoud"],
    "reliability_score": opinion_data.get("reliability_score", 85),
    "reliability_reason": opinion_data.get("reliability_reason", ""),
    "source_name": "Opinie Redactie",
    "country_code": "NL",
    "country_flag": "🇳🇱",
    "is_background": True
}

featured_html = f"""
<div class="featured-banner" onclick="openArticle('1')">
    <div class="featured-img-wrapper">
        <img src="{opinion_data['img']}" alt="{opinion_data['titel']}">
        <span class="badge badge-featured">🔥 Dagelijks Opinie-Dossier</span>
    </div>
    <div class="featured-content">
        <h2>{opinion_data['titel']}</h2>
        <p>{opinion_data['samenvatting']}</p>
        <div style="font-size:0.8rem; color:#4cc9f0; margin-top:8px;"><b>🛡️ Betrouwbaarheidsindicator:</b> {opinion_data.get('reliability_score', 85)}% <small style="color:#cbd5e1;">({opinion_data.get('reliability_reason', '')})</small></div>
        <div style="font-size:0.75rem; color:#ffb703; margin-top:6px;">📷 {opinion_data['image_caption']}</div>
        <div class="read-more">Lees het volledige opiniedossier &rarr;</div>
    </div>
</div>
"""

category_counts = {
    "Wereld": 3, "Europa": 3, "Nederland": 3, "Midden-Limburg": 3,
    "Wiskunde & Wetenschap": 3, "Technologie": 3, "Sport": 3,
    "Fitness & Resistance Training": 3, "Humor & Luchtig": 1
}

articles_to_process = []
for cat, count in category_counts.items():
    items = feed_results.get(cat, [])[:count]
    for item in items:
        # Extra controle op categorie borgen
        if cat == "Midden-Limburg" and item.get("category") != "Midden-Limburg":
            continue
            
        article_id += 1
        clean_sum = strip_tags(item.get('summary', item.get('description', '')))
        item_link = item.get('link', '#')
        source_name = extract_domain_name(item_link)
        img_url = extract_feed_image(item, f"art_{article_id}")
        
        articles_to_process.append({
            "id": str(article_id),
            "title": item.title,
            "category": cat,
            "link": item_link,
            "source_name": source_name,
            "country_code": item.get("country_code", "NL"),
            "country_flag": item.get("country_flag", "🇳🇱"),
            "clean_sum": clean_sum,
            "img_url": img_url
        })

# BATCH AI PROCESS (Vertaling, Samenvatting & Captions)
processed_summaries = {}
if client and articles_to_process:
    try:
        input_payload = [{"id": a["id"], "title": a["title"], "text": a["clean_sum"][:300]} for a in articles_to_process]
        batch_prompt = (
            f"Verwerk de volgende lijst nieuwsartikelen:\n{json.dumps(input_payload, ensure_ascii=False)}\n\n"
            f"Instructies per artikel ID:\n"
            f"1. ALS de titel/tekst NIET in het Nederlands, Engels of Duits is, vertaal deze naar het Nederlands.\n"
            f"2. Maak een heldere samenvatting in max 2 zinnen (Nederlands).\n"
            f"3. Schrijf een bijpassende caption in het Nederlands die de inhoud van de foto toelicht.\n\n"
            f"Geef antwoord als JSON dictionary met het artikel ID als key:\n"
            f"{{\n"
            f'  "2": {{"title": "Gevraagde titel (vertaald indien nodig)", "summary": "...", "caption": "..."}}\n'
            f"}}"
        )
        res_batch = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=batch_prompt,
            config={'response_mime_type': 'application/json', 'tools': []}
        )
        processed_summaries = json.loads(res_batch.text.strip())
        print(f"✅ Batch verwerking geslaagd voor {len(processed_summaries)} artikelen.")
    except Exception as err:
        print(f"⚠️ Batch AI Fout: {err}")

articles_html = ""
for item in articles_to_process:
    aid = item["id"]
    ai_data = processed_summaries.get(aid, {})
    
    final_title = ai_data.get("title", item["title"])
    ai_summary = ai_data.get("summary", item["clean_sum"][:130] + "...")
    img_caption = ai_data.get("caption", f"Afbeelding ter illustratie bij: {final_title[:30]}")
    final_img_url = item["img_url"]
    
    modal_data[aid] = {
        "title": final_title,
        "category": item["category"],
        "img": final_img_url,
        "caption": img_caption,
        "ai_summary": ai_summary,
        "full_text": item["clean_sum"],
        "original_link": item["link"],
        "source_name": item["source_name"],
        "country_code": item["country_code"],
        "country_flag": item["country_flag"],
        "is_background": False
    }

    # Bepaal of kaart de volle breedte moet beslaan (bijv. voor Humor & Luchtig)
    full_width = " card-full-width" if item["category"] == "Humor & Luchtig" else ""
    articles_html += f"""
    <div class="card{full_width}" onclick="openArticle('{aid}')">
        <div class="card-img-wrapper">
            <img src="{final_img_url}" alt="{final_title}">
            <span class="badge">{item['category']}</span>
            <span class="badge-source">{item['country_flag']} {item['country_code']} • {item['source_name']}</span>
        </div>
        <div class="card-content">
            <h3>{final_title}</h3>
            <p>{ai_summary}</p>
            <div style="font-size:0.75rem; color:#90e0ef; margin-top:8px;">📷 {img_caption}</div>
            <div class="read-more">Lees bericht &rarr;</div>
        </div>
    </div>
    """

json_modal_data = json.dumps(modal_data).replace('</', r'<\/')

# 9. HTML LAYOUT OPBOUWEN
html_content = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Cache-Control Meta Tags voor directe verversing -->
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">

    <title>Patrick’s Nieuwsboard</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0b132b; margin: 0; padding: 20px; color: #e0e6ed; }}
        header {{ text-align: center; padding: 25px 15px 15px 15px; background: linear-gradient(135deg, #1c2541, #3a506b, #00b4d8); color: #ffffff; border-radius: 16px; margin-bottom: 25px; }}
        
        /* TICKER TAPE STYLES */
        .ticker-wrap {{ width: 100%; background: rgba(11, 19, 43, 0.6); overflow: hidden; height: 38px; line-height: 38px; border-radius: 8px; margin-top: 15px; border: 1px solid rgba(0, 180, 216, 0.4); display: flex; align-items: center; }}
        .ticker-icon {{ background: #00b4d8; color: #0b132b; padding: 0 12px; font-size: 1.1rem; height: 100%; display: flex; align-items: center; justify-content: center; z-index: 2; }}
        .ticker-move {{ display: inline-block; white-space: nowrap; padding-left: 100%; animation: ticker 150s linear infinite; }}
        .ticker-wrap:hover .ticker-move {{ animation-play-state: paused; }}
        .ticker-item {{ display: inline-block; padding: 0 25px; font-size: 0.85rem; color: #caf0f8; }}
        .ticker-flag {{ font-size: 0.75rem; opacity: 0.9; margin-right: 4px; }}
        @keyframes ticker {{
            0% {{ transform: translate3d(0, 0, 0); }}
            100% {{ transform: translate3d(-100%, 0, 0); }}
        }}

        .widget-bar {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 25px; }}
        .widget {{ background: #1c2541; padding: 16px; border-radius: 12px; border-left: 4px solid #00b4d8; }}
        .widget-title {{ font-size: 0.75rem; text-transform: uppercase; color: #90e0ef; font-weight: bold; margin-bottom: 5px; }}

        .featured-banner {{ width: 100%; background: #1e293b; border-radius: 16px; border: 2px solid #ffb703; overflow: hidden; margin-bottom: 25px; cursor: pointer; display: flex; flex-direction: column; }}
        @media (min-width: 768px) {{ .featured-banner {{ flex-direction: row; height: 340px; }} .featured-img-wrapper {{ width: 50%; height: 100% !important; }} .featured-content {{ width: 50%; padding: 30px !important; }} }}
        .featured-img-wrapper {{ position: relative; height: 200px; }}
        .featured-img-wrapper img {{ width: 100%; height: 100%; object-fit: cover; }}
        .badge-featured {{ background: #ffb703; color: #000; position: absolute; top: 15px; left: 15px; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 0.8rem; }}
        .featured-content {{ padding: 20px; display: flex; flex-direction: column; justify-content: center; }}
        .featured-content h2 {{ margin: 0 0 10px 0; color: #ffffff; font-size: 1.4rem; }}

        .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
        @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        .card {{ background: #1c2541; border-radius: 14px; overflow: hidden; border: 1px solid #3a506b; cursor: pointer; display: flex; flex-direction: column; }}
        
        /* STYLING VOOR VOLLEDIGE BREEDTE (O.A. HUMOR & LUCHTIG) */
        .card-full-width {{ grid-column: 1 / -1; }}
        
        .card-img-wrapper {{ position: relative; height: 160px; }}
        .card img {{ width: 100%; height: 100%; object-fit: cover; }}
        .badge {{ position: absolute; top: 10px; left: 10px; background: rgba(0, 180, 216, 0.9); color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: bold; }}
        .badge-source {{ position: absolute; bottom: 10px; right: 10px; background: rgba(11, 19, 43, 0.85); color: #90e0ef; padding: 3px 8px; border-radius: 8px; font-size: 0.7rem; font-weight: bold; border: 1px solid #3a506b; }}
        .card-content {{ padding: 15px; flex-grow: 1; display: flex; flex-direction: column; }}
        h3 {{ margin: 0 0 10px 0; font-size: 1rem; color: #caf0f8; }}
        p {{ font-size: 0.85rem; color: #cbd5e1; margin: 0; flex-grow: 1; }}
        .read-more {{ margin-top: 10px; font-size: 0.8rem; color: #00b4d8; font-weight: bold; }}

        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(11, 19, 43, 0.9); z-index: 1000; overflow-y: auto; padding: 20px; }}
        .modal-container {{ max-width: 700px; margin: 20px auto; background: #1c2541; border-radius: 16px; border: 1px solid #00b4d8; overflow: hidden; padding: 20px; }}
        .modal-actions {{ display: flex; gap: 10px; margin-top: 20px; }}
        .btn {{ padding: 10px 15px; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; text-decoration: none; }}
        .btn-back {{ background: #3a506b; color: white; }}
        .btn-source {{ background: #00b4d8; color: white; }}
        
        footer {{ margin-top: 40px; text-align: center; font-size: 0.75rem; color: #64748b; border-top: 1px solid #1e293b; padding-top: 15px; }}
    </style>
</head>
<body>
    <header>
        <h1 style="margin: 0 0 5px 0;">⚡ Patrick’s Nieuwsboard</h1>
        <p style="margin: 0;">Laatst bijgewerkt: <b>{last_updated}</b> (Actieve uren: 05:00-20:00 CET)</p>
        
        <!-- TICKER TAPE BAR -->
        <div class="ticker-wrap">
            <div class="ticker-icon">📡</div>
            <div class="ticker-move">
                {ticker_items_html}
            </div>
        </div>
    </header>
    
    <div class="widget-bar">
        <div class="widget" style="grid-column: span 2;">
            <div class="widget-title">🌤️ Weersverwachting Weert</div>
            <div class="widget-body">{weather_html_summary}</div>
        </div>
        <div class="widget">
            <div class="widget-title">💡 Spreuk van de dag</div>
            <div class="widget-body"><small><i>"{daily_quote}"</i><br><b>— {daily_quote_author}</b></small></div>
        </div>
        <div class="widget">
            <div class="widget-title">📌 Praktische Tip</div>
            <div class="widget-body"><small>{daily_tip}</small></div>
        </div>
    </div>

    {featured_html}

    <div class="grid">
        {articles_html}
    </div>

    <!-- OPSCHOONING FOOTER -->
    <footer>
        <p>Build ID: <code>{build_id}</code> | AI Engine: Gemini 3.6 Flash</p>
    </footer>

    <div id="modalOverlay" class="modal-overlay" onclick="if(event.target.id==='modalOverlay') closeModal();">
        <div class="modal-container">
            <img id="modalImg" style="width:100%; height:240px; object-fit:cover; border-radius:8px;" src="" alt="">
            <div id="modalCaption" style="font-size:0.8rem; color:#90e0ef; margin-top:6px; font-style:italic;"></div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                <span id="modalBadge" style="background:#00b4d8; color:white; padding:3px 8px; border-radius:10px; font-size:0.7rem; font-weight:bold;"></span>
                <span id="modalSourceBadge" style="background:#0b132b; color:#90e0ef; padding:3px 8px; border-radius:8px; font-size:0.75rem; border:1px solid #3a506b;"></span>
            </div>
            <h2 id="modalTitle" style="color:white; font-size:1.3rem; margin-top:10px;"></h2>
            <div id="modalReliability" style="display:none; background:#0f172a; padding:8px 12px; border-radius:8px; border-left:3px solid #ffb703; margin:10px 0; font-size:0.85rem; color:#e2e8f0;"></div>
            <div id="modalAiBox" style="background:#0b132b; padding:10px; border-left:3px solid #00b4d8; margin:10px 0; color:#90e0ef; font-size:0.9rem;"></div>
            <div id="modalFullText" style="line-height:1.6; font-size:0.9rem;"></div>
            <div class="modal-actions">
                <button class="btn btn-back" onclick="closeModal()">&larr; Terug</button>
                <a id="modalSourceLink" class="btn btn-source" href="#" target="_blank">Origineel &rarr;</a>
            </div>
        </div>
    </div>

    <script>
        const articlesData = {json_modal_data};

        function openArticle(id) {{
            const a = articlesData[id];
            if (!a) return;
            document.getElementById('modalImg').src = a.img;
            document.getElementById('modalCaption').innerText = '📷 ' + a.caption;
            document.getElementById('modalBadge').innerText = a.category;
            document.getElementById('modalSourceBadge').innerText = (a.country_flag || '') + ' ' + (a.country_code || '') + ' • ' + (a.source_name || '');
            document.getElementById('modalTitle').innerText = a.title;
            
            const relBox = document.getElementById('modalReliability');
            if (a.reliability_score !== undefined) {{
                relBox.style.display = 'block';
                relBox.innerHTML = '<b>🛡️ Betrouwbaarheidsindicator: ' + a.reliability_score + '%</b><br><small style="color:#cbd5e1;">' + (a.reliability_reason || '') + '</small>';
            }} else {{
                relBox.style.display = 'none';
            }}

            document.getElementById('modalAiBox').innerHTML = '<b>Samenvatting & Context:</b><br>' + a.ai_summary;
            document.getElementById('modalFullText').innerHTML = a.full_text;
            
            const srcBtn = document.getElementById('modalSourceLink');
            if (a.is_background) {{ 
                srcBtn.style.display = 'none'; 
            }} else {{ 
                srcBtn.style.display = 'inline-block'; 
                srcBtn.href = a.original_link; 
                srcBtn.innerText = 'Origineel (' + (a.source_name || 'Bron') + ') \u2192';
            }}
            
            document.getElementById('modalOverlay').style.display = 'block';
        }}

        function closeModal() {{
            document.getElementById('modalOverlay').style.display = 'none';
        }}

        document.addEventListener("visibilitychange", function() {{
            if (document.visibilityState === "visible") {{
                window.location.reload(true);
            }}
        }});
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ index.html gegenereerd! Build ID: {build_id}")
