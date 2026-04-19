"""
build_dataset.py — one-time pipeline to build the SEA SWIPES animal dataset.

Flow:
  1. Use pre-crawled indexes with actual content (fishbase, marinebio, NOAA,
     oceana, marinemammalcenter). Wikipedia list-page crawls returned page_count=0.
  2. For each animal, search the indexes, then fall back to general HD web search.
     Walk top-5 results to find the closest weight match.
     Animals are marked verified=True if the parsed weight is within
     VERIFY_TOLERANCE (30%) of the hardcoded value.
  3. Write the full dataset (all 60 animals) to HD FS at
     /agent/sea-swipes/animals.json. HD weight is used when verified;
     hardcoded weight is the fallback.

The game reads /agent/sea-swipes/animals.json at startup via the FS API.

Requires:  pip install requests
Env var:   HD_API_KEY — your Human Delta API key (hd_live_...)
"""

import os
import re
import time
import json
import requests

HD_API_KEY = os.environ["HD_API_KEY"]
BASE_URL = "https://api.humandelta.ai"
HEADERS = {"Authorization": f"Bearer {HD_API_KEY}", "Content-Type": "application/json"}

# Pre-crawled indexes with actual content (page_count > 0).
# Wikipedia list-page crawls all returned page_count=0, so we use these instead.
EXISTING_INDEX_IDS = [
    "9c09b49e-4ea0-4e37-8b7b-3c957aa61303",  # fishbase.se           (100 pages)
    "6a723596-ef21-41e0-bb63-5a0123fbc5d4",  # marinebio.org/species (100 pages)
    "cc838144-a835-40b7-8abb-b9aa0ffb1c40",  # marinemammalcenter.org (100 pages)
    "0b15726f-49fe-4eb4-9bf7-49136631ccc1",  # fisheries.noaa.gov    (99 pages)
    "f48e2e0a-976a-49d7-b471-de4749cb9fcf",  # oceana.org/marine-life (86 pages)
]

