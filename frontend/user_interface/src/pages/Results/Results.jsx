import { useLocation, useNavigate } from "react-router-dom";
import "./Results.css";

{/* Results page */}
function Results() {
  const location = useLocation();
  const navigate = useNavigate();

  const { p1Score, p2Score } = location.state || { p1Score: 0, p2Score: 0 };

  /* Determine winner */
  function getWinnerText() {
    if (p1Score > p2Score) return "Player 1 Wins";
    if (p2Score > p1Score) return "Player 2 Wins";
    return "It's a Tie!";
  }

  function getWinnerColor() {
    if (p1Score > p2Score) return "#00b4d8";
    if (p2Score > p1Score) return "#e94560";
    return "#f5a623";
  }

  function getWinnerSub() {
    if (p1Score > p2Score) return "dominated the deep sea";
    if (p2Score > p1Score) return "ruled the ocean";
    return "both conquered the deep";
  }

  function playAgain() {
    navigate("/");
  }

  return (
    <div className="results-page">

      {/* Bubbles background */}
      <div className="results-bubbles">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="results-bubble"
            style={{
              width:  `${40 + Math.random() * 120}px`,
              height: `${40 + Math.random() * 120}px`,
              left:   `${Math.random() * 100}%`,
              animationDelay:    `${Math.random() * 6}s`,
              animationDuration: `${5 + Math.random() * 4}s`,
            }}
          />
        ))}
    </div>

      {/* Winner announcement */}
      <p className="results-label">game over</p>
      <h1 className="results-winner" style={{ color: getWinnerColor() }}>
        {getWinnerText()}
      </h1>
      <p className="results-sub">{getWinnerSub()}</p>

      {/* Score cards */}
      <div className="results-scores">
        <div className={`results-card p1 ${p1Score > p2Score ? "winner-card" : ""}`}>
          <svg width="36" height="36" viewBox="0 0 24 24"
            fill="none" stroke="#00b4d8"
            strokeWidth="1.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="10"/>
            <circle cx="12" cy="9" r="3"/>
            <path d="M6 20c0-3 2.7-5 6-5s6 2 6 5"/>
          </svg>
          <span className="results-player p1-label">P1</span>
          <span className="results-num p1-num">{p1Score}</span>
          <span className="results-pts">points</span>
        </div>

        <span className="results-vs">VS</span>

        <div className={`results-card p2 ${p2Score > p1Score ? "winner-card" : ""}`}>
          <svg width="36" height="36" viewBox="0 0 24 24"
            fill="none" stroke="#e94560"
            strokeWidth="1.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="10"/>
            <circle cx="12" cy="9" r="3"/>
            <path d="M6 20c0-3 2.7-5 6-5s6 2 6 5"/>
          </svg>
          <span className="results-player p2-label">P2</span>
          <span className="results-num p2-num">{p2Score}</span>
          <span className="results-pts">points</span>
        </div>
      </div>

      {/* Buttons */}
      <div className="results-btns">
        <button className="btn-play" onClick={playAgain}>Play Again</button>
      </div>

    </div>
  );
}

export default Results;