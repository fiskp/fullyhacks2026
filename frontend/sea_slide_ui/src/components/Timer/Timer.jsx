import "./Timer.css";
{ /* Timer component */ }
function Timer({ gameStarted, timeLeft }) {

  function getTimerColor() {
    if (timeLeft > 5) return "var(--white)";
    if (timeLeft > 2) return "#f5a623";
    return "var(--red)";
  }

  return (
    <div className="timer-bar">
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