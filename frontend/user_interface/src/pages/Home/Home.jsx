import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Home.css";

function Home() {
  const [category, setCategory] = useState("");
  const navigate = useNavigate();

  function handleStart() {
    if (!category.trim()) {
      return;
    }
    navigate("/game", { state: { category } });
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") {
      handleStart();
    }
  }

  return (
    <div className="home">
    {/* Content */}
    <div className="home-content">

    {/* Title */}
    <h1 className="home-title">SEA SLIDES</h1>
    <p className="home-sub">What do you want to explore today?</p>

    {/* Input with gradient border */}
    <div className="input-wrapper">
      <input
        type="text"
        className="category-input"
        placeholder="Ocean animals, Space, History"
        value={category}
        onChange={e => setCategory(e.target.value)}
        onKeyDown={handleKeyDown}
        />
    </div> 

    {/* Start button */}
    <button
      className="start-btn"
      onClick={handleStart}
      disabled={!category.trim()}
      >
        START GAME
      </button>

      </div>

      </div>
  );
}

export default Home;