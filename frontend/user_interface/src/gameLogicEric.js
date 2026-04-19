const HD_BASE    = "/hd";
const HD_FS_PATH = "/agent/sea-swipes/eric_questions.json";

const _state = {
  items:      [],
  pool:       [],
  winner:     null,
  challenger: null,
  scores:     [0, 0],
};

async function _fetchItems() {
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
  _state.pool = _shuffled(_state.items).filter(a => a !== _state.winner);
}

export async function initEricQueue() {
  _state.scores     = [0, 0];
  _state.winner     = null;
  _state.challenger = null;

  const items = await _fetchItems();
  if (!items || items.length < 2) throw new Error("Failed to load Eric Ly questions");

  _state.items = items;
  _state.pool  = _shuffled(items);

  const a = _state.pool.shift();
  const b = _state.pool.shift();
  if (a.value >= b.value) {
    _state.winner = a;
    _state.pool.unshift(b);
  } else {
    _state.winner = b;
    _state.pool.unshift(a);
  }
}

export function setEricScores(p1, p2) {
  _state.scores = [p1, p2];
}

export function advanceEricWinner(correct) {
  if (correct === "right") _state.winner = _state.challenger;
}

export function getNextEricRound() {
  if (_state.pool.length === 0) _refillPool();

  _state.challenger = _state.pool.shift();

  const w = _state.winner;
  const c = _state.challenger;

  return {
    left:    { name: w.name, stat: w.display,  emoji: w.emoji, fun_fact: w.fun_fact },
    right:   { name: c.name, stat: c.display,  emoji: c.emoji, fun_fact: c.fun_fact },
    prompt:  "Which number is bigger?",
    correct: w.value >= c.value ? "left" : "right",
  };
}