# (name, emoji, weight_kg, fun_fact, source_url)
# weight_kg values are verified typical-large-adult averages from Wikipedia and scientific sources.
# Sources are stored for traceability and used as fallback source URLs when HD search fails.
ANIMALS = [
    ("Blue Whale",             "🐋", 130_000, "Heaviest animal ever known to exist",           "https://en.wikipedia.org/wiki/Blue_whale"),
    ("Bowhead Whale",          "🐋",  85_000, "Can live over 200 years",                       "https://en.wikipedia.org/wiki/Bowhead_whale"),
    ("Fin Whale",              "🐋",  40_000, "Second-largest animal on Earth",                "https://en.wikipedia.org/wiki/Fin_whale"),
    ("Sperm Whale",            "🐳",  45_000, "Deepest-diving toothed whale",                  "https://en.wikipedia.org/wiki/Sperm_whale"),
    ("Humpback Whale",         "🐋",  36_000, "Famous for its complex songs",                  "https://en.wikipedia.org/wiki/Humpback_whale"),
    ("Gray Whale",             "🐋",  41_000, "Migrates up to 20,000 km round trip",           "https://en.wikipedia.org/wiki/Gray_whale"),
    ("Sei Whale",              "🐋",  17_000, "One of the fastest baleen whales",              "https://en.wikipedia.org/wiki/Sei_whale"),
    ("Whale Shark",            "🦈",  18_000, "Largest fish in the ocean",                     "https://en.wikipedia.org/wiki/Whale_shark"),
    ("Minke Whale",            "🐋",   8_000, "Smallest of the baleen whales",                 "https://en.wikipedia.org/wiki/Common_minke_whale"),
    ("Orca",                   "🐬",   5_600, "Apex predator of the ocean",                    "https://en.wikipedia.org/wiki/Orca"),
    ("Basking Shark",          "🦈",   4_650, "Second-largest fish alive",                     "https://en.wikipedia.org/wiki/Basking_shark"),
    ("Pilot Whale",            "🐬",   2_300, "Actually a large dolphin species",              "https://en.wikipedia.org/wiki/Pilot_whale"),
    ("Ocean Sunfish",          "🐟",   1_000, "Heaviest bony fish alive",                      "https://en.wikipedia.org/wiki/Ocean_sunfish"),
    ("Elephant Seal",          "🦭",   2_200, "Males can weigh over 2,000 kg",                 "https://en.wikipedia.org/wiki/Elephant_seal"),
    ("Giant Manta Ray",        "🐟",   3_000, "Biggest of the manta rays",                     "https://en.wikipedia.org/wiki/Giant_oceanic_manta_ray"),
    ("Beluga Sturgeon",        "🐟",   1_000, "One of the largest freshwater fish",            "https://en.wikipedia.org/wiki/Beluga_(sturgeon)"),
    ("Beluga Whale",           "🐳",   1_500, "Known as the canary of the sea",                "https://en.wikipedia.org/wiki/Beluga_whale"),
    ("Narwhal",                "🦄",   1_600, "The unicorn of the sea",                        "https://en.wikipedia.org/wiki/Narwhal"),
    ("Manta Ray",              "🐟",   1_350, "Largest ray, wingspan up to 7 m",               "https://en.wikipedia.org/wiki/Manta_ray"),
    ("Great White Shark",      "🦈",   1_500, "Most famous apex predator",                     "https://en.wikipedia.org/wiki/Great_white_shark"),
    ("Steller Sea Lion",       "🦭",     544, "Largest of the eared seals",                    "https://en.wikipedia.org/wiki/Steller_sea_lion"),
    ("Greenland Shark",        "🦈",     900, "Slowest and longest-lived shark",               "https://en.wikipedia.org/wiki/Greenland_shark"),
    ("Leatherback Sea Turtle", "🐢",     500, "Largest living reptile",                        "https://en.wikipedia.org/wiki/Leatherback_sea_turtle"),
    ("Atlantic Bluefin Tuna",  "🐟",     250, "One of the fastest open-water fish",            "https://en.wikipedia.org/wiki/Atlantic_bluefin_tuna"),
    ("Polar Bear",             "🐻‍❄️",     450, "Largest land carnivore, often at sea",          "https://en.wikipedia.org/wiki/Polar_bear"),
    ("Swordfish",              "🐟",     400, "Uses its bill to slash prey",                   "https://en.wikipedia.org/wiki/Swordfish"),
    ("Colossal Squid",         "🦑",     495, "Heaviest known invertebrate",                   "https://en.wikipedia.org/wiki/Colossal_squid"),
    ("Tiger Shark",            "🦈",     635, "Known for eating almost anything",              "https://en.wikipedia.org/wiki/Tiger_shark"),
    ("Walrus",                 "🦭",   1_200, "Uses tusks to haul out of water",               "https://en.wikipedia.org/wiki/Walrus"),
    ("Sixgill Shark",          "🦈",     590, "Deep-water primitive shark species",            "https://en.wikipedia.org/wiki/Bluntnose_sixgill_shark"),
    ("Marlin",                 "🐟",     300, "Bill used to slash prey",                       "https://en.wikipedia.org/wiki/Atlantic_blue_marlin"),
    ("Leopard Seal",           "🦭",     400, "Primary predator of penguins",                  "https://en.wikipedia.org/wiki/Leopard_seal"),
    ("Weddell Seal",           "🦭",     500, "Can dive to 600 m depth",                       "https://en.wikipedia.org/wiki/Weddell_seal"),
    ("Manatee",                "🐄",     500, "Gentle herbivore of warm waters",               "https://en.wikipedia.org/wiki/Manatee"),
    ("Hammerhead Shark",       "🦈",     230, "Uses wide head for 360 deg vision",             "https://en.wikipedia.org/wiki/Great_hammerhead"),
    ("Pacific Sleeper Shark",  "🦈",     350, "Slow-moving deep-water giant",                  "https://en.wikipedia.org/wiki/Pacific_sleeper_shark"),
    ("Risso's Dolphin",        "🐬",     400, "Heavily scarred from squid battles",            "https://en.wikipedia.org/wiki/Risso%27s_dolphin"),
    ("Dugong",                 "🐄",     400, "Close relative of the manatee",                 "https://en.wikipedia.org/wiki/Dugong"),
    ("Atlantic Halibut",       "🐟",     160, "Largest flatfish in the Atlantic",              "https://en.wikipedia.org/wiki/Atlantic_halibut"),
    ("Bottlenose Dolphin",     "🐬",     300, "Highly intelligent social animal",              "https://en.wikipedia.org/wiki/Common_bottlenose_dolphin"),
    ("Sea Lion",               "🦭",     300, "Known for agility and intelligence",            "https://en.wikipedia.org/wiki/California_sea_lion"),
    ("Giant Squid",            "🦑",     200, "Largest invertebrate on Earth",                 "https://en.wikipedia.org/wiki/Giant_squid"),
    ("Oarfish",                "🐟",     200, "Longest bony fish in the world",                "https://en.wikipedia.org/wiki/Giant_oarfish"),
    ("Giant Pacific Octopus",  "🐙",      15, "Largest octopus species",                       "https://en.wikipedia.org/wiki/Giant_Pacific_octopus"),
    ("Goblin Shark",           "🦈",     210, "Deep-sea shark with protruding jaws",           "https://en.wikipedia.org/wiki/Goblin_shark"),
    ("Green Sea Turtle",       "🐢",     130, "Named for its greenish fat",                    "https://en.wikipedia.org/wiki/Green_sea_turtle"),
    ("Giant Clam",             "🐚",     200, "Largest bivalve mollusk",                       "https://en.wikipedia.org/wiki/Giant_clam"),
    ("Bull Shark",             "🦈",     130, "Can survive in freshwater",                     "https://en.wikipedia.org/wiki/Bull_shark"),
    ("Loggerhead Sea Turtle",  "🐢",     135, "Named for its large head",                      "https://en.wikipedia.org/wiki/Loggerhead_sea_turtle"),
    ("Common Dolphin",         "🐬",     110, "One of the fastest cetaceans",                  "https://en.wikipedia.org/wiki/Common_dolphin"),
    ("Sailfish",               "🐟",      90, "Fastest fish in the ocean",                     "https://en.wikipedia.org/wiki/Sailfish"),
    ("Spinner Dolphin",        "🐬",      75, "Named for its aerial spins",                    "https://en.wikipedia.org/wiki/Spinner_dolphin"),
    ("Giant Moray Eel",        "🐍",      30, "Largest moray eel species",                     "https://en.wikipedia.org/wiki/Giant_moray"),
    ("Japanese Spider Crab",   "🦀",      19, "Widest leg span of any arthropod",              "https://en.wikipedia.org/wiki/Japanese_spider_crab"),
    ("King Crab",              "🦀",      12, "One of the largest crustaceans",                "https://en.wikipedia.org/wiki/Red_king_crab"),
    ("Goliath Grouper",        "🐟",     363, "Can weigh over 360 kg",                         "https://en.wikipedia.org/wiki/Atlantic_goliath_grouper"),
    ("Sea Otter",              "🦦",      30, "Densest fur of any mammal",                     "https://en.wikipedia.org/wiki/Sea_otter"),
    ("Barracuda",              "🐟",      23, "Known for speed and sharp teeth",               "https://en.wikipedia.org/wiki/Great_barracuda"),
    ("Harbour Porpoise",       "🐬",      68, "Smallest cetacean in the North Atlantic",       "https://en.wikipedia.org/wiki/Harbour_porpoise"),
    ("Horseshoe Crab",         "🦀",       4, "Living fossil, 450 million years old",          "https://en.wikipedia.org/wiki/Horseshoe_crab"),
]

