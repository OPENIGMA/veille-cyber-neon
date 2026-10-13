#!/usr/bin/env python3
# scripts/collect_feeds.py
# V3: scoring par thème + équilibrage + debug scoring

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

# géos de la zone
GEOGRAPHY = [
    "Toulouse", "Montpellier", "Marseille", "Nice", "Perpignan", "Nîmes",
    "Foix", "Carcassonne", "Rodez", "Avignon", "Toulon", "Ajaccio", "Bastia"
]

# Poids de thèmes : plus le mot est précis, plus le score est grand
THEME_WEIGHTS = {
    "Ordre Public & Mouvements Sociaux": {
        "manifestation": 8,
        "manif": 9,
        "manifestants": 9,
        "rassemblement": 6,
        "grève": 9,
        "greve": 9,
        "blocage": 9,
        "squat": 9,
        "free rave": 8,
        "technival": 8,
        "occupation": 5,
        "voie publique": 5,
        "circulation": 3,
        "ordre public": 6,
        "mobilisation": 4,
    },
    "Sécurité & Criminalité": {
        "cyber": 10,
        "cybercriminalité": 12,
        "cybercriminalite": 12,
        "attaque": 9,
        "ransomware": 11,
        "piratage": 11,
        "hacker": 10,
        "drones": 10,
        "armes": 8,
        "criminalité": 8,
        "criminalite": 8,
        "incendie": 4,
        "trafic": 3,
        "infrastructure": 7,
        "sécurité": 5,
        "securite": 5,
    },
    "Idéologies & Radicalités": {
        "radicalisation": 12,
        "radical": 8,
        "terrorisme": 12,
        "terroriste": 11,
        "secte": 10,
        "separatisme": 11,
        "séparatisme": 11,
        "ultra-droite": 12,
        "ultra-gauche": 12,
        "gauche radicale": 9,
        "droite radicale": 9,
        "apologie": 8,
        "extrémisme": 9,
        "extremisme": 9,
        "idéologie": 7,
        "ideologie": 7,
    },
    "Institutions & Politique": {
        "élections": 11,
        "elections": 11,
        "visite officielle": 10,
        "éducation": 9,
        "education": 9,
        "santé": 9,
        "sante": 9,
        "politique": 6,
        "gouvernement": 5,
        "mairie": 4,
        "préfecture": 5,
        "prefecture": 5,
        "institution": 6,
    },
    "Secteurs Stratégiques & Environnement": {
        "agriculture": 10,
        "nucleaire": 11,
        "nucléaire": 11,
        "ferroviaire": 10,
        "transport": 8,
        "transports": 8,
        "energie": 7,
        "énergie": 7,
        "environnement": 6,
        "pollution": 5,
        "canalisation": 5,
        "infrastructure": 5,
    }
}

