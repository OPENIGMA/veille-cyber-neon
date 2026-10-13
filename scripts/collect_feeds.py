#!/usr/bin/env python3
# scripts/collect_feeds.py
# Améliorations:
# - meilleure détection des thèmes/subthèmes via mots-clés (mot entier)
# - extraction d'images (media_content, media_thumbnail, enclosure, img dans summary)
# - nettoyage du HTML dans les résumés
# - diversification des requêtes pour couvrir plus de sujets

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

# géos à cibler
GEOGRAPHY = [
    "Toulouse", "Montpellier", "Marseille", "Nice", "Perpignan", "Nîmes",
    "Foix", "Carcassonne", "Rodez", "Avignon", "Toulon", "Ajaccio", "Bastia"
]

# mots clés généraux pour couvrir plus de thématiques
KEYWORDS = [
    "manifestation", "grève", "blocage", "squat", "free rave", "technival",
    "cyber", "cybercriminalité", "attaque", "infrastructure", "drones", "armes",
    "radicalisation", "séparatisme", "secte", "terrorisme", "ultra-droite", "ultra-gauche",
    "agriculture", "nucleaire", "ferroviaire", "transport", "santé", "éducation",
    "élections", "visite officielle", "projet d'aménagement", "installation illicite"
]

# mapping mot-cle -> (label thème, sous-thème)
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
    "drones": ("Sécurité & Criminalité", "Drones"),
    "armes": ("Sécurité & Criminalité", "Armes"),

    "radicalisation": ("Idéologies & Radicalités", "Radicalisation"),
    "séparatisme": ("Idéologies & Radicalités", "Separatisme"),
    "separatisme": ("Idéologies & Radicalités", "Separatisme"),
    "secte": ("Idéologies & Radicalités", "Derives sectaires"),
    "terrorisme": ("Idéologies & Radicalités", "Terrorisme"),
    "ultra-droite": ("Idéologies & Radicalités", "Ultra-droite"),
    "ultra-gauche": ("Idéologies & Radicalités", "Ultra-gauche"),
    "animaliste": ("Idéologies & Radicalités", "Animaliste"),
    "écologie": ("Idéologies & Radicalités", "Ecologie"),
    "ecologie": ("Idéologies & Radicalités", "Ecologie"),
    "survivalisme": ("Idéologies & Radicalités", "Survivalisme"),

    "agriculture": ("Secteurs Stratégiques & Environnement", "Agriculture"),
    "nucleaire": ("Secteurs Stratégiques & Environnement", "Nucleaire"),
    "ferroviaire": ("Secteurs Stratégiques & Environnement", "Ferroviaire"),
    "transport": ("Secteurs Stratégiques & Environnement", "Transports"),
    "santé": ("Institutions & Politique", "Sante"),
    "sante": ("Institutions & Politique", "Sante"),
    "éducation": ("Institutions & Politique", "Enseignement Education nationale"),
    "education": ("Institutions & Politique", "Enseignement Education nationale"),
    "élections": ("Institutions & Politique", "Elections 2027"),
    "elections": ("Institutions & Politique", "Elections 2027"),
    "visite officielle": ("Institutions & Politique", "Visite Officielle"),
    "projet d'aménagement": ("Ordre Public & Mouvements Sociaux", "Projet Amenagement Conteste"),
    "installation illicite": ("Ordre Public & Mouvements Sociaux", "Installation illicite")
}

USER_AGENT = "veille-cyber-bot/1.0 (+https://github.com/OPENIGMA/veille-cyber-neon)"


def fetch_google_news(query: str, max_items: int = 6):
    url = f"https://news.google.com/rss/search?q={requests.utils.requote_uri(query)}&hl=fr&gl=FR&ceid=FR:fr"
    headers = {"User-Agent": USER_AGENT}
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []

    items = []
    for entry in feed.entries[:max_items]:
        title = getattr(entry, "title", "Sans titre")
        link = getattr(entry, "link", "#")
        summary_html = getattr(entry, "summary", "")

        # try to extract published date
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime.fromtimestamp(
                    feedparser.mktime_tz(entry.published_parsed), tz=timezone.utc
                ).astimezone().isoformat()
            except Exception:
                published = datetime.now(timezone.utc).isoformat()
        else:
            published = datetime.now(timezone.utc).isoformat()

        # try to extract image: media_content, media_thumbnail, enclosures, or <img> in summary
        image = None
        if 'media_content' in entry:
            m = entry.get('media_content')
            if isinstance(m, (list, tuple)) and m:
                image = m[0].get('url')
            elif isinstance(m, dict):
                image = m.get('url')
        if not image and 'media_thumbnail' in entry:
            mt = entry.get('media_thumbnail')
            if isinstance(mt, (list, tuple)) and mt:
                image = mt[0].get('url')
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

        # normaliser image url
        if image:
            image = image.strip()
            if image.startswith("//"):
                image = "https:" + image
            if image.startswith("http:"):
                image = "https:" + image.split("http:")[-1]
            if not image.lower().startswith("http"):
                image = None

        # sanitize summary: strip tags and unescape
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
    # essayer clés plus longues d'abord
    for kw in sorted(THEME_MAP.keys(), key=lambda x: -len(x)):
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, t, flags=re.IGNORECASE):
            return THEME_MAP[kw]
    # scoring fallback
    scores = {}
    for kw, (label, sub) in THEME_MAP.items():
        cnt = t.count(kw)
        if cnt:
            scores.setdefault((label, sub), 0)
            scores[(label, sub)] += cnt
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    # règles génériques
    if any(k in t for k in ["cyber", "hacker", "ransomware", "attaque"]):
        return ("Sécurité & Criminalité", "Cybercriminalite")
    if any(k in t for k in ["manifestation", "manif", "manifestants", "rassemblement"]):
        return ("Ordre Public & Mouvements Sociaux", "Manifestation")
    return ("Sécurité & Criminalité", "Delinquance criminalite")


