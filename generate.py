import feedparser
import urllib.request
import urllib.error
import json
import os
import re
import random
from datetime import datetime
import zoneinfo

# 0. Nederlandse tijdstempel bepalen
tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
last_updated = datetime.now(tz).strftime("%d-%m-%Y om %H:%M uur")

# 1. RSS Feeds met objectieve bronnen per rubriek
FEEDS = {
    "Wereld": [
        "https://feeds.nos.nl/nosnieuwsbuitenland",
        "https://www.nu.nl/rss/Buitenland",
        "http://feeds.bbci.co.uk/news/world/rss.xml"
    ],
    "Europa": [
        "https://feeds.nos.nl/nosnieuwseuropa",
        "https://www.bnr.nl/rss/nieuws",
        "https://rss.dw.com/rdf/rss-en-all"
    ],
    "Nederland": [
        "https://feeds.nos.nl/nosnieuwsbinnenland",
        "https://www.rtlnieuws.nl/rss.xml",
        "https://www.trouw.nl/rss.xml"
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

# 2. Pool van Achtergrondonderwerpen
BACKGROUND_POOL = [
    {
        "title": "Generatieve AI op de Arbeidsmarkt",
        "topic": "De impact van AI op kantoorwerk, productiviteit en werkgelegenheid",
        "img": "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=600"
    },
    {
        "title": "Energietransitie & Het Volle Stroomnet",
        "topic": "Netcongestie, de grenzen van het elektriciteitsnet en verduurzamingsuitdagingen",
        "img": "https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=600"
    },
    {
        "title": "Dilemma op de Woningmarkt",
        "topic": "Binnenstedelijk bouwen ten opzichte van uitbreiden in het groen",
        "img": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=600"
    },
    {
        "title": "Kernenergie in het Nederlandse Klimaatbeleid",
        "topic": "De rol van nieuwe kerncentrales vs zon- en windenergie",
        "img": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600"
    },
    {
        "title": "Regulering van Sociale Media voor Jeugd",
        "topic": "Leeftijdsgrenzen, mentale gezondheid en algoritmes op telefoons",
        "img": "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=600"
    },
    {
        "title": "Rekeningrijden en Toekomst van Mobiliteit",
        "topic": "Betalen naar gebruik, wegenbelasting en de vergroening van het wagenpark",
        "img": "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?w=600"
    }
]

# 3. Uitgebreid weer ophalen voor Midden-Limburg
weather_html_summary = "Weergegevens niet beschikbaar."
try:
    url_w = "https://api.open-meteo.com/v1/forecast?latitude=51.19&longitude=5.99&current_weather=true&hourly=temperature_2m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Europe%2FAmsterdam"
    w_res = urllib.request.urlopen(url_w, timeout=5).read()
    w_data = json.loads(w_res)
    
    cur_temp = round(w_data['current_weather']['temperature'])
    
    hourly_temps = w_data['hourly']['temperature_2m'][:24]
    hourly_precip = w_data['hourly']['precipitation_probability'][:24]
    max_24h_temp = round(max(hourly_temps))
    min_24h_temp = round(min(hourly_temps))
    max_24h_precip = max(hourly_precip)
    
    daily_dates = w_data['daily']['time']
    daily_max = w_data['daily']['temperature_2m_max']
    daily_min = w_data['daily']['temperature_2m_min']
    
    week_str_list = []
    days_map = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"]
    for i in range(1, min(6, len(daily_dates))):
        dt = datetime.strptime(daily_dates[i], "%Y-%m-%d")
        day_name = days_map[dt.weekday()]
        week_str_list.append(f"{day_name}: {round(daily_min[i])}°/{round(daily_max[i])}°C")
    
    week_summary = " | ".join(week_str_list)

    weather_html_summary = f"""
    <b>Nu: {cur_temp}°C</b><br>
    <small><b>Komende 24u:</b> {min_24h_temp}°C tot {max_24h_temp}°C (Regenkans: {max_24h_precip}%)</small><br>
    <small><b>Deze week:</b> {week_summary}</small>
    """
except Exception as e:
    print(f"Weer ophalen mislukt: {e}")
    weather_html_summary = "Weergegevens momenteel niet beschikbaar."

# Helper om Markdown koppen en vetgedrukte tekst om te zetten naar schone HTML
def clean_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'### (.*?)\n', r'<h4 style="color:#00b4d8; margin-top:15px; margin-bottom:5px;">\1</h4>', text)
    text = re.sub(r'\* (.*?)\n', r'• \1<br>', text)
    text = text.replace("\n", "<br>")
    return text

def strip_tags(text):
    return re.sub('<[^<]+?>', '', text)

articles_html = ""
modal_data = {}
api_key = os.environ.get("AI_API_KEY", "").strip()

article_id = 0

# A. Kies 3 willekeurige achtergrondonderwerpen
selected_backgrounds = random.sample(BACKGROUND_POOL, 3)

for item in selected_backgrounds:
    article_id += 1
    category = "Achtergrond & Meningsvorming"
    summary = f"Synthese van feiten en standpunten over: {item['topic']}."
    full_text = "Er is momenteel geen gedetailleerd dossier beschikbaar."

    if api_key:
        try:
            prompt = (
                f"Schrijf een compleet, op zichzelf staand achtergronddossier over het onderwerp: '{item['topic']}'. "
                f"Gebruik inzichten uit meerdere objectieve bronnen (zoals CBS, TNO, Rijksoverheid, CPB, EU-rapporten en wetenschappelijke studies). "
                f"Structureer het antwoord exact als volgt:\n\n"
                f"### Take-aways\n"
                f"* [Kernpunt 1]\n"
                f"* [Kernpunt 2]\n"
                f"* [Kernpunt 3]\n\n"
                f"### Introductie\n"
                f"[Een heldere, feitelijke introductie van de situatie en waarom dit nu speelt]\n\n"
                f"### Details & Nuances\n"
                f"[Diepgaandere analyse met voor- en nadelen, kansen en risico's]\n\n"
                f"### Betrouwbaarheidswaarde\n"
                f"Score: 8.5/10 - [Toelichting op basis van data en consensus]\n\n"
                f"### Gebruikte Bronnen & Referenties\n"
                f"* [Lijst met relevante instanties, beleidsstukken of onderzoeksinstellingen]"
            )
            
            # Officiële v1 REST endpoint voor gemini-1.5-flash
            url_api = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
            data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
            req = urllib.request.Request(url_api, data=data, headers={'Content-Type': 'application/json'})
            
            response = urllib.request.urlopen(req, timeout=20)
            res_json = json.loads(response.read().decode())
            
            ai_out = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            full_text = clean_markdown(ai_out)
            summary = item['topic']
        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode()
            print(f"HTTP Fout bij '{item['title']}': Status {http_err.code} - Details: {error_body}")
            full_text = f"<b>API Fout ({http_err.code}):</b> Het ophalen via Gemini is mislukt."
        except Exception as ai_err:
            print(f"Algemene AI dossier fout bij '{item['title']}': {ai_err}")
            full_text = f"<b>Niet gelukt om live AI-dossier op te halen.</b><br>Fout: {ai_err}"

    modal_data[str(article_id)] = {
        "title": item["title"],
        "category": category,
        "img": item["img"],
        "ai_summary": summary,
        "full_text": full_text,
        "is_background": True
    }
    
    articles_html += f"""
    <div class="card card-featured" onclick="openArticle('{article_id}')">
        <div class="card-img-wrapper">
            <img src="{item['img']}" alt="{category}">
            <span class="badge badge-featured">{category}</span>
        </div>
        <div class="card-content">
            <h3>{item['title']}</h3>
            <p>{summary}</p>
            <div class="read-more">Open compleet dossier &rarr;</div>
        </div>
    </div>
    """

# B. Verzamel regulier nieuws per categorie
for category, urls in FEEDS.items():
    pool_items = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                pool_items.extend(feed.entries[:5])
        except Exception as err:
            print(f"Fout bij ophalen {url}: {err}")
            
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

        if api_key:
            try:
                extra_prompt = ""
                if category == "Fitness & Resistance Training":
                    extra_prompt = " Leg de nadruk op krachttraining, spieropbouw, herstel of progressie."
                
                prompt = (
                    "Jij bent een redacteur van een positief, energiek nieuwsdashboard. "
                    "Herschrijf het onderstaande bericht in maximaal 2 korte, krachtige zinnen. "
                    "Richt je primair op positief nieuws, kansen, oplossingen, innovaties of menselijke vooruitgang. "
                    f"{extra_prompt} Bericht: {title} - {clean_summary}"
                )
                
                url_api = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
                data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
                req = urllib.request.Request(url_api, data=data, headers={'Content-Type': 'application/json'})
                response = urllib.request.urlopen(req, timeout=10)
                res_json = json.loads(response.read().decode())
                ai_summary = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            except urllib.error.HTTPError as http_err:
                print(f"HTTP Fout bij {category} item {idx}: Status {http_err.code}")
            except Exception as ai_err:
                print(f"AI fout bij {category} item {idx}: {ai_err}")

        modal_data[str(article_id)] = {
            "title": title,
            "category": category,
            "img": img_url,
            "ai_summary": ai_summary,
            "full_text": clean_summary,
            "original_link": link,
            "is_background": False
        }

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

# 5. Volledige HTML opbouwen
html_content = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Patrick’s Nieuwsboard</title>
    
    <link rel="apple-touch-icon" href="https://img.icons8.com/fluency/180/lightning-bolt.png?v=2">
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
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); 
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
            transition: transform 0.2s ease, background-color 0.2s ease;
        }}
        .widget-clickable:hover {{
            background-color: #25335a;
            transform: translateY(-2px);
        }}
        .widget-title {{ font-size: 0.8rem; text-transform: uppercase; color: #90e0ef; font-weight: bold; margin-bottom: 5px; }}
        .widget-body {{ font-size: 0.9rem; line-height: 1.4; color: #ffffff; }}

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
        .card-featured {{
            border: 1px solid #ffb703;
            background: #1e293b;
        }}
        .card:hover {{ 
            transform: translateY(-4px); 
            border-color: #00b4d8;
        }}
        .card-featured:hover {{
            border-color: #ffb703;
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
        .badge-featured {{
            background: rgba(255, 183, 3, 0.95);
            color: #000000;
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
        .modal-full-text {{ font-size: 0.95rem; color: #e0e6ed; line-height: 1.6; margin-bottom: 25px; }}
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
        .btn-back {{ background: #3a506b; color: #ffffff; flex-grow: 1; }}
        .btn-back:hover {{ background: #4f6d91; }}
        .btn-source {{ background: #00b4d8; color: #ffffff; flex-grow: 1; text-align: center; }}
        .btn-source:hover {{ background: #0096c7; }}
    </style>
</head>
<body>
    <header>
        <h1>⚡ Patrick’s Nieuwsboard</h1>
        <p>Positief • Krachtig • Laatst bijgewerkt: <b>{last_updated}</b></p>
    </header>
    
    <div class="widget-bar">
        <div class="widget widget-clickable" onclick="window.location.reload();">
            <div class="widget-title">🔄 Laatste Update</div>
            <div class="widget-body"><b>{last_updated}</b><br><small style="opacity:0.8">Tik hier om te verversen ↻</small></div>
        </div>
        <div class="widget">
            <div class="widget-title">🌤️ Weer Midden-Limburg & Verwachting</div>
            <div class="widget-body">{weather_html_summary}</div>
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
                    <a id="modalSourceLink" class="btn btn-source" href="#" target="_blank" rel="noopener">Bekijk origineel op de website &rarr;</a>
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
            document.getElementById('modalAiBox').innerHTML = '⚡ <b>Focus / Topic:</b><br>' + article.ai_summary;
            document.getElementById('modalFullText').innerHTML = article.full_text;

            const sourceBtn = document.getElementById('modalSourceLink');
            if (article.is_background) {{
                sourceBtn.style.display = 'none';
            }} else {{
                sourceBtn.style.display = 'inline-flex';
                sourceBtn.href = article.original_link;
            }}

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

print("index.html succesvol gegenereerd!")
