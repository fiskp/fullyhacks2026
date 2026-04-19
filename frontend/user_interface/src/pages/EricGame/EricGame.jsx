import { useState, useEffect, useRef } from "react";
import "../../App.css";
import "./EricGame.css";
import Navbar from "../../components/Navbar/Navbar";
import Timer from "../../components/Timer/Timer";
import GameCards from "../../components/GameCards/GameCards";
import { initEricQueue, getNextEricRound, setEricScores, advanceEricWinner } from "../../gameLogicEric";
import { useNavigate } from "react-router-dom";

function EricGame() {
  const [gameStarted, setGameStarted]   = useState(false);
  const [p1Score, setP1Score]           = useState(0);
  const [p2Score, setP2Score]           = useState(0);
  const [p1Position, setP1Position]     = useState(null);
  const [p2Position, setP2Position]     = useState(null);
  const [currentRound, setCurrentRound] = useState(0);
  const [timeLeft, setTimeLeft]         = useState(10);
  const [revealed, setRevealed]         = useState(false);
  const [roundData, setRoundData]       = useState(null);
  const [queueReady, setQueueReady]     = useState(false);
  const [error, setError]               = useState(null);

  const navigate = useNavigate();

  const p1Ref       = useRef(p1Position);
  const p2Ref       = useRef(p2Position);
  const roundRef    = useRef(currentRound);
  const revealedRef = useRef(revealed);
  const p1ScoreRef  = useRef(0);
  const p2ScoreRef  = useRef(0);
  const roundDataRef = useRef(roundData);

  useEffect(() => { p1Ref.current = p1Position; },       [p1Position]);
  useEffect(() => { p2Ref.current = p2Position; },       [p2Position]);
  useEffect(() => { roundRef.current = currentRound; },  [currentRound]);
  useEffect(() => { revealedRef.current = revealed; },   [revealed]);
  useEffect(() => { p1ScoreRef.current = p1Score; },     [p1Score]);
  useEffect(() => { p2ScoreRef.current = p2Score; },     [p2Score]);
  useEffect(() => { roundDataRef.current = roundData; }, [roundData]);

  useEffect(() => {
    initEricQueue()
      .then(() => {
        setRoundData(getNextEricRound());
        setQueueReady(true);
      })
      .catch(err => setError(err.message));
  }, []);

  useEffect(() => {
    if (queueReady) setGameStarted(true);
  }, [queueReady]);

  useEffect(() => {
    if (!gameStarted || revealed) return;
    function handleKeys(e) {
      if (e.key === "ArrowLeft")  setP1Position("left");
      if (e.key === "ArrowRight") setP1Position("right");
      if (e.key === "a")          setP2Position("left");
      if (e.key === "d")          setP2Position("right");
    }
    window.addEventListener("keydown", handleKeys);
    return () => window.removeEventListener("keydown", handleKeys);
  }, [gameStarted, revealed]);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8765");
    ws.onmessage = (event) => {
      const data = event.data;
      if (data === "p1_right") window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
      if (data === "p1_left")  window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft"  }));
      if (data === "p2_right") window.dispatchEvent(new KeyboardEvent("keydown", { key: "d" }));
      if (data === "p2_left")  window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
    };
    ws.onerror = () => {};
    return () => ws.close();
  }, []);

  useEffect(() => {
    if (!gameStarted || revealed) return;

    const interval = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          clearInterval(interval);

          const correctSide = roundDataRef.current?.correct;
          const p1Correct   = p1Ref.current === correctSide;
          const p2Correct   = p2Ref.current === correctSide;

          if (p1Correct && p2Correct) {
            setP1Score(s => s + 1);
            setP2Score(s => s + 1);
            setEricScores(p1ScoreRef.current + 1, p2ScoreRef.current + 1);
          } else {
            if (p1Correct)  { setP1Score(s => s + 2); setEricScores(p1ScoreRef.current + 2, p2ScoreRef.current); }
            if (p2Correct)  { setP2Score(s => s + 2); setEricScores(p1ScoreRef.current, p2ScoreRef.current + 2); }
            if (!p1Correct && !p2Correct) setEricScores(p1ScoreRef.current, p2ScoreRef.current);
          }

          setRevealed(true);

          setTimeout(() => {
            if (p1ScoreRef.current >= 10 || p2ScoreRef.current >= 10) {
              navigate("/results", {
                state: { p1Score: p1ScoreRef.current, p2Score: p2ScoreRef.current },
              });
              return;
            }

            advanceEricWinner(correctSide);
            setRoundData(getNextEricRound());
            setCurrentRound(r => r + 1);
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
  }, [gameStarted, revealed, navigate]);

  function isCorrect(position) {
    if (!position || !roundData) return false;
    return position === roundData.correct;
  }

  if (error) {
    return (
      <div className="game">
        <div className="eric-error">
          <p>Failed to load Eric Ly questions: {error}</p>
          <button onClick={() => navigate("/")}>Back to Home</button>
        </div>
      </div>
    );
  }

  return (
    <div className="game eric-game">
      <div className="eric-banner">ERIC LY EDITION</div>
      <Navbar p1Score={p1Score} p2Score={p2Score} />
      <Timer gameStarted={gameStarted} timeLeft={timeLeft} />
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

export default EricGame;