# sélection des requêtes de recherche, séparées par thème pour éviter le biais d'un seul thème
QUERY_GROUPS = {
    "Ordre Public & Mouvements Sociaux": [
        "manifestation Toulouse", "manifestation Marseille", "manifestation Montpellier",
        "grève Toulouse", "grève Marseille", "grève Montpellier",
        "squat Toulouse", "blocage Marseille", "free rave Montpellier",
        "mobilisation rue Toulouse", "ordre public Marseille"
    ],
    "Sécurité & Criminalité": [
        "cyber Toulouse", "cyber Marseille", "cyber Montpellier",
        "ransomware Toulouse", "attaque Marseille", "drones Nice",
        "armes Toulouse", "criminalité Marseille", "infrastructure critique Toulouse"
    ],
    "Idéologies & Radicalités": [
        "radicalisation Toulon", "radicalisation Marseille", "separatisme Montpellier",
        "ultra-droite Nice", "ultra-gauche Marseille", "secte Toulouse",
        "terrorisme Marseille", "extrémisme Montpellier"
    ],
    "Institutions & Politique": [
        "élections Toulouse", "élections Marseille", "visite officielle Toulouse",
        "éducation Montpellier", "santé Marseille", "politique Toulouse",
        "préfecture Marseille", "institution Toulouse"
    ],
    "Secteurs Stratégiques & Environnement": [
        "agriculture Toulouse", "agriculture Montpellier", "nucléaire Marseille",
        "transport Toulon", "ferroviaire Toulouse", "transport Nice",
        "énergie Marseille", "environnement Montpellier"
    ]
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
            if image.startswith('//'):
                image = 'https:' + image
            if image.startswith('http:'):
                image = 'https:' + image.split('http:')[-1]
            if not image.lower().startswith('http'):
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


def score_theme_for_text(theme_name: str, text: str) -> int:
    score = 0
    normalized = text.lower()
    for word, weight in THEME_WEIGHTS[theme_name].items():
        if ' ' in word:
            if word in normalized:
                score += weight * 2
        else:
            # match word-boundary to avoid counting substrings in unrelated words
            pattern = r'\b' + re.escape(word) + r'\b'
            score += len(re.findall(pattern, normalized)) * weight
    return score


def classify_theme(title: str, summary: str):
    text = (title or '') + ' ' + (summary or '')
    scored = {}
    for theme_name in THEME_WEIGHTS:
        scored[theme_name] = score_theme_for_text(theme_name, text)

    # si aucun score → fallback sécurité
    if not any(score > 0 for score in scored.values()):
        return "Sécurité & Criminalité", "Delinquance criminalite", scored

    # choisir le meilleur
    best_theme = max(scored.items(), key=lambda kv: kv[1])[0]
    best_score = scored[best_theme]

    # sous-thème par thème
    if best_theme == "Ordre Public & Mouvements Sociaux":
        sub = "Manifestation" if 'manifestation' in text.lower() or 'manif' in text.lower() else "Greve" if 'grève' in text.lower() or 'greve' in text.lower() else "Squat" if 'squat' in text.lower() else "Blocage occupation"
    elif best_theme == "Sécurité & Criminalité":
        sub = "Cybercriminalite" if 'cyber' in text.lower() or 'ransomware' in text.lower() or 'piratage' in text.lower() else "Drones" if 'drone' in text.lower() else "Armes" if 'arme' in text.lower() else "Delinquance criminalite"
    elif best_theme == "Idéologies & Radicalités":
        sub = "Radicalisation" if 'radical' in text.lower() else "Separatisme" if 'separatisme' in text.lower() or 'sèparatisme' in text.lower() else "Terrorisme" if 'terror' in text.lower() else "Derives sectaires" if 'secte' in text.lower() else "Ultra-droite"
    elif best_theme == "Institutions & Politique":
        sub = "Elections 2027" if 'election' in text.lower() else "Sante" if 'sant' in text.lower() else "Enseignement Education nationale" if 'educ' in text.lower() else "Visite Officielle" if 'visite' in text.lower() else "Culte"
    else:
        sub = "Transports" if 'transport' in text.lower() else "Agriculture" if 'agric' in text.lower() else "Nucleaire" if 'nucle' in text.lower() else "Transports"

    return best_theme, sub, scored


def build_items():
    collected = []
    seen = set()
    per_theme_counter = {theme: 0 for theme in QUERY_GROUPS}
    MAX_PER_THEME = 20

    for theme_name, queries in QUERY_GROUPS.items():
        for query in queries:
            items = fetch_google_news(query, max_items=5)
            for item in items:
                key = (item['title'], item['url'])
                if key in seen:
                    continue
                seen.add(key)

                # si le thème est déjà rempli -> on passe
                if per_theme_counter[theme_name] >= MAX_PER_THEME:
                    continue

                best_theme, sub, scores = classify_theme(item['title'], item['summary'])

                # On force un équilibre : si le thème est largement dominant, on accepte seulement s’il est le meilleur score
                payload = {
                    "title": item['title'],
                    "summary": item['summary'],
                    "url": item['url'],
                    "date": item['date'],
                    "theme": best_theme,
                    "subtheme": sub,
                    "source": "Google News",
                    "image": item.get('image'),
                    "scores": scores,
                    "assigned_by": "scoring-v3"
                }

                # région simple en fonction de la query / geographie
                qlow = query.lower()
                if any(v in qlow for v in ["marseille", "nice", "toulon", "avignon"]):
                    payload["region"] = "PACA"
                elif any(v in qlow for v in ["ajaccio", "bastia"]):
                    payload["region"] = "CORSE"
                else:
                    payload["region"] = "OCCITANIE"

                # city / dept best effort
                payload["city"] = ""
                payload["department"] = ""
                for city in GEOGRAPHY:
                    if city.lower() in (item['title'] + ' ' + item['summary']).lower():
                        payload['city'] = city
                        break
                if payload['city'] == "Toulouse":
                    payload['department'] = 'Haute-Garonne'
                elif payload['city'] == 'Marseille':
                    payload['department'] = 'Bouches-du-Rhône'
                elif payload['city'] == 'Nice':
                    payload['department'] = 'Alpes-Maritimes'
                elif payload['city'] == 'Montpellier':
                    payload['department'] = 'Hérault'
                elif payload['city'] == 'Toulon':
                    payload['department'] = 'Var'
                elif payload['city'] == 'Perpignan':
                    payload['department'] = 'Pyrénées-Orientales'
                elif payload['city'] == 'Nîmes' or payload['city'] == 'Nimes':
                    payload['department'] = 'Gard'
                elif payload['city'] == 'Ajaccio':
                    payload['department'] = 'Corse-du-Sud'
                elif payload['city'] == 'Bastia':
                    payload['department'] = 'Haute-Corse'

                collected.append(payload)
                per_theme_counter[best_theme] = per_theme_counter.get(best_theme, 0) + 1

                if len(collected) >= 80:
                    return collected

    return collected


def main():
    DATA_DIR.mkdir(exist_ok=True)
    items = build_items()
    payload = {
        "items": items
    }
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Écrit {len(items)} éléments dans {DATA_FILE}")


if __name__ == "__main__":
    main()