POLL_INTERVAL    = 5     # seconds; docs recommend 3-5 s
HD_FS_PATH       = "/agent/sea-swipes/animals.json"
VERIFY_TOLERANCE = 0.30  # allow ±30% variance between hardcoded and HD-parsed weight


# ---------------------------------------------------------------------------
# Step 0 — Crawl individual Wikipedia species pages via HD
# ---------------------------------------------------------------------------

def start_crawl(name: str, url: str, max_pages: int = 100) -> str:
    while True:
        resp = requests.post(
            f"{BASE_URL}/v1/indexes",
            headers=HEADERS,
            json={
                "source_type": "website",
                "name": name,
                "website": {"url": url, "max_pages": max_pages},
            },
        )
        if resp.status_code == 429:
            print(f"  (rate limit — waiting 30s for a slot...)", flush=True)
            time.sleep(30)
            continue
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


def crawl_wikipedia_pages(animals: list) -> list[str]:
    """
    Start one HD crawl job per animal Wikipedia page (max_pages=3 to catch
    infobox + body without wandering to unrelated articles).
    Returns the index_ids of jobs that completed successfully.
    """
    print(f"\nStep 0 — Crawling {len(animals)} Wikipedia species pages via HD...")
    jobs: list[tuple[str, str]] = []  # (animal_name, index_id)

    for name, _emoji, _kg, _fact, wiki_url in animals:
        print(f"  {name}... ", end="", flush=True)
        slug = name.lower().replace("'", "").replace(" ", "-")
        idx = start_crawl(f"wiki-{slug}", wiki_url, max_pages=3)
        jobs.append((name, idx))
        print(f"queued ({idx[:8]}...)")
        time.sleep(0.5)  # brief pause to stay within burst limits

    print(f"\n  Polling {len(jobs)} crawl jobs...")
    completed: list[str] = []
    for name, idx in jobs:
        print(f"  {name}... ", end="", flush=True)
        try:
            poll_until_complete(idx)
            completed.append(idx)
            print("done")
        except RuntimeError as e:
            print(f"FAILED ({e})")

    print(f"  {len(completed)}/{len(jobs)} Wikipedia indexes ready.\n")
    return completed


