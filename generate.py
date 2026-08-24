import feedparser
import json
import os
import re
import random
import urllib.request
from datetime import datetime
import zoneinfo
from google import genai

# 0. Nederlandse tijdstempel bepalen
tz = zoneinfo.ZoneInfo("Europe/Amsterdam")
last_updated = datetime.now(tz).strftime("%d-%m-%Y om %H:%M uur")
unix_timestamp = int(datetime.now(tz).timestamp())

# Initialize Gemini Client
api_key = os.environ.get("AI_API_KEY", "").strip()
client = genai.Client(api_key=api_key) if api_key else None

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 1. RSS Feeds
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

# 2. Pool Achtergrondonderwerpen
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

# 3. Weer ophalen
weather_html_summary = "Weergegevens niet beschikbaar."
try:
    url_w = "https://api.open-meteo.com/v1/forecast?latitude=51.19&longitude=5.99&current_weather=true&hourly=temperature_2m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Europe%2FAmsterdam"
    req_w = urllib.request.Request(url_w, headers=HEADERS)
    w_res = urllib.request.urlopen(req_w, timeout=5).read()
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
article_id = 0

# Achtergrondonderwerpen
selected_backgrounds = random.sample(BACKGROUND_POOL, 3)
for item in selected_backgrounds:
    article_id += 1
    category = "Achtergrond & Meningsvorming"
    summary = f"Synthese van feiten en standpunten over: {item['topic']}."
    full_text = "Er is momenteel geen gedetailleerd dossier beschikbaar."

    if client:
        try:
            prompt = (
                f"Schrijf een compleet, op zichzelf staand achtergronddossier over: '{item['topic']}'. "
                f"Structureer exact als volgt:\n\n"
                f"### Take-aways\n* [Kernpunt 1]\n* [Kernpunt 2]\n\n"
                f"### Introductie\n[Feitelijke introductie]\n\n"
                f"### Details & Nuances\n[Diepgaandere analyse]\n\n"
                f"### Betrouwbaarheid\nScore: 8.5/10 - [Toelichting]"
            )
            response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
            full_text = clean_markdown(response.text.strip())
            summary = item['topic']
        except Exception as ai_err:
            print(f"AI fout: {ai_err}")

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
            <div class="read-more">Open dossier &rarr;</div>
        </div>
    </div>
    """

# Nieuws Artikelen
for category, urls in FEEDS.items():
    pool_items = []
    for url in urls:
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            if feed.entries:
                pool_items.extend(feed.entries[:5])
        except Exception as err:
            print(f"Fout bij {url}: {err}")
            
    category_items = random.sample(pool_items, min(len(pool_items), 3))
            
    for idx, item in enumerate(category_items):
        article_id += 1
        title = item.title
        link = item.get('link', '#')
        raw_summary = item.get('summary', item.get('description', 'Geen samenvatting.'))
        clean_summary = strip_tags(raw_summary)
        
        default_img = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600"
        if category == "Fitness & Resistance Training":
            default_img = "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=600"

        img_url = default_img
        if 'media_content' in item and len(item.media_content) > 0:
            img_url = item.media_content[0].get('url', default_img)

        ai_summary = clean_summary[:140] + "..."

        if client:
            try:
                prompt = (
                    f"Herschrijf in maximaal 2 korte, krachtige zinnen. "
                    f"Richt je op vooruitgang en oplossingen. Bericht: {title} - {clean_summary}"
                )
                response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
                ai_summary = response.text.strip()
            except Exception as ai_err:
                print(f"AI Fout: {ai_err}")

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
                <div class="read-more">Lees bericht &rarr;</div>
            </div>
        </div>
        """

json_modal_data = json.dumps(modal_data).replace('</', r'<\/')

