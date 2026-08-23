import feedparser
import urllib.request
import json
import os

# 1. RSS Feeds definieuren (Gecorrigeerde en werkende werkende URL's)
FEEDS = {
    "Wereld": "https://feeds.nos.nl/nosnieuwsbuitenland",
    "Nederland": "https://www.nu.nl/rss/Algemeen",
    "Midden-Limburg": "https://www.l1.nl/rss",
    "Wetenschap": "https://www.nu.nl/rss/Wetenschap",
    "Tech": "https://www.bright.nl/rss",
    "Sport": "https://www.nu.nl/rss/Sport"
}

# 2. Weer ophalen voor Midden-Limburg (Roermond)
weather_temp = "18"
try:
    w_res = urllib.request.urlopen("https://api.open-meteo.com/v1/forecast?latitude=51.19&longitude=5.99&current_weather=true", timeout=5).read()
    w_data = json.loads(w_res)['current_weather']
    weather_temp = str(w_data['temperature'])
except Exception as e:
    print(f"Weer ophalen mislukt: {e}")

# 3. Nieuws verzamelen
articles_html = ""
api_key = os.environ.get("AI_API_KEY", "").strip()

for category, url in FEEDS.items():
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            item = feed.entries[0]
            title = item.title
            summary = item.get('summary', item.get('description', 'Geen beschrijving beschikbaar.'))
            
            # Afbeelding opsporen
            img_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600"
            if 'media_content' in item and len(item.media_content) > 0:
                img_url = item.media_content[0].get('url', img_url)
            elif 'links' in item:
                for link in item.links:
                    if link.get('type', '').startswith('image/'):
                        img_url = link.href
                        break

            # Standaard samenvatting als fallback
            ai_summary = summary[:150].replace('<p>', '').replace('</p>', '') + "..."

            # AI Herschrijven (als API key aanwezig is)
            if api_key:
                try:
                    prompt = f"Herschrijf dit nieuwsbericht kort en krachtig (max 2 zinnen) in een energieke en positieve toon: {title} - {summary}"
                    url_api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
                    req = urllib.request.Request(url_api, data=data, headers={'Content-Type': 'application/json'})
                    response = urllib.request.urlopen(req, timeout=8)
                    res_json = json.loads(response.read().decode())
                    ai_summary = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                except Exception as ai_err:
                    print(f"AI niet gelukt voor {category}, valt terug op tekst: {ai_err}")

            # Bouw kaart
            articles_html += f"""
            <div class="card">
                <img src="{img_url}" alt="{category}" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600';">
                <div class="card-content">
                    <span class="badge">{category}</span>
                    <h3>{title}</h3>
                    <p>{ai_summary}</p>
                </div>
            </div>
            """
    except Exception as feed_err:
        print(f"Fout bij verwerken van {category}: {feed_err}")

# 4. Volledige HTML bouwen
html_content = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mijn Positieve Nieuws</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }}
        header {{ text-align: center; padding: 20px; background: linear-gradient(135deg, #FF6B6B, #FFE66D); color: #222; border-radius: 12px; margin-bottom: 20px; font-weight: bold; }}
        .widget-bar {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }}
        .widget {{ background: white; padding: 15px; border-radius: 10px; flex: 1; min-width: 200px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); display: flex; flex-direction: column; }}
        .card img {{ width: 100%; height: 180px; object-fit: cover; background-color: #eee; }}
        .card-content {{ padding: 15px; flex-grow: 1; }}
        .badge {{ background: #4ECDC4; color: white; padding: 4px 8px; border-radius: 5px; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; }}
        h3 {{ margin: 10px 0 5px 0; font-size: 1.1rem; }}
        p {{ font-size: 0.95rem; color: #555; line-height: 1.4; }}
    </style>
</head>
<body>
    <header>
        <h1>⚡ Jouw Dagelijkse Dosis Positiviteit</h1>
    </header>
    
    <div class="widget-bar">
        <div class="widget">🌡️ <b>Weer Midden-Limburg:</b> {weather_temp}°C</div>
        <div class="widget">💡 <b>Tip van de dag:</b> Begin de dag met een glas water en 5 minuten zonlicht.</div>
        <div class="widget">✨ <b>Quote:</b> "Succes is niet de sleutel tot geluk. Geluk is de sleutel tot succes."</div>
    </div>

    <div class="grid">
        {articles_html}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("index.html succesvol gegenereerd!")
