import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Home.css";

import sharkSvg  from "../../assets/shark.svg";
import jellyfish from "../../assets/jellyfish.svg";
import octopus   from "../../assets/octopus.svg";
import seaTurtle from "../../assets/sea-turtle.svg";
import whale      from "../../assets/whale.svg";

function Home() {
  const [category, setCategory] = useState("");
  const navigate = useNavigate();

  function handleStart() {
    if (!category.trim()) return;
    navigate("/game", { state: { category } });
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") handleStart();
  }

  return (
    <div className="home">

      {/* Sea animal decorations */}
      <img src={sharkSvg}  className="sea-animal animal-shark"   alt="" />
      <img src={jellyfish} className="sea-animal animal-jelly"   alt="" />
      <img src={octopus}   className="sea-animal animal-octopus" alt="" />
      <img src={seaTurtle} className="sea-animal animal-turtle"  alt="" />
      <img src={whale}      className="sea-animal animal-whale"      alt="" />

      {/* Content */}
      <div className="home-content">

        <h1 className="home-title">SEA SLIDES</h1>
        <p className="home-sub">First player to reach 10 points wins the game</p>

        {/* Input with gradient border */}
        <div className="input-wrapper">
          <input
            type="text"
            className="category-input"
            placeholder="e.g. Ocean animals, Space, History..."
            value={category}
            onChange={e => setCategory(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>

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