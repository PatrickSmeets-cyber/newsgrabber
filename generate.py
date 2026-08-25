import feedparser
import json
import os
import re
import random
import urllib.request
import urllib.parse
import uuid
from datetime import datetime
import zoneinfo
from google import genai

# Timezone & Unieke Run ID
tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
last_updated = datetime.now(tz).strftime("%d-%m-%Y om %H:%M uur")
build_id = str(uuid.uuid4())[:8]

# Gemini Client initialiseren
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

FEEDS = {
    "Wereld": ["https://feeds.nos.nl/nosnieuwsbuitenland", "https://www.nu.nl/rss/Buitenland"],
    "Europa": ["https://feeds.nos.nl/nosnieuwseuropa", "https://www.bnr.nl/rss/nieuws"],
    "Nederland": ["https://feeds.nos.nl/nosnieuwsbinnenland", "https://www.rtlnieuws.nl/rss.xml"],
    "Midden-Limburg": ["https://www.weertdegekste.nl/feed/", "https://www.nederweert24.nl/feed/", "https://www.l1nieuws.nl/rss/nieuws"],
    "Wiskunde & Wetenschap": ["https://www.nu.nl/rss/Wetenschap", "https://feeds.nos.nl/nosnieuwswetenschap"],
    "Technologie": ["https://www.bright.nl/rss", "https://www.nu.nl/rss/Tech"],
    "Sport": ["https://feeds.nos.nl/nossport", "https://www.nu.nl/rss/Sport"],
    "Fitness & Resistance Training": ["https://www.fit.nl/feed", "https://www.nu.nl/rss/Gezondheid"],
    "Humor & Luchtig": ["https://speld.nl/feed/", "https://www.nu.nl/rss/Opmerkelijk"]
}

# --- DYNAMISCH GENEREREN SPREUK & TIP VIA AI ---
daily_quote = "De enige constante in het leven is verandering."
daily_quote_author = "Heraclitus"
daily_tip = "Neem elk uur even 2 minuten afstand van je scherm om je ogen rust te geven."

if client:
    try:
        prompt_extras = (
            "Bedenk voor vandaag:\n"
            "1. Een inspirerende, filosofische of motiverende spreuk/quote inclusief auteur.\n"
            "2. Een unieke, praktische en direct toepasbare dagelijkse tip op het gebied van productiviteit, gezondheid of welzijn.\n\n"
            "Geef het antwoord exact in het volgende JSON-formaat terug:\n"
            "{\n"
            '  "quote": "Tekst van de spreuk",\n'
            '  "auteur": "Auteur naam",\n'
            '  "tip": "Praktische tip tekst"\n'
            "}"
        )
        res_extras = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt_extras,
            config={'response_mime_type': 'application/json'}
        )
        data_extras = json.loads(res_extras.text.strip())
        daily_quote = data_extras.get("quote", daily_quote)
        daily_quote_author = data_extras.get("auteur", daily_quote_author)
        daily_tip = data_extras.get("tip", daily_tip)
        print("✅ Spreuk en Tip dynamisch gegenereerd door Gemini")
    except Exception as err:
        print(f"❌ Fout bij genereren Spreuk/Tip: {err}")

# --- 7-DAAGSE WEERSVERWACHTING ---
weather_html_summary = "Weergegevens niet beschikbaar."
try:
    url_w = "https://api.open-meteo.com/v1/forecast?latitude=51.19&longitude=5.99&current_weather=true&daily=temperature_2m_max,temperature_2m_min&timezone=Europe%2FAmsterdam"
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
        
    weather_html_summary = f"<b>Nu: {cur_temp}°C</b><div style='display:flex; justify-content:space-between; margin-top:8px;'>{days_html}</div>"
except Exception as e:
    print(f"Weerfout: {e}")

def clean_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'### (.*?)\n', r'<h4 style="color:#00b4d8; margin-top:15px; margin-bottom:5px;">\1</h4>', text)
    text = re.sub(r'\* (.*?)\n', r'• \1<br>', text)
    return text.replace("\n", "<br>")

def strip_tags(text):
    return re.sub('<[^<]+?>', '', text)

