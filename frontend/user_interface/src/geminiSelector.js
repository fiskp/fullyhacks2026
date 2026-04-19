const GEMINI_BASE  = "https://generativelanguage.googleapis.com/v1beta";
const GEMINI_MODEL = "gemini-2.0-flash";

async function _callGemini(prompt) {
  const key = import.meta.env.VITE_GEMINI_API_KEY;
  if (!key) return null;
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

// HD mode: pick the most strategic next challenger from a pool of animals.
// pool: array of animal objects { name, weight_kg }
// winner: current winning animal object, or null
// recent: array of recent challenger objects
// scores: [p1, p2]
// Returns an index into pool[], or null on any failure.
export async function geminiPickAnimal(pool, winner, recent, scores) {
  if (!pool.length) return null;

  const [s1, s2] = scores;
  const gap = s1 - s2;
  const difficultyHint = Math.abs(gap) > 3
    ? "One player is dominating — pick a challenger with weight very close to the current winner to make guessing harder."
    : "Scores are tight — pick a challenger with a dramatic weight difference for excitement.";

  const options = pool
    .map((a, i) => `${i}: ${a.name} (${a.weight_kg} kg)`)
    .join("\n");

  const prompt = [
    `Current winner: ${winner ? `${winner.name} (${winner.weight_kg} kg)` : "none"}.`,
    `Recent challengers: ${recent.slice(-3).map(a => a.name).join(", ") || "none"}.`,
    `Player scores — P1: ${s1}, P2: ${s2}.`,
    difficultyHint,
    `Available challengers:\n${options}`,
    "Reply with only the number of the challenger you choose. No explanation.",
  ].join("\n");

  const text = await _callGemini(prompt);
  if (text === null) return null;
  const idx = parseInt(text, 10);
  return Number.isFinite(idx) && idx >= 0 && idx < pool.length ? idx : null;
}

// Mock-data fallback mode: pick the most strategic next round from a pool.
// pool: array of round objects { left, right, prompt, correct }
// scores: [p1, p2]
// Returns an index into pool[], or null on any failure.
export async function geminiPickRound(pool, scores) {
  if (!pool.length) return null;

  const [s1, s2] = scores;
  const gap = s1 - s2;
  const difficultyHint = Math.abs(gap) > 3
    ? "One player is dominating — pick a round where the two stats are close together, making it harder to guess."
    : "Scores are tight — pick a round with a dramatic stat difference for excitement.";

  const options = pool
    .map((r, i) => `${i}: ${r.left.name} (${r.left.stat}) vs ${r.right.name} (${r.right.stat}) — ${r.prompt}`)
    .join("\n");

  const prompt = [
    `Player scores — P1: ${s1}, P2: ${s2}.`,
    difficultyHint,
    `Available rounds:\n${options}`,
    "Reply with only the number of the round you choose. No explanation.",
  ].join("\n");

  const text = await _callGemini(prompt);
  if (text === null) return null;
  const idx = parseInt(text, 10);
  return Number.isFinite(idx) && idx >= 0 && idx < pool.length ? idx : null;
}
