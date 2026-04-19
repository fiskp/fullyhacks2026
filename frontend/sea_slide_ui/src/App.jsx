import { useState, useEffect, useRef } from "react";
import "./App.css";
import Navbar from "./components/Navbar/Navbar";
import Timer from "./components/Timer/Timer";
import GameCards from "./components/GameCards/GameCards";
import { rounds } from "./mock_data/rounds";

function App() {

  const [gameStarted, setGameStarted]   = useState(false);
  const [p1Score, setP1Score]           = useState(0);
  const [p2Score, setP2Score]           = useState(0);
  const [p1Position, setP1Position]     = useState(null);
  const [p2Position, setP2Position]     = useState(null);
  const [currentRound, setCurrentRound] = useState(0);
  const [timeLeft, setTimeLeft]         = useState(10);
  const [revealed, setRevealed]         = useState(false);

  /* useRef lets us read current values inside setTimeout without stale closures */
  const p1Ref       = useRef(p1Position);
  const p2Ref       = useRef(p2Position);
  const roundRef    = useRef(currentRound);
  const revealedRef = useRef(revealed);

  /* Keep refs in sync with state */
  useEffect(() => { p1Ref.current = p1Position; },    [p1Position]);
  useEffect(() => { p2Ref.current = p2Position; },    [p2Position]);
  useEffect(() => { roundRef.current = currentRound; }, [currentRound]);
  useEffect(() => { revealedRef.current = revealed; }, [revealed]);

  const round = rounds[currentRound];

  /* Start game on Enter */
  useEffect(() => {
    function handleStart(e) {
      if (e.key === "Enter" && !gameStarted) {
        setGameStarted(true);
      }
    }
    window.addEventListener("keydown", handleStart);
    return () => window.removeEventListener("keydown", handleStart);
  }, [gameStarted]);

  /* Arrow keys — only before reveal */
  useEffect(() => {
    if (!gameStarted || revealed) return;

    function handleKeys(e) {
      if (e.key === "ArrowLeft")  setP1Position("left");
      if (e.key === "ArrowRight") setP1Position("right");
      if (e.key === "ArrowUp")    setP2Position("left");
      if (e.key === "ArrowDown")  setP2Position("right");
    }

    window.addEventListener("keydown", handleKeys);
    return () => window.removeEventListener("keydown", handleKeys);
  }, [gameStarted, revealed]);

  /* Timer — clean and simple */
  useEffect(() => {
    if (!gameStarted || revealed) return;

    const interval = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          clearInterval(interval);

          /* Reveal using refs so values are always current */
          const correctSide = rounds[roundRef.current].correct;
          const p1Correct = p1Ref.current === correctSide;
          const p2Correct = p2Ref.current === correctSide;

          if (p1Correct && p2Correct) {
            /* Both correct — 1 point each */
            setP1Score(s => s + 1);
            setP2Score(s => s + 1);
          } else {
            /* Only one correct — 2 points */
            if (p1Correct) setP1Score(s => s + 2);
            if (p2Correct) setP2Score(s => s + 2);
          }
          setRevealed(true);

          /* Auto advance after 2 seconds */
          setTimeout(() => {
            const next = roundRef.current + 1;
            if (next >= rounds.length) {
              alert("Game Over!");
              return;
            }
            setCurrentRound(next);
            setP1Position(null);
            setP2Position(null);
            setRevealed(false);
            setTimeLeft(10);
          }, 2000);

          return 0;
        }
        return t - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [gameStarted, revealed]);

  /* Check if position is correct */
  function isCorrect(position) {
    if (!position) return false;
    return position === round.correct;
  }

  return (
    <div className="game">

      {!gameStarted && (
        <div className="start-overlay">
          <p className="start-sub">Press Enter to Start</p>
        </div>
      )}

      <Navbar p1Score={p1Score} p2Score={p2Score} />
      <Timer gameStarted={gameStarted} timeLeft={timeLeft} />
      <GameCards
        round={round}
        p1Position={p1Position}
        p2Position={p2Position}
        revealed={revealed}
        isCorrect={isCorrect}
      />

    </div>
  );
}

export default App;