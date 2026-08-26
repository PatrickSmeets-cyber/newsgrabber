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

# Draai alleen tussen 05:00 en 20:00 uur (inclusief 20:xx)
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

# 3. UITGEBREIDE FEEDS (Minimaal 10 top relevante bronnen per rubriek: NL, EN, DE)
FEEDS = {
    "Wereld": [
        "https://feeds.nos.nl/nosnieuwsbuitenland",
        "https://www.nu.nl/rss/Buitenland",
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.tagesschau.de/xml/rss2/",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.dw.com/rdf/rss-en-world",
        "https://www.lemonde.fr/en/rss/une.xml",
        "https://www.theguardian.com/world/rss"
    ],
    "Europa": [
        "https://feeds.nos.nl/nosnieuwseuropa",
        "https://www.bnr.nl/rss/nieuws",
        "https://www.politico.eu/feed/",
        "https://www.euronews.com/rss?format=xml",
        "https://www.spiegel.de/europa/index.rss",
        "https://www.bbc.com/news/world/europe/rss.xml",
        "https://www.lemonde.fr/europe/rss_full.xml",
        "https://www.irishtimes.com/crawled/rss/world/europe.xml",
        "https://www.brusselsjournal.com/rss.xml",
        "https://www.euractiv.com/feed/"
    ],
    "Nederland": [
        "https://feeds.nos.nl/nosnieuwsbinnenland",
        "https://www.rtlnieuws.nl/rss.xml",
        "https://www.nu.nl/rss/Binnenland",
        "https://www.trouw.nl/binnenland/rss.xml",
        "https://www.volkskrant.nl/nieuws-achtergrond/rss.xml",
        "https://www.parool.nl/nederland/rss.xml",
        "https://www.ad.nl/binnenland/rss.xml",
        "https://www.telegraaf.nl/rss",
        "https://www.nrc.nl/rss/",
        "https://www.metrotime.be/nl/rss.xml"
    ],
    "Midden-Limburg": [
        "https://www.weertdegekste.nl/feed/",
        "https://www.nederweert24.nl/feed/",
        "https://www.l1nieuws.nl/rss/nieuws",
        "https://www.limburger.nl/rss",
        "https://www.middenlimburgactueel.nl/feed/",
        "https://www.weert.nl/rss",
        "https://www.roermond.nl/rss",
        "https://www.1limburg.nl/rss",
        "https://www.vilt.be/rss",
        "https://www.vvd-weert.nl/feed/"
    ],
    "Wiskunde & Wetenschap": [
        "https://www.nu.nl/rss/Wetenschap",
        "https://feeds.nos.nl/nosnieuwswetenschap",
        "https://www.sciencedaily.com/rss/all.xml",
        "https://www.spektrum.de/alias/rss/spektrum-de-rss-feed/996406",
        "https://www.nature.com/nature.rss",
        "https://www.newscientist.com/feed/home/",
        "https://phys.org/rss-feed/",
        "https://www.scientificamerican.com/feed/",
        "https://www.kennislink.nl/feed/",
        "https://www.quantamagazine.org/feed/"
    ],
    "Technologie": [
        "https://www.bright.nl/rss",
        "https://www.nu.nl/rss/Tech",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.heise.de/rss/heise-atom.xml",
        "https://tweakers.net/feeds/nieuws.xml",
        "https://www.theverge.com/rss/index.xml",
        "https://wired.com/feed/rss",
        "https://techcrunch.com/feed/",
        "https://www.golem.de/rss.php?feed=RSS2.0",
        "https://www.zdnet.com/news/rss.xml"
    ],
    "Sport": [
        "https://feeds.nos.nl/nossport",
        "https://www.nu.nl/rss/Sport",
        "https://www.espn.com/espn/rss/news",
        "https://www.kicker.de/news.rss",
        "https://www.voetbalzone.nl/rss/nieuws.xml",
        "https://www.sportnieuws.nl/rss",
        "https://www.bbc.com/sport/rss.xml",
        "https://www.skysports.com/rss/12040",
        "https://www.marca.com/en/rss/index.xml",
        "https://www.laola1.at/de/rss/"
    ],
    "Fitness & Resistance Training": [
        "https://www.fit.nl/feed",
        "https://www.menshealth.com/nl/rss/all.xml/",
        "https://www.menshealth.com/rss/all.xml/",
        "https://www.ironman.com/news/rss",
        "https://www.bodybuilding.com/rss/articles",
        "https://startingstrength.com/feed",
        "https://generationsiron.com/feed/",
        "https://www.strongerbyscience.com/feed/",
        "https://breakmuscle.com/feed/",
        "https://www.t-nation.com/feed/"
    ],
    "Humor & Luchtig": [
        "https://speld.nl/feed/",
        "https://www.nu.nl/rss/Opmerkelijk",
        "https://www.theonion.com/rss",
        "https://www.postillon.com/feeds/posts/default?alt=rss",
        "https://www.humo.be/rss",
        "https://www.clickhole.com/feed/",
        "https://www.duffelblog.com/feed",
        "https://www.babylonbee.com/feed",
        "https://www.vandaaginside.nl/rss.xml",
        "https://www.fok.nl/rss/nieuws"
    ]
}

