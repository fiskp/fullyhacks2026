import { rounds } from "./mock_data/rounds";

let _index = 0;

export async function initQueue() {
  _index = 0;
}

export function getNextRound() {
  const round = rounds[_index % rounds.length];
  _index++;
  return round;
}
