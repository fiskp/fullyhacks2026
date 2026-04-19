import "./GameCards.css";
import VSColumn from "../VSColumn/VSColumn";

function GameCards({ round, p1Position, p2Position, revealed, isCorrect, nextRound }) {

  /* Green for correct side, red for incorrect after reveal */
  function getNameColor(side) {
    if (!revealed) return "var(--white)";
    return round.correct === side ? "var(--green)" : "var(--red)";
  }

  return (
    <div className="game-cards">

      {/* Left card */}
      <section className="card left-card">
        <h2
          className="animal-name"
          style={{ color: getNameColor("left") }}
        >
          {round.left.name}
        </h2>
        <div className="stat-pill">
          {revealed ? round.left.stat : "???"}
        </div>
      </section>

      {/* Center overlay */}
      <VSColumn
        p1Position={p1Position}
        p2Position={p2Position}
        prompt={round.prompt}
        revealed={revealed}
        nextRound={nextRound}
      />

      {/* Right card */}
      <section className="card right-card">
        <h2
          className="animal-name"
          style={{ color: getNameColor("right") }}
        >
          {round.right.name}
        </h2>
        <div className="stat-pill">
          {revealed ? round.right.stat : "???"}
        </div>
      </section>

    </div>
  );
}

export default GameCards;