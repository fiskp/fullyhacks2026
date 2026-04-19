import { useEffect, useRef } from "react";
import "./VSColumn.css";

function VSColumn({ p1Position, p2Position, prompt, revealed }) {

  const videoRef = useRef(null);

  /* Start webcam feed */
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch(err => console.log("Camera error:", err));
  }, []);

  function getIconClass(position) {
    if (position === "left")  return "player-icon moved-left";
    if (position === "right") return "player-icon moved-right";
    return "player-icon";
  }

  return (
    <div className="vs-column">

      <div className="icons-row">
        <div className={getIconClass(p1Position)}>
          <svg width="52" height="52" viewBox="0 0 24 24"
            fill="none" stroke="#00b4d8"
            strokeWidth="1.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="10"/>
            <circle cx="12" cy="9" r="3"/>
            <path d="M6 20c0-3 2.7-5 6-5s6 2 6 5"/>
          </svg>
        </div>

        <div className={getIconClass(p2Position)}>
          <svg width="52" height="52" viewBox="0 0 24 24"
            fill="none" stroke="#e94560"
            strokeWidth="1.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="10"/>
            <circle cx="12" cy="9" r="3"/>
            <path d="M6 20c0-3 2.7-5 6-5s6 2 6 5"/>
          </svg>
        </div>
      </div>

      <div className="vs-group">

        {/* Prompt updates each round */}
        <div className="prompt-box">{prompt}</div>

        {/* Hide VS circle after reveal */}
        {!revealed && <div className="vs-circle">VS</div>}

        {/* Live webcam feed */}
        <video
          ref={videoRef}
          autoPlay
          muted
          className="camera-feed"
        />

      </div>

    </div>
  );
}

export default VSColumn;