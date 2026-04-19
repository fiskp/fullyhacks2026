# Plan: Custom Topic Generation

## Context
The game (Sea Swipe / Sea Swipe) currently has a category input on the home page that passes the value via nav state, but it's ignored — the game always loads hardcoded marine animals from HD FS and only ever asks weight comparisons. The goal is to make the topic input actually drive the game: Gemini generates items + comparison attributes for any topic, HD crawls Wikipedia to verify numeric values, and the game plays with multi-attribute questions (heavier, faster, older, more teeth, etc.).

---

## Architecture Overview

**Zero-backend preserved** — all orchestration stays client-side, HD proxy through Vite, Gemini direct fetch.

**Two-phase loading (shown to user on Home page):**
1. **Gemini phase (~3s):** Generate item list + comparison attributes + initial value estimates for every item
2. **HD phase (~20–30s):** Crawl Wikipedia per item in parallel, search HD for each item × attribute, overwrite Gemini estimates with verified values; cache result in HD FS

**Fallback chain:** HD fails → use Gemini estimates → HD unavailable entirely → existing marine-animal flow

---

## Data Structures

**Topic Plan (from Gemini):**
```js
{
  topic: "animals",
  items: [{ name: "Lion", emoji: "🦁", wikipedia_slug: "Lion" }, ...],  // 10–15 items
  attributes: [
    { key: "weight_kg", unit: "kg", prompt: "Which one is heavier? (kg)", search_query: "{name} weight in kilograms" },
    { key: "lifespan_years", unit: "years", prompt: "Which one lives longer? (years)", search_query: "{name} lifespan years" },
    { key: "teeth_count", unit: "", prompt: "Which one has more teeth?", search_query: "{name} number of teeth" }
  ],
  values: {
    "Lion": { weight_kg: 190, lifespan_years: 16, teeth_count: 30 },
    ...
  }
}
```

**Final Dataset (HD-enriched, written to HD FS cache):**
```js
{
  topic: "animals",
  slug: "animals",
  items: [
    { name: "Lion", emoji: "🦁", weight_kg: 190, lifespan_years: 16, teeth_count: 30 },
    ...
  ],
  attributes: [ /* same as above */ ]
}
```

**Round (unchanged interface, attribute rotates each round):**
```js
{ left: { name, stat, emoji }, right: { name, stat, emoji }, prompt, correct: "left"|"right" }
```

---

## Files to Create

### 1. `src/topicGenerator.js` (new)
Single Gemini call. Prompt asks for JSON with `items`, `attributes`, and `values`. Parse response text as JSON (strip any markdown fences). Return the object or `null` on failure.

```js
export async function generateTopicPlan(topic)
// → { topic, items, attributes, values } | null
```

### 2. `src/datasetBuilder.js` (new)
Orchestrates HD crawl + search + cache.

```js
export async function buildDataset(plan, onProgress)
// onProgress(step: string, pct: number)
// Steps: "Checking cache…", "Crawling pages…", "Fetching stats…", "Done"
// → { topic, slug, items, attributes }

// Internal helpers (not exported):
async function _checkCache(slug)          // HD FS read at /agent/sea-swipes/topics/{slug}.json
async function _writeCache(slug, dataset) // HD FS write
async function _crawlAll(items)           // POST /v1/indexes per item in parallel, poll until done or 30s timeout
async function _searchAll(items, attributes, indexIds) // POST /v1/search per item×attribute in parallel
function _parseValue(snippets)            // regex to extract first number from search results
function _mergeValues(plan, hdValues)     // overwrite plan.values with HD-found values, keep Gemini estimate for misses
```

---

## Files to Modify

### 3. `src/gameLogic.js`
- Add `attributes` to `_state`
- Change `initQueue` signature: `initQueue(dataset?)` — if `dataset` is provided, skip HD FS fetch and load items + attributes from it
- Backward compat: `initQueue()` with no arg still does existing marine-animal HD FS fetch (weight-only)
- `getNextRound()` in custom-topic mode: picks a random attribute from `_state.attributes`, uses that attribute's key for stat display and correct-answer determination
- Keep existing HD mode (weight_kg) unchanged for the no-arg fallback path

