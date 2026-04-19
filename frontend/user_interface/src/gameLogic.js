import { rounds } from "./mock_data/rounds";
import { geminiPickRound } from "./geminiSelector";

const QUEUE_MIN = 2;

const _state = {
  pool:   [],    // shuffled indices of rounds not yet queued
  queue:  [],    // round objects ready to show
  scores: [0, 0],
};

function _shuffledIndices() {
  const arr = rounds.map((_, i) => i);
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export async function initQueue() {
  _state.scores = [0, 0];
  _state.pool  = _shuffledIndices();
  _state.queue = _state.pool.map(i => rounds[i]);
  _state.pool  = [];
}

export function setScores(p1, p2) {
  _state.scores = [p1, p2];
}

export function getNextRound() {
  if (_state.queue.length <= QUEUE_MIN) {
    _refillQueue().catch(console.warn);
  }
  return _state.queue.shift() ?? rounds[0];
}

async function _refillQueue() {
  const pool = _shuffledIndices().map(i => rounds[i]);

  const geminiIdx = await geminiPickRound(pool, _state.scores);

  if (geminiIdx !== null) {
    // Splice Gemini's pick to the front, then append the rest
    const [picked] = pool.splice(geminiIdx, 1);
    _state.queue.push(picked, ...pool);
  } else {
    _state.queue.push(...pool);
  }
}
