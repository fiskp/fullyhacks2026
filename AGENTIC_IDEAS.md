# Agentic Enhancement Ideas — SEA SWIPE

AI integration points using Google Gemini API. Key to be added to `.env` as `GEMINI_API_KEY`.

---

## 1. Gemini-Powered Challenger Selection  ★ Highest impact

**Where:** `game.js` — inside `refillQueue()`  
**What:** Instead of picking challengers randomly from the pool, send Gemini the current winner and recent round history and ask it to pick a strategically interesting next animal — e.g. one with a surprisingly close or dramatically different weight.  
**Why it's agentic:** The queue becomes context-aware. Gemini can create tension (pick an animal that might dethrone a long-running winner) or vary the difficulty dynamically.

```js
// Rough shape of the Gemini call inside refillQueue():
// POST https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent
// Prompt: "Current winner: Blue Whale (150,000 kg). Recent animals: [...].
//          From this list: [...], pick the next challenger that would make
//          the most interesting comparison. Return only the animal name."
```

---

## 2. Adaptive Difficulty

**Where:** `game.js` — fed into the same Gemini call as #1, or a separate call after `resolveRound()`  
**What:** Pass the score gap between players to Gemini. If one player is dominating, bias challenger selection toward animals with weights very close to the current winner (harder to guess). If scores are tight, pick animals with more obvious weight differences.  
**Why it's agentic:** The game self-balances without hardcoded rules.

---

## 3. Live Fun Fact Generation

**Where:** `game.js` — called inside `resolveRound()` after scores are updated, during the 2.5s reveal window  
**What:** Stream a Gemini-generated fun fact or "did you know" blurb about whichever animal just won. Replaces the static `fun_fact` string from the dataset.  
**Why it's agentic:** Every reveal feels fresh; Gemini can reference the matchup context ("A walrus outweighs a grand piano — but a great white shark would still outswim it.").

```js
// Fire-and-forget during the reveal phase — result renders if it arrives before next round
async function fetchFunFact(winner, challenger) { ... }
```

---

## 4. Dynamic Animal Discovery

**Where:** `scripts/build_dataset.py` — replace or augment the hardcoded `ANIMALS` list  
**What:** Ask Gemini to generate a list of marine animals given a theme or constraint (e.g. "give me 20 lesser-known deep-sea animals with verifiable weights"). Feed that list into the existing HD search pipeline instead of (or alongside) the hardcoded 60.  
**Why it's agentic:** The dataset can grow and diversify without manual curation.

---

## 5. Post-Game Summary / Roast

**Where:** `game.js` — triggered on `"gameover"` phase  
**What:** Send both players' full round history to Gemini and generate a short, funny post-game summary — who guessed correctly most, which animal was the most surprising, etc.  
**Why it's agentic:** Adds a shareable, narrative ending to each game that feels personalized.

---

## Setup (when key is ready)

Add to `.env`:
```
GEMINI_API_KEY=your_key_here
```

For `game.js` (browser), inject similarly to `HD_API_KEY`:
```html
<script>window.GEMINI_API_KEY = "your_key_here";</script>
```

Gemini base URL: `https://generativelanguage.googleapis.com/v1beta`  
Recommended model: `gemini-2.0-flash` (fast, low latency — good for in-round calls)