# 4. WEERSVERWACHTING LOKAAL WEERT (51.2517 N, 5.7068 E)
weather_html_summary = "Weergegevens niet beschikbaar."
try:
    url_w = "https://api.open-meteo.com/v1/forecast?latitude=51.2517&longitude=5.7068&current_weather=true&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Europe%2FAmsterdam"
    req_w = urllib.request.Request(url_w, headers=HEADERS)
    w_data = json.loads(urllib.request.urlopen(req_w, timeout=5).read())
    
    cur_temp = round(w_data['current_weather']['temperature'])
    daily_dates = w_data['daily']['time']
    daily_max = w_data['daily']['temperature_2m_max']
    daily_min = w_data['daily']['temperature_2m_min']
    
    days_html = ""
    for idx in range(min(7, len(daily_dates))):
        d_obj = datetime.strptime(daily_dates[idx], "%Y-%m-%d")
        day_name = d_obj.strftime("%a")
        days_html += f"<div style='text-align:center; padding: 2px 4px;'><span style='color:#90e0ef; font-size:0.75rem;'>{day_name}</span><br><b style='font-size:0.85rem;'>{round(daily_max[idx])}°</b> <small style='color:#cbd5e1;'>{round(daily_min[idx])}°</small></div>"
        
    weather_html_summary = f"<b>📍 Weert nu: {cur_temp}°C</b><div style='display:flex; justify-content:space-between; margin-top:8px;'>{days_html}</div>"
except Exception as e:
    print(f"Weerfout: {e}")

# 5. DYNAMISCHE SPREUK EN TIP (1 API Call)
daily_quote = "De enige constante in het leven is verandering."
daily_quote_author = "Heraclitus"
daily_tip = "Neem elk uur even 2 minuten afstand van je scherm om je ogen rust te geven."

