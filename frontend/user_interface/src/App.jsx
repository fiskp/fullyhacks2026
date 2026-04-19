import { useState, useEffect, useRef } from "react";
import "./App.css";
import Navbar from "./components/Navbar/Navbar";
import Timer from "./components/Timer/Timer";
import GameCards from "./components/GameCards/GameCards";
import { initQueue, getNextRound, setScores, advanceWinner } from "./gameLogic";
import { useNavigate } from "react-router-dom";

const TOTAL_ROUNDS = 6;

function App() {

  const [gameStarted, setGameStarted]   = useState(false);
  const [p1Score, setP1Score]           = useState(0);
  const [p2Score, setP2Score]           = useState(0);
  const [p1Position, setP1Position]     = useState(null);
  const [p2Position, setP2Position]     = useState(null);
  const [currentRound, setCurrentRound] = useState(0);
  const [timeLeft, setTimeLeft]         = useState(15);
  const [revealed, setRevealed]         = useState(false);
  const [roundData, setRoundData]       = useState(null);
  const [queueReady, setQueueReady]     = useState(false);

  const navigate = useNavigate();

  /* Refs to avoid stale closures inside setTimeout */
  const p1Ref       = useRef(p1Position);
  const p2Ref       = useRef(p2Position);
  const roundRef    = useRef(currentRound);
  const revealedRef = useRef(revealed);
  const p1ScoreRef  = useRef(0);
  const p2ScoreRef  = useRef(0);

  const roundDataRef = useRef(roundData);

  /* Keep refs in sync with state */
  useEffect(() => { p1Ref.current = p1Position; },        [p1Position]);
  useEffect(() => { p2Ref.current = p2Position; },        [p2Position]);
  useEffect(() => { roundRef.current = currentRound; },   [currentRound]);
  useEffect(() => { revealedRef.current = revealed; },    [revealed]);
  useEffect(() => { p1ScoreRef.current = p1Score; },      [p1Score]);
  useEffect(() => { p2ScoreRef.current = p2Score; },      [p2Score]);
  useEffect(() => { roundDataRef.current = roundData; },  [roundData]);

  /* Load animal queue on mount */
  useEffect(() => {
    initQueue()
      .then(() => {
        setRoundData(getNextRound());
        setQueueReady(true);
      })
      .catch(err => console.error("Failed to load animals:", err));
  }, []);

  /* Start game on Enter — only once the animal queue is ready */
  useEffect(() => {
    function handleStart(e) {
      if (e.key === "Enter" && !gameStarted && queueReady) {
        setGameStarted(true);
      }
    }
    window.addEventListener("keydown", handleStart);
    return () => window.removeEventListener("keydown", handleStart);
  }, [gameStarted, queueReady]);

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

  /* WebSocket — receives CV swipe events from Python */
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8765");
    
    ws.onmessage = (event) => {
      const data = event.data;
      if (data === "p1_right") window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }));
      if (data === "p1_left")  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }));
      if (data === "p2_right") window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
      if (data === "p2_left")  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp' }));
      if (data === "start")    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    };

  ws.onerror = (err) => console.log("WebSocket error:", err);

  return () => ws.close();
}, []);

  /* Timer — reveals on 0, auto advances, navigates to results */
  useEffect(() => {
    if (!gameStarted || revealed) return;

    const interval = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          clearInterval(interval);

          /* Score calculation using refs */
          const correctSide = roundDataRef.current?.correct;
          const p1Correct   = p1Ref.current === correctSide;
          const p2Correct   = p2Ref.current === correctSide;

          if (p1Correct && p2Correct) {
            setP1Score(s => s + 1);
            setP2Score(s => s + 1);
            setScores(p1ScoreRef.current + 1, p2ScoreRef.current + 1);
          } else {
            if (p1Correct)  { setP1Score(s => s + 2); setScores(p1ScoreRef.current + 2, p2ScoreRef.current); }
            if (p2Correct)  { setP2Score(s => s + 2); setScores(p1ScoreRef.current, p2ScoreRef.current + 2); }
            if (!p1Correct && !p2Correct) setScores(p1ScoreRef.current, p2ScoreRef.current);
          }

          setRevealed(true);

          /* Auto advance after 2 seconds */
          setTimeout(() => {
            const next = roundRef.current + 1;

            if (next >= TOTAL_ROUNDS) {
              navigate("/results", {
                state: {
                  p1Score: p1ScoreRef.current,
                  p2Score: p2ScoreRef.current,
                }
              });
              return;
            }

            advanceWinner(correctSide);
            setRoundData(getNextRound());
            setCurrentRound(next);
            setP1Position(null);
            setP2Position(null);
            setRevealed(false);
            setTimeLeft(15);
          }, 2000);

          return 0;
        }
        return t - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [gameStarted, revealed, navigate]);

  function isCorrect(position) {
    if (!position || !roundData) return false;
    return position === roundData.correct;
  }

  return (
    <div className="game">

      {!gameStarted && (
        <div className="start-overlay">
          <p className="start-sub">
            {queueReady ? "Press Enter to Start" : "Loading animals..."}
          </p>
        </div>
      )}

      <Navbar p1Score={p1Score} p2Score={p2Score} />
      <Timer
        gameStarted={gameStarted}
        timeLeft={timeLeft}
        currentRound={currentRound}
      />
      {roundData && (
        <GameCards
          round={roundData}
          p1Position={p1Position}
          p2Position={p2Position}
          revealed={revealed}
          isCorrect={isCorrect}
        />
      )}

    </div>
  );
}

export default App;