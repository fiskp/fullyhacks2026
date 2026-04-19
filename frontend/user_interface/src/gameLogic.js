import { rounds as fallbackRounds } from "./mock_data/rounds";

const HD_BASE    = "/hd";
const HD_FS_PATH = "/agent/sea-swipes/animals.json";

const _state = {
  mode:       "hd",   // "hd" | "fallback"
  animals:    [],     // full HD dataset
  pool:       [],     // remaining challengers (HD) or rounds (fallback)
  winner:     null,   // current winning animal (HD mode)
  challenger: null,   // challenger shown in the active round (HD mode)
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

export async function initQueue() {
  _state.scores     = [0, 0];
  _state.winner     = null;
  _state.challenger = null;

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
}

export function setScores(p1, p2) {
  _state.scores = [p1, p2];
}

// Call with the round's correct value before getNextRound() to advance the winner seat.
// In HD mode, winner is always displayed on the left.
export function advanceWinner(correct) {
  if (_state.mode !== "hd") return;
  if (correct === "right") _state.winner = _state.challenger;
}

export function getNextRound() {
  if (_state.mode === "fallback") {
    if (_state.pool.length === 0) _state.pool = _shuffled(fallbackRounds);
    return _state.pool.shift() ?? fallbackRounds[0];
  }

  if (_state.pool.length === 0) _refillPool();

  _state.challenger = _state.pool.shift();
  const w = _state.winner;
  const c = _state.challenger;

  return {
    left:    { name: w.name, stat: w.weight_kg },
    right:   { name: c.name, stat: c.weight_kg },
    prompt:  "Which one is heavier? (kg)",
    correct: w.weight_kg >= c.weight_kg ? "left" : "right",
  };
}
