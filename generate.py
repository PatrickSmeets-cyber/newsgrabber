import feedparser
import urllib.request
import json
import os
import re

# 1. RSS Feeds met fallbacks per rubriek (Inclusief Fitness & Resistance Training)
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
        "https://www.l1.nl/rss",
        "https://www.limburger.nl/rss/regio/midden-limburg"
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

# 3. Nieuws verzamelen (3 berichten per rubriek)
articles_html = ""
api_key = os.environ.get("AI_API_KEY", "").strip()

def strip_tags(text):
    return re.sub('<[^<]+?>', '', text)

for category, urls in FEEDS.items():
    category_items = []
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                category_items = feed.entries[:3]
                break
        except Exception as err:
            print(f"Fout bij ophalen {url}: {err}")
            
    for idx, item in enumerate(category_items):
        title = item.title
        raw_summary = item.get('summary', item.get('description', 'Geen samenvatting beschikbaar.'))
        summary = strip_tags(raw_summary)
        
        # Standaard afbeeldingen per categorie (als fallback)
        default_img = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600"
        if category == "Fitness & Resistance Training":
            default_img = "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=600" # Krachttraining / Gym foto

        img_url = default_img
        if 'media_content' in item and len(item.media_content) > 0:
            img_url = item.media_content[0].get('url', default_img)
        elif 'links' in item:
            for link in item.links:
                if link.get('type', '').startswith('image/'):
                    img_url = link.href
                    break

        ai_summary = summary[:140] + "..."

        # AI Positieve Herschrijving
        if api_key:
            try:
                extra_prompt = ""
                if category == "Fitness & Resistance Training":
                    extra_prompt = " Leg het accent op krachttraining, spieropbouw, progressive overload of efficiënt herstel."
                
                prompt = f"Herschrijf dit bericht in maximaal 2 korte, krachtige zinnen met een positieve en motiverende toon:{extra_prompt} {title} - {summary}"
                url_api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
                req = urllib.request.Request(url_api, data=data, headers={'Content-Type': 'application/json'})
                response = urllib.request.urlopen(req, timeout=8)
                res_json = json.loads(response.read().decode())
                ai_summary = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            except Exception as ai_err:
                print(f"AI fout bij {category} item {idx}: {ai_err}")

        # Bouw de kaart
        articles_html += f"""
        <div class="card">
            <div class="card-img-wrapper">
                <img src="{img_url}" alt="{category}" onerror="this.onerror=null;this.src='{default_img}';">
                <span class="badge">{category}</span>
            </div>
            <div class="card-content">
                <h3>{title}</h3>
                <p>{ai_summary}</p>
            </div>
        </div>
        """

# 4. Volledige HTML
html_content = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mijn Positieve Nieuws</title>
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
        header p {{ margin: 5px 0 0 0; opacity: 0.9; font-size: 0.95rem; }}
        
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
            transition: transform 0.2s ease;
        }}
        .card:hover {{ transform: translateY(-3px); }}
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
    </style>
</head>
<body>
    <header>
        <h1>⚡ JOUW ENERGIEKE NIEUWSBOARD</h1>
        <p>Positief • Krachtig • Elke 5 min geüpdatet</p>
    </header>
    
    <div class="widget-bar">
        <div class="widget">
            <div class="widget-title">🌡️ Weer Midden-Limburg</div>
            <div class="widget-body"><b>{weather_temp}°C</b> — {weather_desc}</div>
        </div>
        <div class="widget">
            <div class="widget-title">💡 Praktische Tip van de Dag</div>
            <div class="widget-body">Focus bij krachttraining op progressive overload: verhoog geleidelijk het gewicht, herhalingen of controle.</div>
        </div>
        <div class="widget">
            <div class="widget-title">✨ Motiverende Spreuk</div>
            <div class="widget-body">"Kleine dagelijkse vorderingen leiden op termijn tot gigantische resultaten."</div>
        </div>
    </div>

    <div class="grid">
        {articles_html}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("index.html succesvol gegenereerd inclusief Fitness & Resistance Training!")
