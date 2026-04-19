import { rounds as fallbackRounds } from "./mock_data/rounds";
import { geminiPickAnimal, geminiPickRound } from "./geminiSelector";

const HD_BASE    = "/hd";
const HD_FS_PATH = "/agent/sea-swipes/animals.json";

const _state = {
  mode:       "hd",   // "hd" | "fallback"
  animals:    [],
  pool:       [],
  winner:     null,
  challenger: null,
  recent:     [],     // last 5 challengers for Gemini context
  scores:     [0, 0],
};

async function _fetchAnimals() {
  const key = import.meta.env.VITE_HD_API_KEY;
  if (!key) return null;
  try {
    const resp = await fetch(`${HD_BASE}/v1/fs`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${key}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ op: "read", path: HD_FS_PATH }),
    });
    if (!resp.ok) return null;
    const { content } = await resp.json();
    const json = content.replace(/^<!--[\s\S]*?-->\s*/, "");
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function _shuffled(arr) {
  return [...arr].sort(() => Math.random() - 0.5);
}

function _refillPool() {
  _state.pool = _shuffled(_state.animals).filter(a => a !== _state.winner);
}

// Fire-and-forget: ask Gemini to swap pool[0] with its strategic pick.
// Players have ~12 s (10s round + 2s reveal) before getNextRound() runs again,
// giving Gemini ample time to respond before it matters.
function _prefetchNextChallenger() {
  if (_state.pool.length === 0) return;
  const snapshot = [..._state.pool];
  geminiPickAnimal(snapshot, _state.winner, _state.recent, _state.scores)
    .then(idx => {
      if (idx !== null && idx < _state.pool.length) {
        [_state.pool[0], _state.pool[idx]] = [_state.pool[idx], _state.pool[0]];
      }
    })
    .catch(console.warn);
}

export async function initQueue() {
  _state.scores     = [0, 0];
  _state.winner     = null;
  _state.challenger = null;
  _state.recent     = [];

  const animals = await _fetchAnimals();

  if (!animals || animals.length < 2) {
    _state.mode = "fallback";
    _state.pool = _shuffled(fallbackRounds);
    return;
  }

  _state.mode    = "hd";
  _state.animals = animals;
  _state.pool    = _shuffled(animals);

  // Bootstrap: pop two, heavier holds the winner seat, lighter leads the pool
  const a = _state.pool.shift();
  const b = _state.pool.shift();
  if (a.weight_kg >= b.weight_kg) {
    _state.winner = a;
    _state.pool.unshift(b);
  } else {
    _state.winner = b;
    _state.pool.unshift(a);
  }

  // Pre-fetch Gemini's pick for the very first challenger
  _prefetchNextChallenger();
}

export function setScores(p1, p2) {
  _state.scores = [p1, p2];
}

// Called from App.jsx after reveal, before getNextRound(), to advance the winner seat.
export function advanceWinner(correct) {
  if (_state.mode !== "hd") return;
  if (correct === "right") _state.winner = _state.challenger;
}

export function getNextRound() {
  // ── Fallback (mock) mode ──────────────────────────────────────────────────
  if (_state.mode === "fallback") {
    if (_state.pool.length === 0) {
      const pool = _shuffled(fallbackRounds);
      geminiPickRound(pool, _state.scores)
        .then(idx => {
          if (idx !== null) {
            const [picked] = pool.splice(idx, 1);
            _state.pool = [picked, ...pool];
          } else {
            _state.pool = pool;
          }
        })
        .catch(() => { _state.pool = _shuffled(fallbackRounds); });
      _state.pool = _shuffled(fallbackRounds); // immediate fallback while Gemini responds
    }
    return _state.pool.shift() ?? fallbackRounds[0];
  }

  // ── HD mode ───────────────────────────────────────────────────────────────
  if (_state.pool.length === 0) _refillPool();

  _state.challenger = _state.pool.shift();

  _state.recent.push(_state.challenger);
  if (_state.recent.length > 5) _state.recent.shift();

  const w = _state.winner;
  const c = _state.challenger;

  // Pre-fetch Gemini's pick for the round after this one
  _prefetchNextChallenger();

  return {
    left:   { name: w.name, stat: Math.round(w.weight_kg).toLocaleString(), emoji: w.emoji },
    right:  { name: c.name, stat: Math.round(c.weight_kg).toLocaleString(), emoji: c.emoji },
    prompt: "Which one is heavier? (kg)",
    correct: w.weight_kg >= c.weight_kg ? "left" : "right",
  };
}
