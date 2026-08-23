import feedparser, urllib.request, json, os

FEEDS = {
    "Wereld": "https://feeds.feedburner.com/nosnieuwsbuitenland",
    "Europa": "https://rss.app/feeds/v1.1/europa.xml", # Of een specifieke Europa-feed
    "Nederland": "https://www.nu.nl/rss/Algemeen",
    "Midden-Limburg": "https://www.l1.nl/rss",
    "Wetenschap": "https://www.nu.nl/rss/Wetenschap",
    "Tech": "https://www.bright.nl/rss",
    "Sport": "https://www.nu.nl/rss/Sport"
}

# 1. Haal weer op voor Midden-Limburg (bijv. Roermond)
weather_res = urllib.request.urlopen("https://api.open-meteo.com/v1/forecast?latitude=51.19&longitude=5.99&current_weather=true").read()
weather_data = json.loads(weather_res)['current_weather']

# 2. Verzamel ruwe feeditems (titels + afbeeldingen)
# 3. Stuur tekst naar AI API voor positieve herschrijving (korte krachtige 2 zinnen)
# 4. Genereer een HTML-bestand met een modern, energiek CSS-design (Grid layout, heldere kleuren)

# Script slaat het resultaat op als `index.html`
