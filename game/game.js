// SEA SWIPE — game logic: round management, scoring, input handling, win conditions

const HD_BASE   = "https://api.humandelta.ai";
const HD_FS_PATH = "/agent/sea-swipes/animals.json";

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
const WIN_SCORE = 1000;
const QUEUE_MIN = 5;
const QUEUE_MAX = 10;

const state = {
  animals:    [],           // full dataset from HD FS
  used:       new Set(),    // animal indices already shown this game
  scores:     [0, 0],       // [player1, player2]
  winner:     null,         // animal holding the winning seat (carries across rounds)
  challenger: null,         // new animal introduced this round
  round:      null,         // { winner, challenger, answer: "winner"|"challenger"|"tie" }
  guesses:    [null, null], // live guess per player; swappable until timer fires
  pairQueue:  [],           // pre-loaded challengers (individual animals)
  timerStart: null,
  timerHandle: null,
  phase: "loading",         // loading | ready | reveal | gameover
};

// ---------------------------------------------------------------------------
// Queue management
// ---------------------------------------------------------------------------

function buildChallenger() {
  let pool = state.animals
    .map((_, i) => i)
    .filter(i => !state.used.has(i));

  if (pool.length === 0) {
    // All animals shown — reset used but keep current winner out of the pool
    state.used.clear();
    if (state.winner) {
      const winnerIdx = state.animals.indexOf(state.winner);
      if (winnerIdx !== -1) state.used.add(winnerIdx);
    }
    pool = state.animals
      .map((_, i) => i)
      .filter(i => !state.used.has(i));
  }

  const idx = pool[Math.floor(Math.random() * pool.length)];
  state.used.add(idx);
  return state.animals[idx];
}

function refillQueue() {
  while (state.pairQueue.length < QUEUE_MAX) {
    state.pairQueue.push(buildChallenger());
  }
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

// 100 pts/round — shared 50/50 if both right, winner-take-all if one right, 0 if neither.
function resolveRound() {
  clearTimeout(state.timerHandle);
  state.timerHandle = null;

  const { answer } = state.round;
  const [g0, g1]   = state.guesses;
  const p0correct  = g0 === answer;
  const p1correct  = g1 === answer;

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

  // Advance the winner seat: challenger takes over if it was heavier (or a tie)
  state.winner = answer === "challenger" || answer === "tie"
    ? state.challenger
    : state.winner;

  const gameWinner =
    state.scores[0] >= WIN_SCORE ? 0 :
    state.scores[1] >= WIN_SCORE ? 1 : null;

  if (gameWinner !== null) {
    state.phase = "gameover";
    render({ awarded, gameWinner });
    return;
  }

  state.phase = "reveal";
  render({ awarded });

  if (state.pairQueue.length <= QUEUE_MIN) refillQueue();

  setTimeout(startRound, 2500);
}

// ---------------------------------------------------------------------------
// Round lifecycle
// ---------------------------------------------------------------------------

function startRound() {
  // Bootstrap: first round has no winner yet — pop two animals and pick the heavier as winner.
  if (state.winner === null) {
    const a = state.pairQueue.shift();
    const b = state.pairQueue.shift();
    state.winner     = a.weight_kg >= b.weight_kg ? a : b;
    state.challenger = a.weight_kg >= b.weight_kg ? b : a;
  } else {
    state.challenger = state.pairQueue.shift();
  }

  const answer =
    state.winner.weight_kg > state.challenger.weight_kg ? "winner"     :
    state.challenger.weight_kg > state.winner.weight_kg ? "challenger" : "tie";

  state.round      = { winner: state.winner, challenger: state.challenger, answer };
  state.guesses    = [null, null];
  state.timerStart = Date.now();
  state.phase      = "ready";
  state.timerHandle = setTimeout(resolveRound, ROUND_MS);
  render();
}

// ---------------------------------------------------------------------------
// Input — P1: A (winner) / Z (challenger)   |   P2: ← (winner) / → (challenger)
// Winner is always displayed on the left; challenger on the right.
// Players may change their guess freely until the 15s timer fires.
// ---------------------------------------------------------------------------

const KEYS = {
  KeyA:        { player: 0, guess: "winner"     },
  KeyZ:        { player: 0, guess: "challenger" },
  ArrowLeft:   { player: 1, guess: "winner"     },
  ArrowRight:  { player: 1, guess: "challenger" },
};

document.addEventListener("keydown", (e) => {
  if (state.phase !== "ready") return;
  const binding = KEYS[e.code];
  if (!binding) return;
  state.guesses[binding.player] = binding.guess;
  render();
});

// ---------------------------------------------------------------------------
// Render (placeholder — real DOM wiring goes here once index.html is built)
// ---------------------------------------------------------------------------

function render(meta = {}) {
  const elapsed   = state.timerStart ? Date.now() - state.timerStart : 0;
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
    refillQueue();   // pre-fill to QUEUE_MAX before first round
    startRound();
  } catch (err) {
    console.error("Failed to load animals:", err);
    // TODO: show error UI
  }
}

init();
