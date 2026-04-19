import { rounds as fallbackRounds } from "./mock_data/rounds";
import { geminiPickRound } from "./geminiSelector";

const HD_BASE    = "/hd";
const HD_FS_PATH = "/agent/sea-swipes/animals.json";
const QUEUE_MIN  = 2;

const _state = {
  rounds: [],    // loaded from HD FS (or fallback)
  pool:   [],    // shuffled indices of rounds not yet queued
  queue:  [],    // round objects ready to show
  scores: [0, 0],
};

async function _fetchRounds() {
  const key = import.meta.env.VITE_HD_API_KEY;
  if (!key) return fallbackRounds;

  const resp = await fetch(`${HD_BASE}/v1/fs`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ op: "read", path: HD_FS_PATH }),
  });
  if (!resp.ok) return fallbackRounds;

  const { content } = await resp.json();
  const json = content.replace(/^<!--[\s\S]*?-->\s*/, "");
  const animals = JSON.parse(json);

  const shuffled = [...animals].sort(() => Math.random() - 0.5);
  const rounds = [];
  for (let i = 0; i + 1 < shuffled.length; i += 2) {
    const a = shuffled[i], b = shuffled[i + 1];
    rounds.push({
      left:    { name: a.name, stat: a.weight_kg },
      right:   { name: b.name, stat: b.weight_kg },
      prompt:  "Which one is heavier? (kg)",
      correct: a.weight_kg >= b.weight_kg ? "left" : "right",
    });
  }
  return rounds.length ? rounds : fallbackRounds;
}

function _shuffledIndices() {
  const arr = _state.rounds.map((_, i) => i);
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export async function initQueue() {
  _state.scores = [0, 0];
  _state.rounds = await _fetchRounds();
  _state.pool   = _shuffledIndices();
  _state.queue  = _state.pool.map(i => _state.rounds[i]);
  _state.pool   = [];
}

export function setScores(p1, p2) {
  _state.scores = [p1, p2];
}

export function getNextRound() {
  if (_state.queue.length <= QUEUE_MIN) {
    _refillQueue().catch(console.warn);
  }
  return _state.queue.shift() ?? _state.rounds[0];
}

async function _refillQueue() {
  const pool = _shuffledIndices().map(i => _state.rounds[i]);

  const geminiIdx = await geminiPickRound(pool, _state.scores);

  if (geminiIdx !== null) {
    const [picked] = pool.splice(geminiIdx, 1);
    _state.queue.push(picked, ...pool);
  } else {
    _state.queue.push(...pool);
  }
}
