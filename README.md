# SEA SWIPE

A 2-player local party game where players compete to guess which marine animal weighs more. Runs entirely on one machine with a shared screen.

## Architecture

The animal dataset lives in the **Human Delta virtual filesystem** at `/agent/sea-swipes/animals.json`. `build_dataset.py` writes it there once; the game reads it at runtime via the HD FS API — no local JSON file is bundled.

```
/data/                   — unused; dataset is stored in HD FS, not locally
/scripts/
  build_dataset.py       — one-time pipeline: crawl → search weights → write to HD FS
/game/
  index.html             — single-page game UI (open directly in browser, no build step)
  style.css              — ocean theme, player panels, card flip animations
  game.js                — fetches animals from HD FS at startup; all game logic runs client-side
/vision/
  gesture.py             — optional webcam gesture recognition (buzz in without keyboard)
```

## File Details

### `scripts/build_dataset.py`
Runs once before the hackathon demo. Three steps:
1. POSTs crawl jobs to `POST /v1/indexes` for three seed marine-biology URLs.
2. Polls `GET /v1/indexes/{id}` every 5 s until each job reaches `status: "completed"`.
3. For each of 60 hardcoded animal names, calls `POST /v1/search` for weight data,
   filters results below a 0.85 cosine-similarity threshold, parses the weight value,
   then writes the curated array to `POST /v1/fs { op: "write", path: "/agent/sea-swipes/animals.json" }`.

### `game/game.js`
On page load, calls `POST /v1/fs { op: "read", path: "/agent/sea-swipes/animals.json" }` to
fetch the dataset. After that all game logic (round selection, scoring, win detection) runs
entirely client-side with no further API calls.

Controls: P1 = `A` (left) / `Z` (right) | P2 = `←` / `→`

### `vision/gesture.py`
Optional. Maps hand gestures via webcam to keypresses so players can buzz in
without touching the keyboard. Requires `mediapipe` and `opencv-python`.

## Quick Start

**First time (or to refresh the dataset):**
```bash
export HD_API_KEY=hd_live_...
pip install requests
python scripts/build_dataset.py
```

**Playing:**
1. Set `window.HD_API_KEY` in `game/index.html` (see comment in `game.js`).
2. Open `game/index.html` in a browser.
3. First to 10 correct guesses wins.

> **Never commit your API key.** Add a gitignored `game/config.js` that sets
> `window.HD_API_KEY` and load it with a `<script>` tag before `game.js`.