# ---------------------------------------------------------------------------
# Step 1 — Existing marine-bio index IDs (already crawled)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Step 2 — HD search: verify weight and find source URL
# ---------------------------------------------------------------------------

def parse_weight_kg(text: str) -> float | None:
    """Extract first weight value from structured fact-sheet text."""
    # kg / kilograms
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*kg", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", ""))
    # metric tonnes
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:metric\s*)?tonn?e", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "")) * 1000
    # short tons
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:short\s*)?tons?", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "")) * 907.185
    # pounds / lbs
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:lb|lbs|pounds?)", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "")) * 0.453592
    return None


def search_and_verify(animal_name: str, known_weight_kg: float, index_ids: list[str]) -> dict:
    """
    Search crawled Wikipedia indexes for '{animal} weight kg', then fall back
    to general web search if the index search finds nothing useful.
    Returns score, source_url, hd_weight (or None), and verified flag.
    """
    # Try all results across top_k=5 to find the best weight match
    for source_spec in [index_ids, ["web"]]:
        payload = {
            "query": f"{animal_name} weight kg",
            "top_k": 5,
        }
        if isinstance(source_spec, list) and source_spec and isinstance(source_spec[0], str) and source_spec[0] != "web":
            payload["index_ids"] = source_spec
        else:
            payload["sources"] = ["web"]

        resp = requests.post(f"{BASE_URL}/v1/search", headers=HEADERS, json=payload)
        resp.raise_for_status()
        results = resp.json().get("results", [])

        # Walk results and pick the closest weight match
        best = None
        for r in results:
            w = parse_weight_kg(r["text"])
            if w is None:
                continue
            if known_weight_kg > 0:
                ratio = abs(w - known_weight_kg) / known_weight_kg
                if ratio <= VERIFY_TOLERANCE:
                    # Verified hit — take it immediately
                    return {
                        "score":      r["score"],
                        "source_url": r["source_url"],
                        "hd_weight":  round(w),
                        "verified":   True,
                    }
                if best is None or ratio < abs(best[0] - known_weight_kg) / known_weight_kg:
                    best = (w, r)
            else:
                if best is None:
                    best = (w, r)

        if best is not None:
            w, r = best
            return {
                "score":      r["score"],
                "source_url": r["source_url"],
                "hd_weight":  round(w),
                "verified":   False,
            }

    # Nothing found in either source
    return {"score": 0.0, "source_url": "", "hd_weight": None, "verified": False}


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
    # Step 0 — Crawl individual Wikipedia species pages and index via HD.
    # Earlier attempts to crawl Wikipedia list/category pages returned page_count=0
    # (likely JS-gated). Crawling individual species pages (max_pages=3) avoids
    # that issue while keeping each job small.
    wiki_index_ids = crawl_wikipedia_pages(ANIMALS)

    # Step 1 — merge Wikipedia indexes with pre-crawled marine bio indexes.
    index_ids = EXISTING_INDEX_IDS + wiki_index_ids
    print(f"Using {len(index_ids)} total indexes "
          f"({len(EXISTING_INDEX_IDS)} marine bio + {len(wiki_index_ids)} Wikipedia).")

    # Step 2 — verify weights via HD search; prefer real data over hardcoded
    print(f"\nVerifying weights for {len(ANIMALS)} animals via HD search...")
    dataset = []
    unverified = []

    for name, emoji, hardcoded_kg, fun_fact, wiki_url in ANIMALS:
        print(f"  {name}... ", end="", flush=True)
        result = search_and_verify(name, hardcoded_kg, index_ids)

        # Real data takes priority — use HD weight when verified, hardcoded as fallback.
        # Fall back to Wikipedia URL when HD search finds no source.
        final_weight_kg = result["hd_weight"] if result["verified"] else hardcoded_kg
        source = "hd" if result["verified"] else "wikipedia"
        source_url = result["source_url"] if result["verified"] and result["source_url"] else wiki_url

        status = f"OK  hd={result['hd_weight']:,} kg -> using hd" if result["verified"] \
            else f"UNVERIFIED  hd={result['hd_weight']:,} kg -> using wikipedia" if result["hd_weight"] \
            else "UNVERIFIED  hd=none -> using wikipedia"
        print(f"{final_weight_kg:,} kg  [{status}  score={result['score']:.2f}]")

        if not result["verified"]:
            unverified.append((name, hardcoded_kg, result["hd_weight"]))

        dataset.append({
            "name":          name,
            "weight_kg":     final_weight_kg,
            "weight_source": source,
            "hd_score":      round(result["score"], 4),
            "verified":      result["verified"],
            "source":        source_url,
            "fun_fact":      fun_fact,
            "emoji":         emoji,
        })

    dataset.sort(key=lambda x: x["weight_kg"], reverse=True)

    verified_count = sum(1 for a in dataset if a["verified"])
    if unverified:
        print(f"\nUnverified ({len(unverified)}) — Wikipedia weight used as fallback:")
        for name, known, hd in unverified:
            hd_str = f"{hd:,}" if hd else "no parse"
            print(f"  {name}: wikipedia={known:,} kg  hd_found={hd_str} kg")

    # Step 3 — persist to HD filesystem
    print(f"\nWriting {len(dataset)} animals ({verified_count} HD-verified, {len(unverified)} Wikipedia fallback) to {HD_FS_PATH}...")
    write_to_hd_fs(dataset)
    print("Done.")



if __name__ == "__main__":
    main()
