import "./Navbar.css"

{/* Navbar component */}
function Navbar() {
  return (
    <header className="navbar">
      {/* P1 badge */}
      <div className="player-badge p1">
        <svg width="20" height="20" viewBox="0 0 24 24"
          fill="none" stroke="#00b4d8"
          strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="8" r="4"/>
          <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
        </svg>
        <span className="player-label">P1:</span>
        <span className="player-score">0</span>
      </div>

      {/* Game Logo */ }
      <h1 className="logo">SEA SLIDES</h1>

      {/* p2 badge */}
      <div className="player-badge p2">
        <svg width="20" height="20" viewBox="0 0 24 24"
          fill="none" stroke="#e94560"
          strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="8" r="4"/>
          <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
        </svg>
        <span className="player-label">P2:</span>
        <span className="player-score">0</span>
      </div>
    </header>
  );
}

export default Navbar;