def build_items():
    collected = []
    seen = set()

    # build queries: combine keywords with geographies and also add some generic queries
    queries = []
    for kw in KEYWORDS:
        for geo in GEOGRAPHY:
            queries.append(f"{kw} {geo}")
    # some generic queries (no geo) to catch wider topics
    queries.extend([kw for kw in KEYWORDS])
    # also add a few direct geo-only queries to find local news
    for geo in GEOGRAPHY:
        queries.append(geo)

    # deduplicate queries while preserving order
    seen_q = set()
    uniq_queries = []
    for q in queries:
        if q not in seen_q:
            seen_q.add(q)
            uniq_queries.append(q)

    for query in uniq_queries:
        items = fetch_google_news(query, max_items=6)
        for item in items:
            key = (item["title"], item["url"])
            if key in seen:
                continue
            seen.add(key)

            # derive region/department/city from query (best-effort)
            region = "OCCITANIE"
            qlow = query.lower()
            if any(g in qlow for g in ["marseille", "nice", "toulon", "avignon"]):
                region = "PACA"
            elif any(g in qlow for g in ["ajaccio", "bastia"]):
                region = "CORSE"

            # simple city->department mapping
            department = ""
            city = ""
            if "toulouse" in qlow:
                department = "Haute-Garonne"; city = "Toulouse"
            elif "montpellier" in qlow:
                department = "Hérault"; city = "Montpellier"
            elif "marseille" in qlow:
                department = "Bouches-du-Rhône"; city = "Marseille"
            elif "nice" in qlow:
                department = "Alpes-Maritimes"; city = "Nice"
            elif "perpignan" in qlow:
                department = "Pyrénées-Orientales"; city = "Perpignan"
            elif "nîmes" in qlow or "nimes" in qlow:
                department = "Gard"; city = "Nîmes"
            elif "foix" in qlow:
                department = "Ariège"; city = "Foix"
            elif "carcassonne" in qlow:
                department = "Aude"; city = "Carcassonne"
            elif "rodez" in qlow:
                department = "Aveyron"; city = "Rodez"
            elif "toulon" in qlow:
                department = "Var"; city = "Toulon"
            elif "ajaccio" in qlow:
                department = "Corse-du-Sud"; city = "Ajaccio"
            elif "bastia" in qlow:
                department = "Haute-Corse"; city = "Bastia"
            else:
                # fallback: try to detect city name inside title/summary
                for g in GEOGRAPHY:
                    if g.lower() in (item['title'] + ' ' + item['summary']).lower():
                        city = g
                        break
                if city:
                    department = ""
                else:
                    city = ""
                    department = ""

            # detect theme/subtheme from title+summary+query
            label, sub = detect_theme_subtheme(' '.join([query, item['title'], item['summary']]))
            if not label:
                # fallback heuristics
                ttxt = (item['title'] + ' ' + item['summary']).lower()
                if any(k in ttxt for k in ["cyber", "attaque", "hacker", "ransomware"]):
                    label, sub = ("Sécurité & Criminalité", "Cybercriminalite")
                elif any(k in ttxt for k in ["manifestation", "manifestants", "manif"]):
                    label, sub = ("Ordre Public & Mouvements Sociaux", "Manifestation")
                elif any(k in ttxt for k in ["radical", "terror"]):
                    label, sub = ("Idéologies & Radicalités", "Radicalisation")
                else:
                    label, sub = ("Sécurité & Criminalité", "Delinquance criminalite")

            payload_item = {
                "title": item["title"],
                "summary": item["summary"],
                "url": item["url"],
                "date": item["date"],
                "theme": label,
                "subtheme": sub,
                "region": region,
                "department": department,
                "city": city,
                "source": "Google News",
                "image": item.get('image')
            }

            collected.append(payload_item)

            # limit overall collected items to a reasonable number
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