if client:
    try:
        prompt_extras = (
            "Bedenk voor vandaag:\n"
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

# Dynamic Context-Based Image Generator (Unsplash Topic Specific)
def get_topic_image_url(title, category):
    keywords = re.findall(r'\b[a-zA-Z]{4,}\b', title.lower())
    query = ",".join(keywords[:2]) if keywords else category.lower()
    return f"https://source.unsplash.com/featured/800x600/?{urllib.parse.quote(query)}"

def extract_feed_image(entry, default_category, title):
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
        
    return get_topic_image_url(title, default_category)

# 6. FEEDS VERZAMELEN MET ONTDUBBELING
all_headlines_with_sources = []
feed_results = {}
seen_titles = set()

for cat, urls in FEEDS.items():
    pool_items = []
    for url in urls:
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            if feed.entries:
                for entry in feed.entries:
                    # Ontdubbeling op basis van opgeschoonde titel
                    clean_t = re.sub(r'[^\w\s]', '', entry.title.lower()).strip()
                    if clean_t not in seen_titles:
                        seen_titles.add(clean_t)
                        pool_items.append(entry)
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

# 7. OPINIESTUK GENEREREN OF UIT CACHE LADEN (1x per dag) + Betrouwbaarheidsindicator
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
            f"2. Schrijf een sterk, pakkend achtergrond- en opinieartikel met een specifieke, aansprekende titel.\n"
            f"3. Geef een visuele beschrijving voor een bijpassend beeld (image_caption) dat exact beschrijft wat er op de afbeelding te zien is en past bij de inhoud.\n"
            f"4. Bepaal een betrouwbaarheidsindicator als percentage (score 0-100%) op basis van de gebruikte bronnen en de verifieerbaarheid van de feiten, en geef een korte toelichting.\n\n"
            f"Geef antwoord als JSON:\n"
            f"{{\n"
            f'  "titel": "Pakkende specifieke titel",\n'
            f'  "samenvatting": "Korte samenvatting in 2 zinnen",\n'
            f'  "inhoud": "### Kerninzichten\\n* [Punt 1]\\n* [Punt 2]\\n\\n### Diepgaande Analyse\\n[Tekst]\\n\\n### Conclusie\\n[Conclusie]",\n'
            f'  "image_caption": "Gedetailleerde beschrijving die exact aansluit op de afbeelding en tekst",\n'
            f'  "reliability_score": 85,\n'
            f'  "reliability_reason": "Gebaseerd op meervoudige internationale kwaliteitsmediameldingen."\n'
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
            "img": get_topic_image_url(data.get("titel", "news"), "Wereld")
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
            "image_caption": "Nieuwsoverzicht",
            "reliability_score": 50,
            "reliability_reason": "Onvoldoende data voor verificatie.",
            "img": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200"
        }

# 8. REGULIERE ARTIKELEN VERZAMELEN & BATCH AI SAMENVATTING (1 API Call totaal)
modal_data = {}
article_id = 0

# Voeg opiniestuk toe als artikel #1
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
        article_id += 1
        clean_sum = strip_tags(item.get('summary', item.get('description', '')))
        img_url = extract_feed_image(item, cat, item.title)
        articles_to_process.append({
            "id": str(article_id),
            "title": item.title,
            "category": cat,
            "link": item.get('link', '#'),
            "clean_sum": clean_sum,
            "img_url": img_url
        })

