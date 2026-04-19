import "./Timer.css";
{ /* Timer component */ }
function Timer({ gameStarted, timeLeft, currentRound }) {

  function getTimerColor() {
    if (timeLeft > 5) return "var(--white)";
    if (timeLeft > 2) return "#f5a623";
    return "var(--red)";
  }

  return (
    <div className="timer-bar">
      {gameStarted && (
        <span className="round-counter">
          Round {currentRound + 1} / 6
        </span>
      )}
      <span
        className="timer-number"
        style={{ color: getTimerColor() }}
      >
        {gameStarted ? timeLeft : "–"}
      </span>
    </div>
  );
}

export default Timer;