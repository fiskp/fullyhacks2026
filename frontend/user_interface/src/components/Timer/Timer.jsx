import "./Timer.css";

function Timer({ gameStarted, timeLeft }) {

  const TOTAL_TIME = 15;
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const progress = (timeLeft / TOTAL_TIME) * circumference;

  function getTimerColor() {
    if (timeLeft > 8) return "var(--white)";
    if (timeLeft > 4) return "#f5a623";
    return "var(--red)";
  }

  return (
    <div className="timer-bar">
      <div className="timer-circle-wrap">
        <svg width="100" height="100" viewBox="0 0 100 100">
          {/* Background circle */}
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="5"
          />
          {/* Progress circle */}
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke={getTimerColor()}
            strokeWidth="5"
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            strokeLinecap="round"
            transform="rotate(-90 50 50)"
            style={{ transition: "stroke-dashoffset 1s linear, stroke 0.5s" }}
          />
        </svg>
        <span
          className="timer-number"
          style={{ color: getTimerColor() }}
        >
          {gameStarted ? timeLeft : "–"}
        </span>
      </div>
    </div>
  );
}

export default Timer;