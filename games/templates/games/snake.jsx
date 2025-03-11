import { useEffect, useState, useRef, useCallback } from "react";

const roomCode = "default_room"; // Temporary room for testing
const ws = new WebSocket(`ws://localhost:8000/ws/snake-game/${roomCode}/`);

const SnakeGame = () => {
  const canvasRef = useRef(null);
  const [players, setPlayers] = useState({});
  const [playerId, setPlayerId] = useState(null);
  const [direction, setDirection] = useState({ x: 1, y: 0 });

  // Handle incoming WebSocket messages
  useEffect(() => {
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "player_id") {
        setPlayerId(data.id); // Store the assigned player ID
      }

      if (data.type === "game_state") {
        setPlayers(data.players);
      }
    };
  }, []);

  // Function to send snake movement updates
  const moveSnake = useCallback(() => {
    if (!playerId || !players[playerId]) return;

    const updatedSnake = players[playerId].snake.map((seg, index) => {
      return index === 0 // Move only the head based on direction
        ? { x: seg.x + direction.x * 10, y: seg.y + direction.y * 10 }
        : { ...players[playerId].snake[index - 1] };
    });

    ws.send(
      JSON.stringify({
        type: "snake_update",
        id: playerId,
        snake: updatedSnake,
        direction,
      })
    );
  }, [players, direction, playerId]);

  // Move the snake at a fixed interval
  useEffect(() => {
    const gameInterval = setInterval(moveSnake, 100);
    return () => clearInterval(gameInterval);
  }, [moveSnake]);

  // Draw the game state on the canvas
  const drawGame = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear canvas

    Object.values(players).forEach((player) => {
      ctx.fillStyle = playerId === player.id ? "blue" : "green"; // Different color for own snake
      player.snake.forEach((segment) => {
        ctx.fillRect(segment.x, segment.y, 10, 10);
      });
    });
  };

  useEffect(() => {
    drawGame();
  }, [players]);

  // Handle keyboard inputs for snake direction
  const handleKeyDown = (event) => {
    switch (event.key) {
      case "ArrowUp":
        if (direction.y === 0) setDirection({ x: 0, y: -1 });
        break;
      case "ArrowDown":
        if (direction.y === 0) setDirection({ x: 0, y: 1 });
        break;
      case "ArrowLeft":
        if (direction.x === 0) setDirection({ x: -1, y: 0 });
        break;
      case "ArrowRight":
        if (direction.x === 0) setDirection({ x: 1, y: 0 });
        break;
      default:
        break;
    }
  };

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [direction]);

  return (
    <div>
      <h2>Multiplayer Snake Game</h2>
      <canvas ref={canvasRef} width={600} height={600} style={{ border: "1px solid black" }} />
    </div>
  );
};

export default SnakeGame;
