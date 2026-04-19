"""
build_dataset.py — one-time pipeline to build the Depth Charge animal dataset.

Flow:
  1. Kick off website crawl jobs on three marine-biology seed URLs via POST /v1/indexes.
  2. Poll each job until status = "completed".
  3. Vector-search each animal's weight via POST /v1/search.
  4. Filter results with score < 0.85, parse weight from text.
  5. Write the curated dataset to the HD virtual filesystem at
     /agent/sea-slides/animals.json via POST /v1/fs { op: "write" }.

The game (game.js) reads /agent/sea-slides/animals.json at startup
via the same FS API — no local JSON file needed.

Requires:  pip install requests
Env var:   HD_API_KEY — your Human Delta API key (hd_live_...)
"""

import os
import time
import json
import re
import requests

HD_API_KEY = os.environ["HD_API_KEY"]
BASE_URL = "https://api.humandelta.ai"
HEADERS = {"Authorization": f"Bearer {HD_API_KEY}", "Content-Type": "application/json"}

SEED_SITES = [
    ("Oceana Marine Life",       "https://oceana.org/marine-life/"),
    ("NOAA Fisheries Species",   "https://www.fisheries.noaa.gov/species"),
    ("Marine Mammal Center",     "https://www.marinemammalcenter.org/animal-care/learn-about-marine-mammals"),
]

ANIMALS = [
    ("Blue Whale",                "🐋", "Heaviest animal ever known to exist"),
    ("Orca",                      "🐬", "Apex predator of the ocean"),
    ("Sperm Whale",               "🐳", "Deepest-diving toothed whale"),
    ("Humpback Whale",            "🐋", "Famous for complex songs"),
    ("Fin Whale",                 "🐋", "Second-largest animal on Earth"),
    ("Sei Whale",                 "🐋", "One of the fastest baleen whales"),
    ("Gray Whale",                "🐋", "Migrates up to 20,000 km round trip"),
    ("Beluga Whale",              "🐳", "Known as the canary of the sea"),
    ("Narwhal",                   "🦄", "The unicorn of the sea"),
    ("Bowhead Whale",             "🐋", "Can live over 200 years"),
    ("Minke Whale",               "🐋", "Smallest of the baleen whales"),
    ("Pilot Whale",               "🐬", "Actually a large dolphin species"),
    ("Walrus",                    "🦭", "Uses tusks to haul out of water"),
    ("Elephant Seal",             "🦭", "Males can weigh over 2,000 kg"),
    ("Steller Sea Lion",          "🦭", "Largest of the eared seals"),
    ("Sea Lion",                  "🦭", "Known for agility and intelligence"),
    ("Leopard Seal",              "🦭", "Primary predator of penguins"),
    ("Weddell Seal",              "🦭", "Can dive to 600 m depth"),
    ("Manatee",                   "🐄", "Gentle herbivore of warm waters"),
    ("Dugong",                    "🐄", "Close relative of the manatee"),
    ("Great White Shark",         "🦈", "Most famous apex predator"),
    ("Whale Shark",               "🦈", "Largest fish in the ocean"),
    ("Basking Shark",             "🦈", "Second-largest fish alive"),
    ("Tiger Shark",               "🦈", "Known for eating almost anything"),
    ("Bull Shark",                "🦈", "Can survive in freshwater"),
    ("Hammerhead Shark",          "🦈", "Uses wide head for 360° vision"),
    ("Manta Ray",                 "🐟", "Largest ray, wingspan up to 7 m"),
    ("Giant Manta Ray",           "🐟", "Biggest of the manta rays"),
    ("Bottlenose Dolphin",        "🐬", "Highly intelligent social animal"),
    ("Common Dolphin",            "🐬", "Fastest cetacean swimmer"),
    ("Spinner Dolphin",           "🐬", "Named for its aerial spins"),
    ("Risso's Dolphin",           "🐬", "Heavily scarred from squid battles"),
    ("Giant Squid",               "🦑", "Largest invertebrate on Earth"),
    ("Colossal Squid",            "🦑", "Heaviest known invertebrate"),
    ("Giant Pacific Octopus",     "🐙", "Largest octopus species"),
    ("Goliath Grouper",           "🐟", "Can weigh over 360 kg"),
    ("Atlantic Bluefin Tuna",     "🐟", "Fastest open-water fish"),
    ("Oarfish",                   "🐟", "Longest bony fish in the world"),
    ("Ocean Sunfish",             "🐟", "Heaviest bony fish alive"),
    ("Sailfish",                  "🐟", "Fastest fish in the ocean"),
    ("Marlin",                    "🐟", "Bill used to slash prey"),
    ("Swordfish",                 "🐟", "Bill used to slash prey"),
    ("Giant Moray Eel",           "🐍", "Largest moray eel species"),
    ("Barracuda",                 "🐟", "Known for speed and sharp teeth"),
    ("King Crab",                 "🦀", "One of the largest crustaceans"),
    ("Japanese Spider Crab",      "🦀", "Widest leg span of any arthropod"),
    ("Loggerhead Sea Turtle",     "🐢", "Named for its large head"),
    ("Leatherback Sea Turtle",    "🐢", "Largest living reptile"),
    ("Green Sea Turtle",          "🐢", "Named for its greenish fat"),
    ("Horseshoe Crab",            "🦀", "Living fossil, 450 million years old"),
    ("Giant Clam",                "🐚", "Largest bivalve mollusk"),
    ("Sea Otter",                 "🦦", "Densest fur of any mammal"),
    ("Polar Bear",                "🐻‍❄️", "Largest land carnivore, often at sea"),
    ("Harbour Porpoise",          "🐬", "Smallest cetacean in the North Atlantic"),
    ("Beluga Sturgeon",           "🐟", "One of the largest fish in the world"),
    ("Atlantic Halibut",          "🐟", "Largest flatfish in the Atlantic"),
    ("Greenland Shark",           "🦈", "Slowest and longest-lived shark"),
    ("Sixgill Shark",             "🦈", "Deep-water primitive shark species"),
    ("Goblin Shark",              "🦈", "Deep-sea shark with protruding jaws"),
    ("Pacific Sleeper Shark",     "🦈", "Slow-moving deep-water giant"),
]