html_content = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Patrick’s Nieuwsboard</title>
    
    <script>
      // Verwijder eventuele oude ServiceWorkers die netwerkrequests kapers
      if ('serviceWorker' in navigator) {{
        navigator.serviceWorker.getRegistrations().then(function(registrations) {{
          for(let registration of registrations) {{ registration.unregister(); }}
        }});
      }}
    </script>

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
        header h1 {{ margin: 0; font-size: 1.8rem; font-weight: 800; }}
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
        .widget-clickable {{ cursor: pointer; }}
        .widget-clickable:hover {{ background-color: #25335a; }}
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
            cursor: pointer;
        }}
        .card-featured {{ border: 1px solid #ffb703; background: #1e293b; }}
        .card-img-wrapper {{ position: relative; height: 170px; }}
        .card img {{ width: 100%; height: 100%; object-fit: cover; background-color: #0b132b; }}
        .badge {{ 
            position: absolute; 
            top: 12px; left: 12px; 
            background: rgba(0, 180, 216, 0.9); 
            color: #ffffff; 
            padding: 4px 10px; 
            border-radius: 20px; 
            font-size: 0.75rem; 
            font-weight: 700; 
            text-transform: uppercase;
        }}
        .badge-featured {{ background: rgba(255, 183, 3, 0.95); color: #000000; }}
        .card-content {{ padding: 18px; flex-grow: 1; display: flex; flex-direction: column; }}
        h3 {{ margin: 0 0 10px 0; font-size: 1.05rem; line-height: 1.35; color: #caf0f8; }}
        p {{ font-size: 0.9rem; color: #cbd5e1; line-height: 1.5; margin: 0; flex-grow: 1; }}
        .read-more {{ margin-top: 12px; font-size: 0.82rem; color: #00b4d8; font-weight: 700; }}

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
            overflow: hidden;
        }}
        .modal-header-img {{ width: 100%; height: 240px; object-fit: cover; }}
        .modal-body {{ padding: 25px; }}
        .modal-badge {{ background: #00b4d8; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }}
        .modal-title {{ font-size: 1.4rem; color: #ffffff; margin: 15px 0; }}
        .modal-ai-box {{ background: #0b132b; border-left: 4px solid #00b4d8; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; color: #90e0ef; }}
        .modal-full-text {{ font-size: 0.95rem; color: #e0e6ed; line-height: 1.6; margin-bottom: 25px; }}
        .modal-actions {{ display: flex; gap: 12px; border-top: 1px solid #3a506b; padding-top: 20px; }}
        .btn {{ padding: 12px 20px; border-radius: 10px; font-size: 0.9rem; font-weight: bold; cursor: pointer; border: none; text-decoration: none; }}
        .btn-back {{ background: #3a506b; color: #ffffff; flex-grow: 1; }}
        .btn-source {{ background: #00b4d8; color: #ffffff; flex-grow: 1; text-align: center; }}
    </style>
</head>
<body>
    <header>
        <h1>⚡ Patrick’s Nieuwsboard</h1>
        <p>Positief • Krachtig • Laatst bijgewerkt: <b id="lastUpdated">{last_updated}</b></p>
    </header>
    
    <div class="widget-bar">
        <div class="widget widget-clickable" onclick="forceRefresh();">
            <div class="widget-title">🔄 Status & Verversen</div>
            <div class="widget-body"><b>{last_updated}</b><br><small style="color:#00b4d8;">Klik hier om direct te verversen ↻</small></div>
        </div>
        <div class="widget">
            <div class="widget-title">🌤️ Weer Midden-Limburg</div>
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

    <div id="modalOverlay" class="modal-overlay" onclick="closeModalOnOverlay(event)">
        <div class="modal-container">
            <img id="modalImg" class="modal-header-img" src="" alt="Nieuws">
            <div class="modal-body">
                <span id="modalBadge" class="modal-badge"></span>
                <h2 id="modalTitle" class="modal-title"></h2>
                <div id="modalAiBox" class="modal-ai-box"></div>
                <div id="modalFullText" class="modal-full-text"></div>
                <div class="modal-actions">
                    <button class="btn btn-back" onclick="closeModal()">&larr; Terug</button>
                    <a id="modalSourceLink" class="btn btn-source" href="#" target="_blank" rel="noopener">Bekijk origineel &rarr;</a>
                </div>
            </div>
        </div>
    </div>

    <script>
        const articlesData = {json_modal_data};
        const currentBuildTime = {unix_timestamp};

        function forceRefresh() {{
            const timeStamp = new Date().getTime();
            let cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
            window.location.href = cleanUrl + '?nocache=' + timeStamp;
        }}

        // Controleer automatisch iedere 3 minuten op de achtergrond of GitHub een nieuwe site gebouwd heeft
        setInterval(() => {{
            fetch(window.location.pathname + '?check=' + new Date().getTime(), {{ cache: 'no-store' }})
                .then(response => response.text())
                .then(html => {{
                    const match = html.match(/currentBuildTime\\s*=\\s*(\\d+)/);
                    if (match && parseInt(match[1]) > currentBuildTime) {{
                        console.log("Nieuwe update gevonden! Pagina wordt herladen...");
                        forceRefresh();
                    }}
                }}).catch(err => console.log(err));
        }}, 180000);

        function openArticle(id) {{
            const article = articlesData[id];
            if (!article) return;
            document.getElementById('modalImg').src = article.img;
            document.getElementById('modalBadge').innerText = article.category;
            document.getElementById('modalTitle').innerText = article.title;
            document.getElementById('modalAiBox').innerHTML = '⚡ <b>Focus:</b><br>' + article.ai_summary;
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
            if (e.target.id === 'modalOverlay') closeModal();
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("index.html succesvol tegen gehouden caching gegenereerd!")
