import feedparser
import urllib.request
import json
import os
import re
import random
from datetime import datetime
import zoneinfo

# 0. Nederlandse tijdstempel bepalen
tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
last_updated = datetime.now(tz).strftime("%d-%m-%Y om %H:%M uur")

# 1. RSS Feeds met meerdere bronnen per rubriek
FEEDS = {
    "Wereld": [
        "https://feeds.nos.nl/nosnieuwsbuitenland",
        "https://www.nu.nl/rss/Buitenland"
    ],
    "Europa": [
        "https://feeds.nos.nl/nosnieuwseuropa",
        "https://www.nu.nl/rss/Buitenland"
    ],
    "Nederland": [
        "https://feeds.nos.nl/nosnieuwsbinnenland",
        "https://www.nu.nl/rss/Algemeen"
    ],
    "Midden-Limburg": [
        "https://www.weertdegekste.nl/feed/",
        "https://www.nederweert24.nl/feed/",
        "https://www.vmlnieuws.nl/feed/",
        "https://www.l1nieuws.nl/rss/nieuws"
    ],
    "Wiskunde & Wetenschap": [
        "https://www.nu.nl/rss/Wetenschap",
        "https://feeds.nos.nl/nosnieuwswetenschap"
    ],
    "Technologie": [
        "https://www.bright.nl/rss",
        "https://www.nu.nl/rss/Tech"
    ],
    "Sport": [
        "https://feeds.nos.nl/nossport",
        "https://www.nu.nl/rss/Sport"
    ],
    "Fitness & Resistance Training": [
        "https://www.fit.nl/feed",
        "https://www.bodybuilding.com/rss/articles",
        "https://www.nu.nl/rss/Gezondheid"
    ],
    "Humor & Luchtig": [
        "https://speld.nl/feed/",
        "https://www.nu.nl/rss/Opmerkelijk"
    ]
}

# 2. Weer ophalen voor Midden-Limburg (Roermond / Weert)
weather_temp = "18"
weather_desc = "Licht bewolkt"
try:
    w_res = urllib.request.urlopen("https://api.open-meteo.com/v1/forecast?latitude=51.19&longitude=5.99&current_weather=true", timeout=5).read()
    w_data = json.loads(w_res)['current_weather']
    weather_temp = str(w_data['temperature'])
    code = w_data.get('weathercode', 0)
    if code in [0, 1]: weather_desc = "Zonnig"
    elif code in [2, 3]: weather_desc = "Half bewolkt"
    elif code >= 51: weather_desc = "Kans op regen"
except Exception as e:
    print(f"Weer ophalen mislukt: {e}")

# 3. Nieuws verzamelen met random shuffling
articles_html = ""
modal_data = {}
api_key = os.environ.get("AI_API_KEY", "").strip()

def strip_tags(text):
    return re.sub('<[^<]+?>', '', text)

article_id = 0

for category, urls in FEEDS.items():
    pool_items = []
    
    # Verzamel items uit alle feeds in deze categorie
    for url in urls:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                pool_items.extend(feed.entries[:5])
        except Exception as err:
            print(f"Fout bij ophalen {url}: {err}")
            
    # Kies willekeurig 3 unieke artikelen uit de poel
    if len(pool_items) >= 3:
        category_items = random.sample(pool_items, 3)
    else:
        category_items = pool_items[:3]
            
    for idx, item in enumerate(category_items):
        article_id += 1
        title = item.title
        link = item.get('link', '#')
        raw_summary = item.get('summary', item.get('description', 'Geen samenvatting beschikbaar.'))
        clean_summary = strip_tags(raw_summary)
        
        default_img = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600"
        if category == "Fitness & Resistance Training":
            default_img = "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=600"

        img_url = default_img
        if 'media_content' in item and len(item.media_content) > 0:
            img_url = item.media_content[0].get('url', default_img)
        elif 'links' in item:
            for link_item in item.links:
                if link_item.get('type', '').startswith('image/'):
                    img_url = link_item.href
                    break

        ai_summary = clean_summary[:140] + "..."

        # AI Positieve Herschrijving en filtering
        if api_key:
            try:
                extra_prompt = ""
                if category == "Fitness & Resistance Training":
                    extra_prompt = " Leg de nadruk op krachttraining, spieropbouw, herstel of progressie."
                
                prompt = (
                    "Jij bent een redacteur van een positief, energiek nieuwsdashboard. "
                    "Herschrijf het onderstaande bericht in maximaal 2 korte, krachtige zinnen. "
                    "Richt je primair op positief nieuws, kansen, oplossingen, innovaties of menselijke vooruitgang. "
                    "Als het oorspronkelijke bericht neutraal of negatief is, belicht dan de constructieve kant, geleerde lessen of mogelijke oplossingen in een hoopvolle, energieke en positieve toon."
                    f"{extra_prompt} Bericht: {title} - {clean_summary}"
                )
                
                url_api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
                req = urllib.request.Request(url_api, data=data, headers={'Content-Type': 'application/json'})
                response = urllib.request.urlopen(req, timeout=8)
                res_json = json.loads(response.read().decode())
                ai_summary = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            except Exception as ai_err:
                print(f"AI fout bij {category} item {idx}: {ai_err}")

        # Opslaan voor het volledige berichtvenster
        modal_data[str(article_id)] = {
            "title": title,
            "category": category,
            "img": img_url,
            "ai_summary": ai_summary,
            "full_text": clean_summary,
            "original_link": link
        }

        # Bouw de klikbare kaart
        articles_html += f"""
        <div class="card" onclick="openArticle('{article_id}')">
            <div class="card-img-wrapper">
                <img src="{img_url}" alt="{category}" onerror="this.onerror=null;this.src='{default_img}';">
                <span class="badge">{category}</span>
            </div>
            <div class="card-content">
                <h3>{title}</h3>
                <p>{ai_summary}</p>
                <div class="read-more">Lees volledig bericht &rarr;</div>
            </div>
        </div>
        """

