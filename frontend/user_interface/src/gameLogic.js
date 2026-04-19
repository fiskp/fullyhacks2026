const HD_BASE    = "https://api.humandelta.ai";
const HD_FS_PATH = "/agent/sea-swipes/animals.json";

const QUEUE_MIN = 5;
const QUEUE_MAX = 10;

const _state = {
  animals:   [],
  used:      new Set(),
  winner:    null,   // animal holding the winning seat; carries across rounds
  pairQueue: [],
};

export async function initQueue() {
  const resp = await fetch(`${HD_BASE}/v1/fs`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${import.meta.env.VITE_HD_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ op: "read", path: HD_FS_PATH }),
  });
  if (!resp.ok) throw new Error(`HD FS read failed: ${resp.status}`);
  const { content } = await resp.json();
  _state.animals = JSON.parse(content);
  if (_state.animals.length < 2) throw new Error("Dataset too small");
  _refillQueue();
}

function _buildChallenger() {
  let pool = _state.animals.map((_, i) => i).filter(i => !_state.used.has(i));
  if (pool.length === 0) {
    _state.used.clear();
    if (_state.winner) {
      const idx = _state.animals.indexOf(_state.winner);
      if (idx !== -1) _state.used.add(idx);
    }
    pool = _state.animals.map((_, i) => i).filter(i => !_state.used.has(i));
  }
  const idx = pool[Math.floor(Math.random() * pool.length)];
  _state.used.add(idx);
  return _state.animals[idx];
}

function _refillQueue() {
  while (_state.pairQueue.length < QUEUE_MAX) {
    _state.pairQueue.push(_buildChallenger());
  }
}

export function getNextRound() {
  if (_state.pairQueue.length <= QUEUE_MIN) _refillQueue();

  let leftAnimal, rightAnimal;

  if (_state.winner === null) {
    // First round: pop two animals, place heavier on the left
    const a = _state.pairQueue.shift();
    const b = _state.pairQueue.shift();
    leftAnimal  = a.weight_kg >= b.weight_kg ? a : b;
    rightAnimal = a.weight_kg >= b.weight_kg ? b : a;
  } else {
    // Subsequent rounds: winner stays on the left, new challenger on the right
    leftAnimal  = _state.winner;
    rightAnimal = _state.pairQueue.shift();
  }

  const correct = leftAnimal.weight_kg >= rightAnimal.weight_kg ? "left" : "right";

  // Advance the winner seat for the next round
  _state.winner = correct === "left" ? leftAnimal : rightAnimal;

  return {
    left:   { name: leftAnimal.name,  stat: Math.round(leftAnimal.weight_kg).toLocaleString(),  emoji: leftAnimal.emoji  },
    right:  { name: rightAnimal.name, stat: Math.round(rightAnimal.weight_kg).toLocaleString(), emoji: rightAnimal.emoji },
    prompt: "Which is heavier? (kg)",
    correct,
  };
}
