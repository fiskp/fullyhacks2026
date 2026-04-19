# Sea Swipe — Frontend 🌊

React frontend for Sea Swipe, a two-player gesture-controlled trivia game.

## Tech Stack

- React + Vite
- React Router
- WebSocket (receives CV gestures from Python)
- Human Delta API (animal knowledge layer)

## Running

```bash
npm install
npm run dev
```

Open `http://localhost:5173`

## Pages

- `/` — Homepage, enter a category to start
- `/game` — Main game screen
- `/results` — Winner and final scores

## Controls (keyboard fallback)

| Key | Player | Action |
|---|---|---|
| Arrow Left | P1 | Left |
| Arrow Right | P1 | Right |
| Arrow Up | P2 | Left |
| Arrow Down | P2 | Right |

## Scoring

- Both correct → 1 point each
- One correct → 2 points
- First to 10 wins

## Structure

```
src/
  components/
    Navbar/
    Timer/
    GameCards/
    VSColumn/
  pages/
    Home/
    Results/
  mock_data/
  utils/
```