Key change in `getNextRound()` for custom-topic mode:
```js
const attr = _state.attributes[Math.floor(Math.random() * _state.attributes.length)];
const wVal = w[attr.key];
const cVal = c[attr.key];
return {
  left:  { name: w.name, stat: wVal?.toLocaleString() ?? "?", emoji: w.emoji },
  right: { name: c.name, stat: cVal?.toLocaleString() ?? "?", emoji: c.emoji },
  prompt: attr.prompt,
  correct: (wVal ?? 0) >= (cVal ?? 0) ? "left" : "right",
};
```

`geminiPickAnimal` already works with generic objects; update its prompt to use the first attribute's key+unit instead of hardcoded `weight_kg`.

### 4. `src/pages/Home/Home.jsx`
- Add state: `loading: false`, `loadingStep: ""`
- On submit: set `loading = true`, call `generateTopicPlan(category)`, then `buildDataset(plan, onProgress)`, then `navigate("/game", { state: { dataset } })`
- Show loading overlay while `loading` is true with step text + spinner
- If `generateTopicPlan` returns null (Gemini failed): navigate with `{ category }` only → falls back to existing marine flow in App

### 5. `src/App.jsx`
- Add `useLocation` import from react-router-dom
- Read `const { dataset } = useLocation().state ?? {}`
- Change `initQueue()` call to `initQueue(dataset ?? null)`
- No other changes needed

---

## Gemini Prompt Template (for `topicGenerator.js`)

```
You are generating a comparison quiz about: "{topic}".

Return ONLY valid JSON (no markdown, no explanation) in this exact shape:
{
  "items": [{"name": "...", "emoji": "...", "wikipedia_slug": "..."}],  // 12 items
  "attributes": [
    {"key": "snake_case_key", "unit": "unit or empty string", "prompt": "Which one has more/is bigger X? (unit)", "search_query": "{name} X in unit"}
  ],  // 3–5 measurable numeric attributes
  "values": {
    "ItemName": {"key1": number, "key2": number, ...},
    ...
  }
}

Rules:
- Items must be specific and well-known, not vague categories.
- Attributes must be numeric and objectively measurable (no subjective traits).
- Values are your best estimates; they will be verified. Use realistic numbers.
- The "search_query" must contain the literal string {name} as a placeholder.
```

---

## HD Cache Path
- Per-topic: `/agent/sea-swipes/topics/{slugify(topic)}.json`
  (slugify: lowercase, spaces→hyphens, strip special chars)
- Existing marine path `/agent/sea-swipes/animals.json` unchanged

---

## Loading UX (Home.jsx)
```
[Step 1/3] Planning your topic...     (Gemini call)
[Step 2/3] Crawling Wikipedia...      (HD crawl jobs)
[Step 3/3] Fetching stats...          (HD searches)
           Ready!
```
Max wait: 35s. If HD hasn't finished by then, proceed with Gemini-only values and skip the cache write.

---

## Verification

1. `npm run dev` in `frontend/user_interface/`
2. Type "dogs" on home page → loading overlay should progress through 3 steps (~5–35s)
3. Game starts with dog breeds as items, questions vary per round (heavier, lives longer, more teeth, etc.)
4. Correct answer should reflect the actual attribute comparison
5. Type "planets" → same flow, different items and attributes (diameter, moons, distance, etc.)
6. Clear input → submit → game falls back to marine animals (backward compat)
7. Kill network mid-load → game still starts with Gemini-estimated values

---

## Critical File Paths
- `frontend/user_interface/src/gameLogic.js` — core logic change
- `frontend/user_interface/src/geminiSelector.js` — minor generalization
- `frontend/user_interface/src/pages/Home/Home.jsx` — loading UX
- `frontend/user_interface/src/App.jsx` — wire dataset from nav state
- `frontend/user_interface/src/topicGenerator.js` — **new**
- `frontend/user_interface/src/datasetBuilder.js` — **new**
- `frontend/user_interface/vite.config.js` — confirm `/hd` proxy is in place (no change needed)
