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

const ROUND_MS  = 15_000;
const WIN_SCORE = 500;

const state = {
  animals: [],          // full dataset from HD FS
  used: new Set(),      // indices already shown this game
  scores: [0, 0],       // [player1, player2]
  round: null,          // { left: animal, right: animal, answer: "left"|"right"|"tie" }
  guesses: [null, null],// current live guess per player; swappable until timer fires
  timerStart: null,     // Date.now() when the round began
  timerHandle: null,    // setTimeout handle for auto-resolve
  phase: "loading",     // loading | ready | reveal | gameover
};

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

// 100 pts per round — shared 50/50 if both right, winner-take-all if only one right, 0 if neither.
function resolveRound() {
  clearTimeout(state.timerHandle);
  state.timerHandle = null;

  const { answer } = state.round;
  const [g0, g1] = state.guesses;
  const p0correct = g0 === answer;
  const p1correct = g1 === answer;

  let awarded = [0, 0];
  if (p0correct && p1correct) {
    awarded = [50, 50];
  } else if (p0correct) {
    awarded = [100, 0];
  } else if (p1correct) {
    awarded = [0, 100];
  }

  state.scores[0] += awarded[0];
  state.scores[1] += awarded[1];

  const winner =
    state.scores[0] >= WIN_SCORE ? 0 :
    state.scores[1] >= WIN_SCORE ? 1 : null;

  if (winner !== null) {
    state.phase = "gameover";
    render({ awarded, winner });
    return;
  }

  state.phase = "reveal";
  render({ awarded });

  setTimeout(() => {
    startRound();
  }, 2500);
}

// ---------------------------------------------------------------------------
// Round lifecycle
// ---------------------------------------------------------------------------

function pickRound() {
  const pool = state.animals
    .map((_, i) => i)
    .filter(i => !state.used.has(i));

  if (pool.length < 2) {
    state.used.clear();
    return pickRound();
  }

  const shuffled = pool.sort(() => Math.random() - 0.5);
  const [iA, iB] = shuffled;
  state.used.add(iA);
  state.used.add(iB);

  const left  = state.animals[iA];
  const right = state.animals[iB];
  const answer =
    left.weight_kg > right.weight_kg  ? "left"  :
    right.weight_kg > left.weight_kg  ? "right" : "tie";

  state.round = { left, right, answer };
}

function startRound() {
  pickRound();
  state.guesses = [null, null];
  state.timerStart = Date.now();
  state.phase = "ready";
  state.timerHandle = setTimeout(resolveRound, ROUND_MS);
  render();
}

// ---------------------------------------------------------------------------
// Input — P1: A (left) / Z (right)   |   P2: ← (left) / → (right)
// Players may change their guess freely until the timer fires.
// ---------------------------------------------------------------------------

const KEYS = {
  KeyA:        { player: 0, guess: "left"  },
  KeyZ:        { player: 0, guess: "right" },
  ArrowLeft:   { player: 1, guess: "left"  },
  ArrowRight:  { player: 1, guess: "right" },
};

document.addEventListener("keydown", (e) => {
  if (state.phase !== "ready") return;
  const binding = KEYS[e.code];
  if (!binding) return;

  const { player, guess } = binding;
  state.guesses[player] = guess;
  render();
});

// ---------------------------------------------------------------------------
// Render (placeholder — real DOM wiring goes here once index.html is built)
// ---------------------------------------------------------------------------

function render(meta = {}) {
  const elapsed  = state.timerStart ? Date.now() - state.timerStart : 0;
  const remaining = Math.max(0, ROUND_MS - elapsed);
  // TODO: update DOM elements based on state, meta, and remaining ms
  console.log("render", state.phase, state.scores, state.guesses, `${(remaining / 1000).toFixed(1)}s`, meta);
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

async function init() {
  render();
  try {
    state.animals = await fetchAnimals();
    if (state.animals.length < 2) throw new Error("Dataset too small");
    startRound();
  } catch (err) {
    console.error("Failed to load animals:", err);
    // TODO: show error UI
  }
}

init();