# 4. Volledige HTML
html_content = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jouw Persoonlijke Nieuwsboard</title>
    
    <!-- iOS Icons voor iPhone en iPad -->
    <link rel="apple-touch-icon" href="https://img.icons8.com/fluency/180/lightning-bolt.png?v=2">
    <link rel="apple-touch-icon" sizes="152x152" href="https://img.icons8.com/fluency/180/lightning-bolt.png?v=2">
    <link rel="apple-touch-icon" sizes="180x180" href="https://img.icons8.com/fluency/180/lightning-bolt.png?v=2">
    <link rel="icon" type="image/png" href="https://img.icons8.com/fluency/180/lightning-bolt.png?v=2">

    <style>
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            background-color: #0b132b; 
            margin: 0; 
            padding: 20px; 
            color: #e0e6ed; 
        }}
        header {{ 
            text-align: center; 
            padding: 25px 15px; 
            background: linear-gradient(135deg, #1c2541, #3a506b, #00b4d8); 
            color: #ffffff; 
            border-radius: 16px; 
            margin-bottom: 25px; 
            box-shadow: 0 8px 20px rgba(0, 180, 216, 0.2);
        }}
        header h1 {{ margin: 0; font-size: 1.8rem; font-weight: 800; letter-spacing: 0.5px; }}
        header p {{ margin: 6px 0 0 0; opacity: 0.95; font-size: 0.95rem; }}
        
        .widget-bar {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
            gap: 15px; 
            margin-bottom: 25px; 
        }}
        .widget {{ 
            background: #1c2541; 
            padding: 16px; 
            border-radius: 12px; 
            border-left: 4px solid #00b4d8; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.15); 
        }}
        .widget-clickable {{
            cursor: pointer;
            transition: transform 0.2s ease, background-color 0.2s ease, border-color 0.2s ease;
        }}
        .widget-clickable:hover {{
            background-color: #25335a;
            transform: translateY(-2px);
            border-left-color: #90e0ef;
        }}
        .widget-clickable:active {{
            transform: scale(0.98);
        }}
        .widget-title {{ font-size: 0.8rem; text-transform: uppercase; color: #90e0ef; font-weight: bold; margin-bottom: 5px; }}
        .widget-body {{ font-size: 0.95rem; line-height: 1.4; color: #ffffff; }}

        .grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); 
            gap: 20px; 
        }}
        .card {{ 
            background: #1c2541; 
            border-radius: 14px; 
            overflow: hidden; 
            box-shadow: 0 6px 15px rgba(0,0,0,0.2); 
            display: flex; 
            flex-direction: column; 
            border: 1px solid #3a506b;
            transition: transform 0.2s ease, border-color 0.2s ease;
            cursor: pointer;
        }}
        .card:hover {{ 
            transform: translateY(-4px); 
            border-color: #00b4d8;
        }}
        .card-img-wrapper {{ position: relative; height: 170px; }}
        .card img {{ width: 100%; height: 100%; object-fit: cover; background-color: #0b132b; }}
        .badge {{ 
            position: absolute; 
            top: 12px; 
            left: 12px; 
            background: rgba(0, 180, 216, 0.9); 
            color: #ffffff; 
            padding: 4px 10px; 
            border-radius: 20px; 
            font-size: 0.75rem; 
            font-weight: 700; 
            backdrop-filter: blur(4px);
            text-transform: uppercase;
        }}
        .card-content {{ padding: 18px; flex-grow: 1; display: flex; flex-direction: column; }}
        h3 {{ margin: 0 0 10px 0; font-size: 1.05rem; line-height: 1.35; color: #caf0f8; }}
        p {{ font-size: 0.9rem; color: #cbd5e1; line-height: 1.5; margin: 0; flex-grow: 1; }}
        
        .read-more {{ 
            margin-top: 12px; 
            font-size: 0.82rem; 
            color: #00b4d8; 
            font-weight: 700; 
            display: inline-block;
        }}

        /* Modal Overlay voor Volledig Bericht */
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(11, 19, 43, 0.85);
            backdrop-filter: blur(8px);
            z-index: 1000;
            overflow-y: auto;
            padding: 20px;
        }}
        .modal-container {{
            max-width: 680px;
            margin: 30px auto;
            background: #1c2541;
            border-radius: 16px;
            border: 1px solid #00b4d8;
            box-shadow: 0 10px 30px rgba(0,180,216,0.3);
            overflow: hidden;
            animation: fadeIn 0.25s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(15px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .modal-header-img {{ width: 100%; height: 240px; object-fit: cover; }}
        .modal-body {{ padding: 25px; }}
        .modal-badge {{ background: #00b4d8; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; }}
        .modal-title {{ font-size: 1.4rem; color: #ffffff; margin: 15px 0; line-height: 1.3; }}
        .modal-ai-box {{
            background: #0b132b;
            border-left: 4px solid #00b4d8;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            color: #90e0ef;
            font-size: 0.95rem;
            line-height: 1.4;
        }}
        .modal-full-text {{ font-size: 1rem; color: #e0e6ed; line-height: 1.6; margin-bottom: 25px; }}
        .modal-actions {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            border-top: 1px solid #3a506b;
            padding-top: 20px;
        }}
        .btn {{
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: bold;
            cursor: pointer;
            border: none;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }}
        .btn-back {{ background: #3a506b; color: #ffffff; }}
        .btn-back:hover {{ background: #4f6d91; }}
        .btn-source {{ background: #00b4d8; color: #ffffff; flex-grow: 1; text-align: center; }}
        .btn-source:hover {{ background: #0096c7; }}
    </style>
</head>
<body>
    <header>
        <h1>⚡ JOUW PERSOONLIJKE NIEUWSBOARD</h1>
        <p>Positief • Krachtig • Laatst bijgewerkt: <b>{last_updated}</b></p>
    </header>
    
    <div class="widget-bar">
        <div class="widget widget-clickable" onclick="window.location.reload();">
            <div class="widget-title">🔄 Laatste Update</div>
            <div class="widget-body"><b>{last_updated}</b><br><small style="opacity:0.8">Tik hier om pagina te verversen ↻</small></div>
        </div>
        <div class="widget">
            <div class="widget-title">🌡️ Weer Midden-Limburg</div>
            <div class="widget-body"><b>{weather_temp}°C</b> — {weather_desc}</div>
        </div>
        <div class="widget">
            <div class="widget-title">💡 Tip van de Dag</div>
            <div class="widget-body">Focus bij krachttraining op progressive overload: verhoog geleidelijk gewicht of herhalingen.</div>
        </div>
        <div class="widget">
            <div class="widget-title">✨ Motiverende Spreuk</div>
            <div class="widget-body">"Kleine dagelijkse vorderingen leiden op termijn tot gigantische resultaten."</div>
        </div>
    </div>

    <div class="grid">
        {articles_html}
    </div>

    <!-- Modal View -->
    <div id="modalOverlay" class="modal-overlay" onclick="closeModalOnOverlay(event)">
        <div class="modal-container">
            <img id="modalImg" class="modal-header-img" src="" alt="Nieuws afbeelding">
            <div class="modal-body">
                <span id="modalBadge" class="modal-badge"></span>
                <h2 id="modalTitle" class="modal-title"></h2>
                <div id="modalAiBox" class="modal-ai-box"></div>
                <div id="modalFullText" class="modal-full-text"></div>
                <div class="modal-actions">
                    <button class="btn btn-back" onclick="closeModal()">&larr; Terug naar overzicht</button>
                    <a id="modalSourceLink" class="btn btn-source" href="#" target="_blank" rel="noopener">Bekijk bron op de website &rarr;</a>
                </div>
            </div>
        </div>
    </div>

    <script>
        const articlesData = {json.dumps(modal_data)};

        function openArticle(id) {{
            const article = articlesData[id];
            if (!article) return;

            document.getElementById('modalImg').src = article.img;
            document.getElementById('modalBadge').innerText = article.category;
            document.getElementById('modalTitle').innerText = article.title;
            document.getElementById('modalAiBox').innerHTML = '⚡ <b>Positieve AI-samenvatting:</b><br>' + article.ai_summary;
            document.getElementById('modalFullText').innerText = article.full_text;
            document.getElementById('modalSourceLink').href = article.original_link;

            document.getElementById('modalOverlay').style.display = 'block';
            document.body.style.overflow = 'hidden';
        }}

        function closeModal() {{
            document.getElementById('modalOverlay').style.display = 'none';
            document.body.style.overflow = 'auto';
        }}

        function closeModalOnOverlay(e) {{
            if (e.target.id === 'modalOverlay') {{
                closeModal();
            }}
        }}

        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeModal();
        }});
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("index.html succesvol gegenereerd met gevarieerde nieuwsselectie!")
