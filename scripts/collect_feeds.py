#!/usr/bin/env python3
# scripts/collect_feeds.py
# Correctif: le thème est détecté à partir du titre + résumé, pas de la query.
# Cela évite d'avoir toujours une seule thématique (manifestation) et permet
# d'obtenir des résultats plus diversifiés.

import json
from pathlib import Path
from datetime import datetime, timezone
import requests
import feedparser
import re
import html

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "veille.json"

GEOGRAPHY = [
    "Toulouse", "Montpellier", "Marseille", "Nice", "Perpignan", "Nîmes",
    "Foix", "Carcassonne", "Rodez", "Avignon", "Toulon", "Ajaccio", "Bastia"
]

THEME_MAP = {
    "manifestation": ("Ordre Public & Mouvements Sociaux", "Manifestation"),
    "grève": ("Ordre Public & Mouvements Sociaux", "Greve"),
    "greve": ("Ordre Public & Mouvements Sociaux", "Greve"),
    "blocage": ("Ordre Public & Mouvements Sociaux", "Blocage occupation"),
    "squat": ("Ordre Public & Mouvements Sociaux", "Squat"),
    "free rave": ("Ordre Public & Mouvements Sociaux", "Free Rave Teknival"),
    "technival": ("Ordre Public & Mouvements Sociaux", "Free Rave Teknival"),

    "cyber": ("Sécurité & Criminalité", "Cybercriminalite"),
    "cybercriminalité": ("Sécurité & Criminalité", "Cybercriminalite"),
    "cybercriminalite": ("Sécurité & Criminalité", "Cybercriminalite"),
    "attaque": ("Sécurité & Criminalité", "Delinquance criminalite"),
    "ransomware": ("Sécurité & Criminalité", "Cybercriminalite"),
    "piratage": ("Sécurité & Criminalité", "Cybercriminalite"),
    "drones": ("Sécurité & Criminalité", "Drones"),
    "armes": ("Sécurité & Criminalité", "Armes"),

    "radicalisation": ("Idéologies & Radicalités", "Radicalisation"),
    "séparatisme": ("Idéologies & Radicalités", "Separatisme"),
    "separatisme": ("Idéologies & Radicalités", "Separatisme"),
    "terrorisme": ("Idéologies & Radicalités", "Terrorisme"),
    "ultra-droite": ("Idéologies & Radicalités", "Ultra-droite"),
    "ultra-gauche": ("Idéologies & Radicalités", "Ultra-gauche"),
    "secte": ("Idéologies & Radicalités", "Derives sectaires"),
    "animaliste": ("Idéologies & Radicalités", "Animaliste"),
    "écologie": ("Idéologies & Radicalités", "Ecologie"),
    "ecologie": ("Idéologies & Radicalités", "Ecologie"),

    "agriculture": ("Secteurs Stratégiques & Environnement", "Agriculture"),
    "nucléaire": ("Secteurs Stratégiques & Environnement", "Nucleaire"),
    "nucleaire": ("Secteurs Stratégiques & Environnement", "Nucleaire"),
    "ferroviaire": ("Secteurs Stratégiques & Environnement", "Ferroviaire"),
    "transport": ("Secteurs Stratégiques & Environnement", "Transports"),

    "santé": ("Institutions & Politique", "Sante"),
    "sante": ("Institutions & Politique", "Sante"),
    "éducation": ("Institutions & Politique", "Enseignement Education nationale"),
    "education": ("Institutions & Politique", "Enseignement Education nationale"),
    "élections": ("Institutions & Politique", "Elections 2027"),
    "elections": ("Institutions & Politique", "Elections 2027"),
    "visite officielle": ("Institutions & Politique", "Visite Officielle")
}

USER_AGENT = "veille-cyber-bot/1.0 (+https://github.com/OPENIGMA/veille-cyber-neon)"


def fetch_google_news(query: str, max_items: int = 5):
    url = f"https://news.google.com/rss/search?q={requests.utils.requote_uri(query)}&hl=fr&gl=FR&ceid=FR:fr"
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []

    items = []
    for entry in feed.entries[:max_items]:
        title = getattr(entry, "title", "Sans titre")
        link = getattr(entry, "link", "#")
        summary_html = getattr(entry, "summary", "")

        published = datetime.now(timezone.utc).isoformat()
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime.fromtimestamp(
                    feedparser.mktime_tz(entry.published_parsed), tz=timezone.utc
                ).astimezone().isoformat()
            except Exception:
                pass

        image = None
        if 'media_content' in entry:
            media = entry.get('media_content')
            if isinstance(media, (list, tuple)) and media:
                image = media[0].get('url')
            elif isinstance(media, dict):
                image = media.get('url')

        if not image and 'media_thumbnail' in entry:
            thumb = entry.get('media_thumbnail')
            if isinstance(thumb, (list, tuple)) and thumb:
                image = thumb[0].get('url')

        if not image and 'enclosures' in entry:
            enc = entry.get('enclosures')
            if isinstance(enc, (list, tuple)) and enc:
                for e in enc:
                    if e.get('type', '').startswith('image') and e.get('href'):
                        image = e.get('href')
                        break

        if not image:
            pattern = r'<img[^>]+src=["\']?([^"\'>\s]+)'
            m = re.search(pattern, summary_html or '', re.IGNORECASE)
            if m:
                image = m.group(1)

        if image:
            image = image.strip()
            if image.startswith("//"):
                image = "https:" + image
            if image.startswith("http:"):
                image = "https:" + image.split("http:")[-1]
            if not image.lower().startswith("http"):
                image = None

        summary_text = html.unescape(re.sub('<[^<]+?>', '', summary_html)).strip()
        if len(summary_text) > 400:
            summary_text = summary_text[:397] + '...'

        items.append({
            "title": title,
            "summary": summary_text,
            "url": link,
            "date": published,
            "image": image
        })

    return items


