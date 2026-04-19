const HD_BASE    = "https://api.humandelta.ai";
const HD_FS_PATH = "/agent/sea-swipes/animals.json";

const GEMINI_BASE  = "https://generativelanguage.googleapis.com/v1beta";
const GEMINI_MODEL = "gemini-2.0-flash";

const QUEUE_MIN = 5;
const QUEUE_MAX = 10;

const _state = {
  animals:   [],
  used:      new Set(),
  winner:    null,   // animal holding the winning seat; carries across rounds
  pairQueue: [],
  recent:    [],     // last 5 challengers shown (Gemini context)
  scores:    [0, 0], // synced from App.jsx for adaptive difficulty
};

export function setScores(p1, p2) {
  _state.scores = [p1, p2];
}

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
  // HD FS prepends an HTML comment header — skip to the first JSON character
  const jsonStart = content.indexOf("[");
  _state.animals = JSON.parse(jsonStart === -1 ? content : content.slice(jsonStart));
  if (_state.animals.length < 2) throw new Error("Dataset too small");
  await _refillQueue();
}

function _buildChallengerRandom() {
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

async function _geminiPickChallenger(pool) {
  const key = import.meta.env.VITE_GEMINI_API_KEY;
  if (!key) return null;

  const available = pool.map(i => `${_state.animals[i].name} (${_state.animals[i].weight_kg} kg)`);
  const gap = _state.scores[0] - _state.scores[1];
  const difficultyHint = Math.abs(gap) > 3
    ? "The game is unbalanced — pick an animal with weight very close to the current winner to make guessing harder."
    : "Scores are close — pick a dramatic weight contrast to keep the energy high.";

  const prompt = [
    `Current winner: ${_state.winner ? `${_state.winner.name} (${_state.winner.weight_kg} kg)` : "none"}.`,
    `Recent challengers: ${_state.recent.slice(-3).map(a => a.name).join(", ") || "none"}.`,
    difficultyHint,
    `Available animals: ${available.join(", ")}.`,
    "Reply with only the animal name, exactly as written above. No punctuation, no explanation.",
  ].join("\n");

  try {
    const resp = await fetch(
      `${GEMINI_BASE}/models/${GEMINI_MODEL}:generateContent?key=${key}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      }
    );
    if (!resp.ok) return null;
    const data = await resp.json();
    const name = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
    const match = pool.find(i => _state.animals[i].name === name);
    return match ?? null;
  } catch {
    return null;
  }
}

async function _refillQueue() {
  // Fill to QUEUE_MAX with random picks first (fast, synchronous)
  while (_state.pairQueue.length < QUEUE_MAX) {
    _state.pairQueue.push(_buildChallengerRandom());
  }

  // Ask Gemini to replace queue[0] with a strategically chosen challenger
  const queuedNames = new Set(_state.pairQueue.map(a => a.name));
  const pool = _state.animals
    .map((_, i) => i)
    .filter(i => !_state.used.has(i) && !queuedNames.has(_state.animals[i].name));

  if (pool.length === 0) return;

  const geminiIdx = await _geminiPickChallenger(pool);
  if (geminiIdx !== null) {
    _state.pairQueue[0] = _state.animals[geminiIdx];
  }
}

export function getNextRound() {
  if (_state.pairQueue.length <= QUEUE_MIN) {
    _refillQueue().catch(console.warn);
  }

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

  // Track recent challengers for Gemini context
  _state.recent.push(rightAnimal);
  if (_state.recent.length > 5) _state.recent.shift();

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
