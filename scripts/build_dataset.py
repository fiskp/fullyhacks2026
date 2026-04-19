"""
build_dataset.py — one-time pipeline to build the SEA SWIPES animal dataset.

Flow:
  1. Kick off website crawl jobs on three marine-biology seed URLs via POST /v1/indexes.
  2. Poll each job until status = "completed".
  3. For each animal, run a HD vector search to find the best matching source URL
     for attribution. Weights are hardcoded (accurate) — HD search is used only
     for source discovery, not weight extraction.
  4. Write the curated dataset to the HD virtual filesystem at
     /agent/sea-swipes/animals.json via POST /v1/fs { op: "write" }.

The game (game.js) reads /agent/sea-swipes/animals.json at startup
via the same FS API — no local JSON file needed.

Requires:  pip install requests
Env var:   HD_API_KEY — your Human Delta API key (hd_live_...)
"""

import os
import time
import json
import requests

HD_API_KEY = os.environ["HD_API_KEY"]
BASE_URL = "https://api.humandelta.ai"
HEADERS = {"Authorization": f"Bearer {HD_API_KEY}", "Content-Type": "application/json"}

SEED_SITES = [
    ("Oceana Marine Life",       "https://oceana.org/marine-life/"),
    ("NOAA Fisheries Species",   "https://www.fisheries.noaa.gov/species"),
    ("Marine Mammal Center",     "https://www.marinemammalcenter.org/animal-care/learn-about-marine-mammals"),
]

# (name, emoji, weight_kg, fun_fact)
# weight_kg values are hardcoded from known averages; HD search supplies source URLs only.
ANIMALS = [
    ("Blue Whale",             "🐋", 150_000, "Heaviest animal ever known to exist"),
    ("Bowhead Whale",          "🐋", 100_000, "Can live over 200 years"),
    ("Fin Whale",              "🐋",  70_000, "Second-largest animal on Earth"),
    ("Sperm Whale",            "🐳",  57_000, "Deepest-diving toothed whale"),
    ("Humpback Whale",         "🐋",  36_000, "Famous for its complex songs"),
    ("Gray Whale",             "🐋",  36_000, "Migrates up to 20,000 km round trip"),
    ("Sei Whale",              "🐋",  28_000, "One of the fastest baleen whales"),
    ("Whale Shark",            "🦈",  18_000, "Largest fish in the ocean"),
    ("Minke Whale",            "🐋",   7_500, "Smallest of the baleen whales"),
    ("Orca",                   "🐬",   5_400, "Apex predator of the ocean"),
    ("Basking Shark",          "🦈",   4_000, "Second-largest fish alive"),
    ("Pilot Whale",            "🐬",   3_000, "Actually a large dolphin species"),
    ("Ocean Sunfish",          "🐟",   2_300, "Heaviest bony fish alive"),
    ("Elephant Seal",          "🦭",   2_200, "Males can weigh over 2,000 kg"),
    ("Giant Manta Ray",        "🐟",   2_000, "Biggest of the manta rays"),
    ("Beluga Sturgeon",        "🐟",   1_500, "One of the largest freshwater fish"),
    ("Beluga Whale",           "🐳",   1_500, "Known as the canary of the sea"),
    ("Narwhal",                "🦄",   1_600, "The unicorn of the sea"),
    ("Manta Ray",              "🐟",   1_350, "Largest ray, wingspan up to 7 m"),
    ("Great White Shark",      "🦈",   1_100, "Most famous apex predator"),
    ("Steller Sea Lion",       "🦭",   1_000, "Largest of the eared seals"),
    ("Greenland Shark",        "🦈",   1_000, "Slowest and longest-lived shark"),
    ("Leatherback Sea Turtle", "🐢",     900, "Largest living reptile"),
    ("Atlantic Bluefin Tuna",  "🐟",     680, "One of the fastest open-water fish"),
    ("Polar Bear",             "🐻‍❄️",     700, "Largest land carnivore, often at sea"),
    ("Swordfish",              "🐟",     650, "Uses its bill to slash prey"),
    ("Colossal Squid",         "🦑",     750, "Heaviest known invertebrate"),
    ("Tiger Shark",            "🦈",     635, "Known for eating almost anything"),
    ("Walrus",                 "🦭",   1_200, "Uses tusks to haul out of water"),
    ("Sixgill Shark",          "🦈",     590, "Deep-water primitive shark species"),
    ("Marlin",                 "🐟",     818, "Bill used to slash prey"),
    ("Leopard Seal",           "🦭",     600, "Primary predator of penguins"),
    ("Weddell Seal",           "🦭",     600, "Can dive to 600 m depth"),
    ("Manatee",                "🐄",     600, "Gentle herbivore of warm waters"),
    ("Hammerhead Shark",       "🦈",     450, "Uses wide head for 360 deg vision"),
    ("Pacific Sleeper Shark",  "🦈",     400, "Slow-moving deep-water giant"),
    ("Risso's Dolphin",        "🐬",     400, "Heavily scarred from squid battles"),
    ("Dugong",                 "🐄",     400, "Close relative of the manatee"),
    ("Atlantic Halibut",       "🐟",     316, "Largest flatfish in the Atlantic"),
    ("Bottlenose Dolphin",     "🐬",     300, "Highly intelligent social animal"),
    ("Sea Lion",               "🦭",     300, "Known for agility and intelligence"),
    ("Giant Squid",            "🦑",     275, "Largest invertebrate on Earth"),
    ("Oarfish",                "🐟",     270, "Longest bony fish in the world"),
    ("Giant Pacific Octopus",  "🐙",     272, "Largest octopus species"),
    ("Goblin Shark",           "🦈",     210, "Deep-sea shark with protruding jaws"),
    ("Green Sea Turtle",       "🐢",     190, "Named for its greenish fat"),
    ("Giant Clam",             "🐚",     200, "Largest bivalve mollusk"),
    ("Bull Shark",             "🦈",     230, "Can survive in freshwater"),
    ("Loggerhead Sea Turtle",  "🐢",     135, "Named for its large head"),
    ("Common Dolphin",         "🐬",     110, "One of the fastest cetaceans"),
    ("Sailfish",               "🐟",     100, "Fastest fish in the ocean"),
    ("Spinner Dolphin",        "🐬",      75, "Named for its aerial spins"),
    ("Giant Moray Eel",        "🐍",      30, "Largest moray eel species"),
    ("Japanese Spider Crab",   "🦀",      19, "Widest leg span of any arthropod"),
    ("King Crab",              "🦀",      12, "One of the largest crustaceans"),
    ("Goliath Grouper",        "🐟",     360, "Can weigh over 360 kg"),
    ("Sea Otter",              "🦦",      45, "Densest fur of any mammal"),
    ("Barracuda",              "🐟",      50, "Known for speed and sharp teeth"),
    ("Harbour Porpoise",       "🐬",      60, "Smallest cetacean in the North Atlantic"),
    ("Horseshoe Crab",         "🦀",       5, "Living fossil, 450 million years old"),
]

