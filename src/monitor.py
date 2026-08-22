import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


MLB_URL = "https://www.mlb.com/cubs/video/topic/cubs-manager-postgame"
STATE_PATH = Path("src/state.json")

PLAYER_NAMES = [
    "Craig Counsell",
    "Jaxon Wiggins",
    "Dominick Reid",
    "Justin Steele",
    "Ben Brown",
    "Shota Imanaga",
    "Cade Horton",
    "Jordan Wicks",
    "Javier Assad",
    "Jameson Taillon",
    "Michael Busch",
    "Matt Shaw",
    "Pete Crow-Armstrong",
    "Seiya Suzuki",
    "Dansby Swanson",
    "Ian Happ",
    "Kyle Tucker",
    "Alex Bregman",
    "Edward Cabrera",
    "Matthew Boyd",
    "Nico Hoerner",
    "Colin Rea",
    "Kevin Gausman",
    "Antoine Kelly",
]

TOPIC_WORDS = {
    "INJURY": [
        "injury", "injured", "hurt", "soreness",
        "sore", "strain", "tightness", "oblique",
        "shoulder", "elbow", "back", "hamstring",
        "blister", "il"
    ],
    "REHAB": [
        "rehab", "rehabbing", "rehabilitation",
        "recovery", "throwing program",
        "rehab assignment"
    ],
    "RETURN": [
        "return", "returns", "back soon",
        "activated", "activation", "timeline",
        "expected back"
    ],
    "ROLE": [
        "role", "bullpen", "rotation",
        "closer", "starting", "relief"
    ],
    "WORKLOAD": [
        "innings", "pitch count", "pitches",
        "workload", "velocity"
    ],
}


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass

    return {
        "seen_ids": [],
        "initialized": False
    }


def save_state(state):
    STATE_PATH.write_text(
        json.dumps(state, indent=2) + "\n"
    )


def make_id(url):
    return hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:24]


def get_video_entries():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/139 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = requests.get(
        MLB_URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    entries = []
    found_urls = set()

    for link in soup.find_all("a", href=True):

        href = link["href"]

        if "/video/" not in href:
            continue

        if href.startswith("/"):
            href = "https://www.mlb.com" + href

        if "topic/cubs-manager-postgame" in href:
            continue

        title = clean(
            link.get_text(" ", strip=True)
        )

        if not title:
            continue

        combined = (
            title + " " + href
        ).lower()

        if "counsell" not in combined:
            continue

        if href in found_urls:
            continue

        found_urls.add(href)

        entries.append({
            "id": make_id(href),
            "title": title,
            "url": href
        })

    return entries


def get_description(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/139 Safari/537.36"
        )
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Try the normal description metadata.
        meta = soup.find(
            "meta",
            attrs={"name": "description"}
        )

        if meta and meta.get("content"):
            return clean(meta["content"])

        # Try OpenGraph description.
        meta = soup.find(
            "meta",
            attrs={
                "property": "og:description"
            }
        )

        if meta and meta.get("content"):
            return clean(meta["content"])

        # Try visible text.
        text = clean(
            soup.get_text(" ", strip=True)
        )

        return text[:1200]

    except Exception as exc:
        print(
            f"Could not get description for {url}: {exc}"
        )

        return ""


def classify(title, description):

    text = (
        title + " " + description
    ).lower()

    players = []

    for player in PLAYER_NAMES:
        if player.lower() in text:
            players.append(player)

    topics = []

    for topic, words in TOPIC_WORDS.items():
        if any(word in text for word in words):
            topics.append(topic)

    return players, topics


def send_notification(
    title,
    message,
    url,
    important=False
):

    topic = os.environ.get("NTFY_TOPIC")

    if not topic:
        print(
            "NTFY_TOPIC is not configured."
        )
        print(message)
        return

    server = os.environ.get(
        "NTFY_SERVER",
        "https://ntfy.sh"
    ).rstrip("/")

headers = {
    "Title": "COUNSELL ALERT",
    "Priority": (
        "high" if important
        else "default"
    ),
    "Tags": (
        "baseball,warning"
        if important
        else "baseball"
    ),
    "Click": url,
    "Content-Type":
        "text/plain; charset=utf-8",
}

    response = requests.post(
        f"{server}/{topic}",
        data=message.encode("utf-8"),
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    print("Notification sent successfully.")


def send_test_notification():

    send_notification(
        "🚨 COUNSELL ALERT — TEST",
        (
            "This is a test notification from your "
            "Cubs Counsell Alert system.\n\n"
            "If you're seeing this on your phone, "
            "your notification system is working."
        ),
        MLB_URL,
        important=True
    )


def process():

    state = load_state()

    entries = get_video_entries()

    print(
        f"Found {len(entries)} Counsell videos "
        "on the MLB page."
    )

    if not entries:
        raise RuntimeError(
            "MLB page returned zero Counsell videos."
        )

    seen = set(
        state.get("seen_ids", [])
    )

    # First successful run:
    # record existing videos without alerting
    # on every old video.
    if not state.get("initialized", False):

        for entry in entries:
            seen.add(entry["id"])

        state["seen_ids"] = list(seen)[-500:]
        state["initialized"] = True

        save_state(state)

        print(
            f"Initial setup complete. "
            f"Recorded {len(entries)} existing videos."
        )

        print(
            "Future new Counsell videos will "
            "generate notifications."
        )

        return

    new_entries = [
        entry
        for entry in entries
        if entry["id"] not in seen
    ]

    print(
        f"Found {len(new_entries)} new videos."
    )

    for entry in reversed(new_entries):

        description = get_description(
            entry["url"]
        )

        players, topics = classify(
            entry["title"],
            description
        )

        player_text = (
            ", ".join(players)
            if players
            else "No specific player identified"
        )

        topic_text = (
            ", ".join(topics)
            if topics
            else "MEDIA"
        )

        message = (
            "🚨 CRAIG COUNSELL MEDIA ALERT\n\n"
            f"Player(s): {player_text}\n"
            f"Topic: {topic_text}\n\n"
            f"MLB Title:\n{entry['title']}\n"
        )

        if description:
            message += (
                "\nMLB Description:\n"
                f"{description[:1000]}\n"
            )

        message += (
            "\n⚠️ EXACT QUOTE:\n"
            "Not yet verified by a transcript. "
            "The MLB description above is source "
            "metadata and is NOT being presented "
            "as a verbatim quote.\n\n"
            f"🎥 MLB Source:\n{entry['url']}\n\n"
            "Detected: "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        )

        important = bool(
            set(topics)
            & {"INJURY", "REHAB", "RETURN"}
        )

        send_notification(
            f"🚨 Counsell Alert — {entry['title']}",
            message,
            entry["url"],
            important
        )

        seen.add(entry["id"])

    state["seen_ids"] = list(seen)[-500:]

    save_state(state)

    print(
        f"Sent {len(new_entries)} new alerts."
    )


if __name__ == "__main__":

    if os.environ.get(
        "TEST_NOTIFICATION"
    ) == "true":

        send_test_notification()

    else:

        process()