def extract_feed_image(entry, default_category):
    if 'media_content' in entry and entry.media_content:
        for media in entry.media_content:
            if 'url' in media:
                return media['url']
    if 'enclosures' in entry and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image'):
                return enc.get('href')
    
    desc = entry.get('summary', '') or entry.get('description', '')
    img_match = re.search(r'<img [^>]*src=["\']([^"\']+)["\']', desc)
    if img_match:
        return img_match.group(1)
        
    keywords = re.findall(r'\b[a-zA-Z]{5,}\b', entry.title)
    query = keywords[0] if keywords else default_category
    return f"https://loremflickr.com/600/400/{urllib.parse.quote(query)}"

articles_html = ""
modal_data = {}
article_id = 0

all_headlines_with_sources = []
feed_results = {}

for cat, urls in FEEDS.items():
    pool_items = []
    for url in urls:
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            if feed.entries:
                pool_items.extend(feed.entries)
        except Exception as err:
            print(f"Feed fout {url}: {err}")
            
    random.shuffle(pool_items)
    feed_results[cat] = pool_items
    for entry in pool_items[:5]:
        all_headlines_with_sources.append({
            "title": entry.title,
            "link": entry.get("link", "")
        })

# --- 1. OPINIESTUK GENEREREN ---
article_id += 1
category = "Dagelijks Opinie-Dossier"
featured_title = "Actueel Maatschappelijk Dossier"
summary = "AI Analyse van een actueel onderwerp..."
full_text = "Dossier wordt geladen..."
featured_img = "https://loremflickr.com/1200/600/news,editorial"
featured_caption = "Sfeerbeeld maatschappelijk debat"