POLL_INTERVAL = 5   # seconds; docs recommend 3-5 s
HD_FS_PATH = "/agent/sea-swipes/animals.json"


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
    time.sleep(3)  # brief pause before first poll to avoid race on new jobs
    retries = 0
    while True:
        resp = requests.get(f"{BASE_URL}/v1/indexes/{index_id}", headers=HEADERS)
        if resp.status_code == 401 and retries < 5:
            retries += 1
            time.sleep(POLL_INTERVAL)
            continue
        resp.raise_for_status()
        retries = 0
        status = resp.json()["status"]
        if status == "completed":
            return
        if status in terminal:
            raise RuntimeError(f"Crawl {index_id} ended with status '{status}'")
        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Step 2 — HD search for source URL attribution
# ---------------------------------------------------------------------------

def search_source(animal_name: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/v1/search",
        headers=HEADERS,
        json={
            "query": f"{animal_name} marine animal",
            "top_k": 1,
            "sources": ["web"],
        },
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return {"score": 0.0, "source_url": ""}
    top = results[0]
    return {
        "score":      top["score"],
        "source_url": top["source_url"],
    }


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

    # Step 2 — search for source URLs (weights are hardcoded)
    print(f"\nFinding source URLs for {len(ANIMALS)} animals...")
    dataset = []

    for name, emoji, weight_kg, fun_fact in ANIMALS:
        print(f"  {name}... ", end="", flush=True)
        result = search_source(name)
        dataset.append({
            "name":      name,
            "weight_kg": weight_kg,
            "hd_score":  round(result["score"], 4),
            "source":    result["source_url"],
            "fun_fact":  fun_fact,
            "emoji":     emoji,
        })
        print(f"{weight_kg:,} kg  (source score={result['score']:.2f})")

    dataset.sort(key=lambda x: x["weight_kg"], reverse=True)

    # Step 3 — persist to HD filesystem
    print(f"\nWriting {len(dataset)} animals to HD FS at {HD_FS_PATH}...")
    write_to_hd_fs(dataset)
    print("Done.")



if __name__ == "__main__":
    main()
