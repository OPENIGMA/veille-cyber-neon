import json
from pathlib import Path
from datetime import datetime, timezone
import requests
import feedparser

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "veille.json"

THEMES = [
    "ordre public", "manifestation", "grève", "sécurité", "criminalité",
    "radicalisation", "politique", "éducation", "santé", "transport",
    "énergie", "nucleaire", "agriculture", "drones", "cybercriminalité"
]

GEOGRAPHY = [
    "Toulouse", "Montpellier", "Marseille", "Nice", "Perpignan", "Nîmes",
    "Foix", "Carcassonne", "Rodez", "Avignon", "Toulon", "Ajaccio", "Bastia"
]

def fetch_google_news(query: str):
    url = f"https://news.google.com/rss/search?q={requests.utils.requote_uri(query)}"
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    items = []
    for entry in feed.entries[:8]:
        title = getattr(entry, "title", "Sans titre")
        link = getattr(entry, "link", "#")
        summary = getattr(entry, "summary", "Aucune description")
        published = getattr(entry, "published", datetime.now(timezone.utc).isoformat())
        items.append({
            "title": title,
            "summary": summary,
            "url": link,
            "date": published
        })
    return items

def build_items():
    collected = []
    seen = set()

    queries = []
    for theme in THEMES:
        for geo in GEOGRAPHY:
            queries.append(f"{theme} {geo}")

    for query in queries:
        for item in fetch_google_news(query):
            key = (item["title"], item["url"])
            if key in seen:
                continue
            seen.add(key)

            region = "OCCITANIE"
            if any(g in query.lower() for g in ["marseille", "nice", "toulon", "avignon"]):
                region = "PACA"
            elif any(g in query.lower() for g in ["ajaccio", "bastia"]):
                region = "CORSE"

            department = "Haute-Garonne"
            city = "Toulouse"
            if "montpellier" in query.lower():
                department = "Hérault"; city = "Montpellier"
            elif "marseille" in query.lower():
                department = "Bouches-du-Rhône"; city = "Marseille"
            elif "nice" in query.lower():
                department = "Alpes-Maritimes"; city = "Nice"
            elif "perpignan" in query.lower():
                department = "Pyrénées-Orientales"; city = "Perpignan"
            elif "nîmes" in query.lower() or "nimes" in query.lower():
                department = "Gard"; city = "Nîmes"
            elif "foix" in query.lower():
                department = "Ariège"; city = "Foix"
            elif "carcassonne" in query.lower():
                department = "Aude"; city = "Carcassonne"
            elif "rodez" in query.lower():
                department = "Aveyron"; city = "Rodez"
            elif "toulon" in query.lower():
                department = "Var"; city = "Toulon"
            elif "ajaccio" in query.lower():
                department = "Corse-du-Sud"; city = "Ajaccio"
            elif "bastia" in query.lower():
                department = "Haute-Corse"; city = "Bastia"

            theme_label = "Sécurité & Criminalité"
            subtheme = "Cybercriminalite"

            for theme in [
                ("ordre public", "Ordre Public & Mouvements Sociaux", "Manifestation"),
                ("manifestation", "Ordre Public & Mouvements Sociaux", "Manifestation"),
                ("grève", "Ordre Public & Mouvements Sociaux", "Greve"),
                ("sécurité", "Sécurité & Criminalité", "Delinquance criminalite"),
                ("criminalité", "Sécurité & Criminalité", "Delinquance criminalite"),
                ("radicalisation", "Idéologies & Radicalités", "Radicalisation"),
                ("politique", "Institutions & Politique", "Visite Officielle"),
                ("éducation", "Institutions & Politique", "Enseignement Education nationale"),
                ("santé", "Institutions & Politique", "Sante"),
                ("transport", "Secteurs Stratégiques & Environnement", "Transports"),
                ("nucleaire", "Secteurs Stratégiques & Environnement", "Nucleaire"),
                ("agriculture", "Secteurs Stratégiques & Environnement", "Agriculture"),
                ("drones", "Sécurité & Criminalité", "Drones"),
                ("cybercriminalité", "Sécurité & Criminalité", "Cybercriminalite")
            ]:
                key_theme, key_label, key_sub = theme
                if key_theme in query.lower():
                    theme_label = key_label
                    subtheme = key_sub
                    break

            collected.append({
                "title": item["title"],
                "summary": item["summary"][:240],
                "url": item["url"],
                "date": item["date"],
                "theme": theme_label,
                "subtheme": subtheme,
                "region": region,
                "department": department,
                "city": city,
                "source": "Google News"
            })

    return collected[:40]

def main():
    DATA_DIR.mkdir(exist_ok=True)
    items = build_items()
    payload = {"items": items}
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Écrit {len(items)} éléments dans {DATA_FILE}")

if __name__ == "__main__":
    main()
