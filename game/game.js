// SEA SLIDES — game logic: round management, scoring, input handling, win conditions

const HD_BASE = "https://api.humandelta.ai";
const HD_FS_PATH = "/agent/depth-charge/animals.json";

// HD_API_KEY must be set before game loads — inject via a <script> tag in index.html:
//   <script>window.HD_API_KEY = "hd_live_...";</script>
// Never commit a real key; load it from an env var or a local config file that's gitignored.

async function fetchAnimals() {
  const resp = await fetch(`${HD_BASE}/v1/fs`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${window.HD_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ op: "read", path: HD_FS_PATH }),
  });
  if (!resp.ok) throw new Error(`HD FS read failed: ${resp.status}`);
  const { content } = await resp.json();
  return JSON.parse(content);
}

// ---------------------------------------------------------------------------
// Game state
// ---------------------------------------------------------------------------

const state = {
  animals: [],       // full dataset from HD FS
  used: new Set(),   // indices already shown this game
  scores: [0, 0],   // [player1, player2]
  round: null,       // { left: animal, right: animal, answer: "left"|"right"|"tie" }
  phase: "loading",  // loading | ready | reveal | gameover
};

const WIN_SCORE = 10;

// ---------------------------------------------------------------------------
// Round logic
// ---------------------------------------------------------------------------

function pickRound() {
  const pool = state.animals
    .map((a, i) => i)
    .filter(i => !state.used.has(i));

  if (pool.length < 2) {
    // Ran out of animals — reset used set
    state.used.clear();
    return pickRound();
  }

  const [iA, iB] = pool.sort(() => Math.random() - 0.5).slice(0, 2);
  state.used.add(iA);
  state.used.add(iB);

  const left = state.animals[iA];
  const right = state.animals[iB];
  const answer =
    left.weight_kg > right.weight_kg ? "left" :
    right.weight_kg > left.weight_kg ? "right" : "tie";

  state.round = { left, right, answer };
}

// ---------------------------------------------------------------------------
// Input handling — P1: A (left) / Z (right)  |  P2: ← (left) / → (right)
// ---------------------------------------------------------------------------

const KEYS = {
  KeyA:        { player: 0, guess: "left" },
  KeyZ:        { player: 0, guess: "right" },
  ArrowLeft:   { player: 1, guess: "left" },
  ArrowRight:  { player: 1, guess: "right" },
};

document.addEventListener("keydown", (e) => {
  if (state.phase !== "ready") return;
  const binding = KEYS[e.code];
  if (!binding) return;

  const { player, guess } = binding;
  const correct = guess === state.round.answer;

  if (correct) {
    state.scores[player]++;
    if (state.scores[player] >= WIN_SCORE) {
      state.phase = "gameover";
      render();
      return;
    }
  }

  state.phase = "reveal";
  render({ lastPlayer: player, lastGuess: guess, correct });

  setTimeout(() => {
    pickRound();
    state.phase = "ready";
    render();
  }, 2500);
});

// ---------------------------------------------------------------------------
// Render (placeholder — real DOM wiring goes here once index.html is built)
// ---------------------------------------------------------------------------

function render(meta = {}) {
  // TODO: update DOM elements based on state and meta
  console.log("render", state.phase, state.scores, meta);
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

async function init() {
  render(); // show loading state
  try {
    state.animals = await fetchAnimals();
    if (state.animals.length < 2) throw new Error("Dataset too small");
    pickRound();
    state.phase = "ready";
    render();
  } catch (err) {
    console.error("Failed to load animals:", err);
    // TODO: show error UI
  }
}

init();