if client and all_headlines_with_sources:
    try:
        sample = random.sample(all_headlines_with_sources, min(len(all_headlines_with_sources), 12))
        prompt = (
            f"Gebruik de onderstaande nieuwsbronnen:\n"
            f"{json.dumps(sample, ensure_ascii=False)}\n\n"
            f"Opdracht:\n"
            f"1. Kies het meest actuele onderwerp.\n"
            f"2. Bedenk een pakkende titel.\n"
            f"3. Schrijf een achtergrond- en opinieartikel.\n"
            f"4. Bedenk een korte bijbehorende foto-caption (max 10 woorden).\n\n"
            f"Geef exact het volgende JSON-formaat terug:\n"
            f"{{\n"
            f'  "titel": "Titel",\n'
            f'  "samenvatting": "Korte samenvatting in 1-2 zinnen",\n'
            f'  "inhoud": "### Kerninzichten\\n* [Punt 1]\\n* [Punt 2]\\n\\n### Analyse & Context\\n[Uitgebreide tekst]\\n\\n### Conclusie\\n[Conclusie]",\n'
            f'  "image_caption": "Korte uitleg bij het plaatje"\n'
            f"}}"
        )
        res = client.models.generate_content(
            model='gemini-3.6-flash', 
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        data = json.loads(res.text.strip())
        featured_title = data.get("titel", featured_title)
        summary = data.get("samenvatting", summary)
        full_text = clean_markdown(data.get("inhoud", ""))
        featured_caption = data.get("image_caption", featured_caption)
        print(f"✅ AI Opiniedossier gegenereerd: {featured_title}")
    except Exception as err:
        print(f"❌ AI Opinie Fout: {err}")
        full_text = f"Fout bij genereren AI dossier: {err}"

modal_data[str(article_id)] = {
    "title": featured_title,
    "category": category,
    "img": featured_img,
    "caption": featured_caption,
    "ai_summary": summary,
    "full_text": full_text,
    "is_background": True
}

featured_html = f"""
<div class="featured-banner" onclick="openArticle('{article_id}')">
    <div class="featured-img-wrapper">
        <img src="{featured_img}" alt="{featured_title}">
        <span class="badge badge-featured">🔥 {category}</span>
    </div>
    <div class="featured-content">
        <h2>{featured_title}</h2>
        <p>{summary}</p>
        <div style="font-size:0.75rem; color:#ffb703; margin-top:5px;">📷 {featured_caption}</div>
        <div class="read-more">Lees het volledige opiniedossier &rarr;</div>
    </div>
</div>
"""

# --- 2. REGULIERE RUBRIEKEN ---
category_counts = {
    "Wereld": 3, "Europa": 3, "Nederland": 3, "Midden-Limburg": 3,
    "Wiskunde & Wetenschap": 3, "Technologie": 3, "Sport": 3,
    "Fitness & Resistance Training": 3, "Humor & Luchtig": 1
}

for cat, required_count in category_counts.items():
    pool_items = feed_results.get(cat, [])
    selected_items = pool_items[:required_count]
    
    for item in selected_items:
        article_id += 1
        title = item.title
        link = item.get('link', '#')
        clean_sum = strip_tags(item.get('summary', item.get('description', '')))
        
        img_url = extract_feed_image(item, cat)
        ai_summary = clean_sum[:130] + "..."
        img_caption = f"Afbeelding bij {cat}"

        if client:
            try:
                res = client.models.generate_content(
                    model='gemini-3.6-flash', 
                    contents=(
                        f"Geef een korte samenvatting (max 2 zinnen) en een foto-caption (max 8 woorden) voor dit bericht:\n"
                        f"Titel: {title}\nInhoud: {clean_sum}\n\n"
                        f"Geef antwoord als JSON: {{\n\"summary\": \"...\",\n\"caption\": \"...\"\n}}"
                    ),
                    config={'response_mime_type': 'application/json'}
                )
                res_data = json.loads(res.text.strip())
                ai_summary = res_data.get("summary", ai_summary)
                img_caption = res_data.get("caption", img_caption)
            except Exception as err:
                print(f"AI verwerkingsfout: {err}")

        modal_data[str(article_id)] = {
            "title": title, "category": cat, "img": img_url,
            "caption": img_caption, "ai_summary": ai_summary,
            "full_text": clean_sum, "original_link": link, "is_background": False
        }

        full_width_class = " card-full-width" if cat == "Humor & Luchtig" else ""

        articles_html += f"""
        <div class="card{full_width_class}" onclick="openArticle('{article_id}')">
            <div class="card-img-wrapper">
                <img src="{img_url}" alt="{title}" onerror="this.onerror=null;this.src='https://loremflickr.com/600/400/news';">
                <span class="badge">{cat}</span>
            </div>
            <div class="card-content">
                <h3>{title}</h3>
                <p>{ai_summary}</p>
                <div style="font-size:0.75rem; color:#90e0ef; margin-top:8px;">📷 {img_caption}</div>
                <div class="read-more">Lees bericht &rarr;</div>
            </div>
        </div>
        """

json_modal_data = json.dumps(modal_data).replace('</', r'<\/')

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
        @media (min-width: 768px) {{ .featured-banner {{ flex-direction: row; height: 300px; }} .featured-img-wrapper {{ width: 50%; height: 100% !important; }} .featured-content {{ width: 50%; padding: 30px !important; }} }}
        .featured-img-wrapper {{ position: relative; height: 200px; }}
        .featured-img-wrapper img {{ width: 100%; height: 100%; object-fit: cover; }}
        .badge-featured {{ background: #ffb703; color: #000; position: absolute; top: 15px; left: 15px; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 0.8rem; }}
        .featured-content {{ padding: 20px; display: flex; flex-direction: column; justify-content: center; }}
        .featured-content h2 {{ margin: 0 0 10px 0; color: #ffffff; font-size: 1.5rem; }}

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
        <p>Laatst bijgewerkt: <b>{last_updated}</b></p>
    </header>
    
    <div class="widget-bar">
        <div class="widget">
            <div class="widget-title">🌤️ 7-Daagse Weersverwachting</div>
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
        <p>Build ID: <code>{build_id}</code> | AI Provider: Gemini 3.6 Flash</p>
    </footer>

    <div id="modalOverlay" class="modal-overlay" onclick="if(event.target.id==='modalOverlay') closeModal();">
        <div class="modal-container">
            <img id="modalImg" style="width:100%; height:220px; object-fit:cover; border-radius:8px;" src="" alt="">
            <div id="modalCaption" style="font-size:0.8rem; color:#90e0ef; margin-top:5px; font-style:italic;"></div>
            <span id="modalBadge" style="background:#00b4d8; color:white; padding:3px 8px; border-radius:10px; font-size:0.7rem; font-weight:bold; margin-top:10px; display:inline-block;"></span>
            <h2 id="modalTitle" style="color:white; font-size:1.3rem;"></h2>
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
            document.getElementById('modalAiBox').innerHTML = '<b>Samenvatting / Focus:</b><br>' + a.ai_summary;
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
