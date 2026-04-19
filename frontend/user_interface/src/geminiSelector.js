const GEMINI_BASE  = "https://generativelanguage.googleapis.com/v1beta";
const GEMINI_MODEL = "gemini-2.0-flash";

const _ctx = {
  winner:  null,   // current winning animal { name, weight_kg }
  recent:  [],     // last 5 challengers
  scores:  [0, 0], // [p1, p2]
};

export function updateContext({ winner, challenger, scores }) {
  if (winner  !== undefined) _ctx.winner = winner;
  if (scores  !== undefined) _ctx.scores = scores;
  if (challenger) {
    _ctx.recent.push(challenger);
    if (_ctx.recent.length > 5) _ctx.recent.shift();
  }
}

// Returns the name of the chosen animal, or null on any failure.
export async function geminiPickChallenger(pool) {
  const key = import.meta.env.VITE_GEMINI_API_KEY;
  if (!key) return null;

  const available = pool.map(a => `${a.name} (${a.weight_kg} kg)`);
  const gap = _ctx.scores[0] - _ctx.scores[1];
  const difficultyHint = Math.abs(gap) > 3
    ? "The game is unbalanced — pick an animal with weight very close to the current winner to make guessing harder."
    : "Scores are close — pick a dramatic weight contrast to keep the energy high.";

  const prompt = [
    `Current winner: ${_ctx.winner ? `${_ctx.winner.name} (${_ctx.winner.weight_kg} kg)` : "none"}.`,
    `Recent challengers: ${_ctx.recent.slice(-3).map(a => a.name).join(", ") || "none"}.`,
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
    return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? null;
  } catch {
    return null;
  }
}
