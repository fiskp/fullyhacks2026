const GEMINI_BASE  = "https://generativelanguage.googleapis.com/v1beta";
const GEMINI_MODEL = "gemini-2.0-flash";

// pool: array of round objects { left, right, prompt, correct }
// scores: [p1, p2]
// Returns an index into pool[], or null on any failure.
export async function geminiPickRound(pool, scores) {
  const key = import.meta.env.VITE_GEMINI_API_KEY;
  if (!key || pool.length === 0) return null;

  const [s1, s2] = scores;
  const gap = s1 - s2;
  const difficultyHint = Math.abs(gap) > 3
    ? "One player is dominating — pick a round where the two stats are close together, making it harder to guess correctly."
    : "Scores are tight — pick a round with a dramatic difference in stats to create excitement.";

  const options = pool
    .map((r, i) => `${i}: ${r.left.name} (${r.left.stat}) vs ${r.right.name} (${r.right.stat}) — ${r.prompt}`)
    .join("\n");

  const prompt = [
    `Player scores — P1: ${s1}, P2: ${s2}.`,
    difficultyHint,
    `Available rounds:\n${options}`,
    "Reply with only the number of the round you choose. No explanation.",
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
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
    const idx = parseInt(text, 10);
    return Number.isFinite(idx) && idx >= 0 && idx < pool.length ? idx : null;
  } catch {
    return null;
  }
}