# BATCH AI PROCESS: Alle nieuwsartikelen in 1 enkele API call verwerken
processed_summaries = {}
if client and articles_to_process:
    try:
        input_payload = [{"id": a["id"], "title": a["title"], "text": a["clean_sum"][:300]} for a in articles_to_process]
        batch_prompt = (
            f"Verwerk de volgende lijst nieuwsartikelen:\n{json.dumps(input_payload, ensure_ascii=False)}\n\n"
            f"Opdracht per artikel ID:\n"
            f"1. Maak een heldere samenvatting in max 2 zinnen in het Nederlands.\n"
            f"2. Schrijf een 'caption' die het getoonde visuele beeld exact beschrijft in relatie tot de inhoud van de tekst (max 12 woorden).\n\n"
            f"Geef het antwoord terug als JSON dictionary met het artikel ID als key:\n"
            f"{{\n"
            f'  "2": {{"summary": "...", "caption": "..."}},\n'
            f'  "3": {{"summary": "...", "caption": "..."}}\n'
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
    
    ai_summary = ai_data.get("summary", item["clean_sum"][:130] + "...")
    img_caption = ai_data.get("caption", f"Afbeelding ter illustratie van: {item['title'][:30]}")
    
    modal_data[aid] = {
        "title": item["title"],
        "category": item["category"],
        "img": item["img_url"],
        "caption": img_caption,
        "ai_summary": ai_summary,
        "full_text": item["clean_sum"],
        "original_link": item["link"],
        "is_background": False
    }

    full_width = " card-full-width" if item["category"] == "Humor & Luchtig" else ""
    articles_html += f"""
    <div class="card{full_width}" onclick="openArticle('{aid}')">
        <div class="card-img-wrapper">
            <img src="{item['img_url']}" alt="{item['title']}" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800';">
            <span class="badge">{item['category']}</span>
        </div>
        <div class="card-content">
            <h3>{item['title']}</h3>
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
    <title>Patrick’s Nieuwsboard</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0b132b; margin: 0; padding: 20px; color: #e0e6ed; }}
        header {{ text-align: center; padding: 25px 15px; background: linear-gradient(135deg, #1c2541, #3a506b, #00b4d8); color: #ffffff; border-radius: 16px; margin-bottom: 25px; }}
        
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
        .card-full-width {{ grid-column: 1 / -1; }}
        .card-img-wrapper {{ position: relative; height: 160px; }}
        .card img {{ width: 100%; height: 100%; object-fit: cover; }}
        .badge {{ position: absolute; top: 10px; left: 10px; background: rgba(0, 180, 216, 0.9); color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: bold; }}
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
        <h1>⚡ Patrick’s Nieuwsboard</h1>
        <p>Laatst bijgewerkt: <b>{last_updated}</b> (Actieve uren: 05:00-20:00 CET)</p>
    </header>
    
    <div class="widget-bar">
        <div class="widget">
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
        <div class="widget">
            <div class="widget-title">🤖 AI Status</div>
            <div class="widget-body"><small>{ai_status}</small></div>
        </div>
    </div>

    {featured_html}

    <div class="grid">
        {articles_html}
    </div>

    <footer>
        <p>Build ID: <code>{build_id}</code> | AI Engine: Gemini 3.6 Flash (Optimized Rate Limit Batching)</p>
    </footer>

    <div id="modalOverlay" class="modal-overlay" onclick="if(event.target.id==='modalOverlay') closeModal();">
        <div class="modal-container">
            <img id="modalImg" style="width:100%; height:240px; object-fit:cover; border-radius:8px;" src="" alt="">
            <div id="modalCaption" style="font-size:0.8rem; color:#90e0ef; margin-top:6px; font-style:italic;"></div>
            <span id="modalBadge" style="background:#00b4d8; color:white; padding:3px 8px; border-radius:10px; font-size:0.7rem; font-weight:bold; margin-top:10px; display:inline-block;"></span>
            <h2 id="modalTitle" style="color:white; font-size:1.3rem;"></h2>
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
            document.getElementById('modalTitle').innerText = a.title;
            
            const relBox = document.getElementById('modalReliability');
            if (a.reliability_score !== undefined) {{
                relBox.style.display = 'block';
                relBox.innerHTML = '<b>🛡️ Betrouwbaarheidsindicator: ' + a.reliability_score + '%</b><br><small style="color:#cbd5e1;">' + (a.reliability_reason || '') + '</small>';
            }} else {{
                relBox.style.display = 'none';
            }}

            document.getElementById('modalAiBox').innerHTML = '<b>Samenvatting & Visuele Focus:</b><br>' + a.ai_summary;
            document.getElementById('modalFullText').innerHTML = a.full_text;
            
            const srcBtn = document.getElementById('modalSourceLink');
            if (a.is_background) {{ srcBtn.style.display = 'none'; }} 
            else {{ srcBtn.style.display = 'inline-block'; srcBtn.href = a.original_link; }}
            
            document.getElementById('modalOverlay').style.display = 'block';
        }}

        function closeModal() {{
            document.getElementById('modalOverlay').style.display = 'none';
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ index.html gegenereerd! Build ID: {build_id}")