SCORE_THRESHOLD = 0.85
POLL_INTERVAL = 5   # seconds; docs recommend 3-5 s
HD_FS_PATH = "/agent/sea-slides/animals.json"


# ---------------------------------------------------------------------------
# Step 1 — Crawl index jobs
# ---------------------------------------------------------------------------

def start_crawl(name: str, url: str) -> str:
    resp = requests.post(
        f"{BASE_URL}/v1/indexes",
        headers=HEADERS,
        json={
            "source_type": "website",
            "name": name,
            "website": {"url": url, "max_pages": 100},
        },
    )
    resp.raise_for_status()
    return resp.json()["index_id"]


def poll_until_complete(index_id: str) -> None:
    terminal = {"completed", "failed", "cancelled"}
    while True:
        resp = requests.get(f"{BASE_URL}/v1/indexes/{index_id}", headers=HEADERS)
        resp.raise_for_status()
        status = resp.json()["status"]
        if status == "completed":
            return
        if status in terminal:
            raise RuntimeError(f"Crawl {index_id} ended with status '{status}'")
        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Step 2 — Vector search per animal
# ---------------------------------------------------------------------------

def search_weight(animal_name: str) -> dict | None:
    resp = requests.post(
        f"{BASE_URL}/v1/search",
        headers=HEADERS,
        json={
            "query": f"{animal_name} average weight kilograms",
            "top_k": 3,
            "sources": ["web"],
        },
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return None
    top = results[0]
    return {
        "score":      top["score"],
        "text":       top["text"],
        "source_url": top["source_url"],
    }


def extract_weight_kg(text: str) -> float | None:
    # kg
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*kg", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", ""))
    # metric tonnes
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:metric\s*)?tonn?e", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "")) * 1000
    # short tons
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:short\s*)?ton", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "")) * 907.185
    # pounds
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:lb|lbs|pound)", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "")) * 0.453592
    return None


# ---------------------------------------------------------------------------
# Step 3 — Write dataset to HD virtual filesystem
# ---------------------------------------------------------------------------

def write_to_hd_fs(dataset: list[dict]) -> None:
    resp = requests.post(
        f"{BASE_URL}/v1/fs",
        headers=HEADERS,
        json={
            "op":      "write",
            "path":    HD_FS_PATH,
            "content": json.dumps(dataset, indent=2, ensure_ascii=False),
        },
    )
    resp.raise_for_status()
    if not resp.json().get("ok"):
        raise RuntimeError(f"FS write failed: {resp.json()}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Step 1 — kick off crawls
    print("Starting crawl index jobs...")
    index_ids = []
    for name, url in SEED_SITES:
        index_id = start_crawl(name, url)
        print(f"  Queued: '{name}' -> {index_id}")
        index_ids.append(index_id)

    print("Polling until all crawls complete...")
    for index_id in index_ids:
        poll_until_complete(index_id)
        print(f"  Completed: {index_id}")

    # Step 2 — search weights
    print(f"\nSearching weights for {len(ANIMALS)} animals...")
    dataset = []
    skipped = []

    for name, emoji, fun_fact in ANIMALS:
        print(f"  {name}... ", end="", flush=True)

        result = search_weight(name)
        if result is None:
            print("no results")
            skipped.append((name, "no results"))
            continue

        score = result["score"]
        if score < SCORE_THRESHOLD:
            print(f"score {score:.2f} below threshold")
            skipped.append((name, f"score {score:.2f}"))
            continue

        weight_kg = extract_weight_kg(result["text"])
        if weight_kg is None:
            print("could not parse weight")
            skipped.append((name, "unparseable weight"))
            continue

        dataset.append({
            "name":      name,
            "weight_kg": weight_kg,
            "hd_score":  round(score, 4),
            "source":    result["source_url"],
            "fun_fact":  fun_fact,
            "emoji":     emoji,
        })
        print(f"{weight_kg:,.0f} kg  (score={score:.2f})")

    dataset.sort(key=lambda x: x["weight_kg"], reverse=True)

    # Step 3 — persist to HD filesystem
    print(f"\nWriting {len(dataset)} animals to HD FS at {HD_FS_PATH}...")
    write_to_hd_fs(dataset)
    print("Done.")

    if skipped:
        print(f"\nSkipped {len(skipped)} animals:")
        for name, reason in skipped:
            print(f"  {name}: {reason}")


if __name__ == "__main__":
    main()