def detect_theme_subtheme(text: str):
    t = text.lower()

    # 1) chercher dans le titre + résumé, pas dans la query
    for kw in sorted(THEME_MAP.keys(), key=lambda x: -len(x)):
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, t, flags=re.IGNORECASE):
            return THEME_MAP[kw]

    # 2) score
    scores = {}
    for kw, (label, sub) in THEME_MAP.items():
        cnt = t.count(kw)
        if cnt:
            scores[(label, sub)] = scores.get((label, sub), 0) + cnt

    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]

    # 3) fallback par mots-clés génériques
    lower_txt = t
    if any(k in lower_txt for k in ["cyber", "hacker", "ransomware", "attaque", "piratage", "drones"]):
        return ("Sécurité & Criminalité", "Cybercriminalite")
    if any(k in lower_txt for k in ["manifestation", "manif", "manifestants", "rassemblement"]):
        return ("Ordre Public & Mouvements Sociaux", "Manifestation")
    if any(k in lower_txt for k in ["radical", "terror", "secte", "séparatisme", "separatisme"]):
        return ("Idéologies & Radicalités", "Radicalisation")
    if any(k in lower_txt for k in ["agriculture", "nucleaire", "transport", "ferroviaire"]):
        return ("Secteurs Stratégiques & Environnement", "Transports")
    return ("Sécurité & Criminalité", "Delinquance criminalite")


def build_items():
    collected = []
    seen = set()

    grouped_queries = {
        "Ordre Public & Mouvements Sociaux": [
            "manifestation Toulouse", "manifestation Montpellier", "manifestation Marseille",
            "grève Toulouse", "grève Montpellier", "grève Marseille",
            "squat Toulouse", "blocage Marseille", "free rave Montpellier"
        ],
        "Sécurité & Criminalité": [
            "cyber Toulouse", "cyber Marseille", "cyber Montpellier",
            "drones Nice", "drones Toulon", "ransomware Toulouse",
            "attaque Marseille", "armes Toulouse"
        ],
        "Idéologies & Radicalités": [
            "radicalisation Toulon", "radicalisation Marseille", "separatisme Montpellier",
            "ultra-droite Nice", "ultra-gauche Marseille", "secte Toulouse"
        ],
        "Institutions & Politique": [
            "élections Toulouse", "élections Marseille", "visite officielle Toulouse",
            "éducation Montpellier", "santé Marseille", "santé Toulouse"
        ],
        "Secteurs Stratégiques & Environnement": [
            "agriculture Toulouse", "agriculture Montpellier", "nucléaire Marseille",
            "transport Toulon", "ferroviaire Toulouse", "transport Nice"
        ]
    }

    for theme_name, queries in grouped_queries.items():
        for query in queries:
            items = fetch_google_news(query, max_items=5)
            for item in items:
                key = (item["title"], item["url"])
                if key in seen:
                    continue
                seen.add(key)

                text = (item["title"] + " " + item["summary"]).lower()
                label, sub = detect_theme_subtheme(text)

                # Par sécurité, si l’article est vraiment hors sujet, on garde le thème de groupe
                if label == "Sécurité & Criminalité" and theme_name == "Ordre Public & Mouvements Sociaux":
                    if "manifestation" not in text and "grève" not in text and "blocage" not in text:
                        label, sub = (theme_name, "Divers")

                if label == "Ordre Public & Mouvements Sociaux" and theme_name == "Sécurité & Criminalité":
                    if "cyber" not in text and "attaque" not in text and "drones" not in text:
                        label, sub = (theme_name, "Divers")

                payload_item = {
                    "title": item["title"],
                    "summary": item["summary"],
                    "url": item["url"],
                    "date": item["date"],
                    "theme": label,
                    "subtheme": sub,
                    "region": "PACA" if any(v in query.lower() for v in ["marseille", "nice", "toulon", "avignon"]) else "OCCITANIE",
                    "department": "",
                    "city": "",
                    "source": "Google News",
                    "image": item.get("image")
                }

                collected.append(payload_item)
                if len(collected) >= 120:
                    return collected

    return collected


def main():
    DATA_DIR.mkdir(exist_ok=True)
    items = build_items()
    payload = {"items": items}
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Écrit {len(items)} éléments dans {DATA_FILE}")

if __name__ == "__main__":
    main()
