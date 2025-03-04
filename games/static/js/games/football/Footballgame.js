const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

// Game Dimensions
canvas.width = 800;
canvas.height = 400;

// Player & Ball State
let players = {
    player1: { x: 150, y: 200, team: "A" },
    player2: { x: 650, y: 200, team: "B" }
};
let ball = { x: 400, y: 200, vx: 0, vy: 0, speed: 5 };

// Scores
let scores = { A: 0, B: 0 };

// Movement Controls
let keys = {};

window.addEventListener("keydown", (e) => keys[e.key] = true);
window.addEventListener("keyup", (e) => keys[e.key] = false);

// Game Loop
function update() {
    movePlayers();
    moveBall();
    checkCollisions();
    drawGame();
    requestAnimationFrame(update);
}

// Move Players
function movePlayers() {
    let speed = 4;
    
    if (keys["ArrowUp"]) players.player1.y -= speed;
    if (keys["ArrowDown"]) players.player1.y += speed;
    if (keys["ArrowLeft"]) players.player1.x -= speed;
    if (keys["ArrowRight"]) players.player1.x += speed;

    if (keys["w"]) players.player2.y -= speed;
    if (keys["s"]) players.player2.y += speed;
    if (keys["a"]) players.player2.x -= speed;
    if (keys["d"]) players.player2.x += speed;

    if (keys[" "]) kickBall(players.player1);
}

// Ball Movement
function moveBall() {
    ball.x += ball.vx;
    ball.y += ball.vy;

    ball.vx *= 0.98; // Friction
    ball.vy *= 0.98;

    // Bounce off walls
    if (ball.y <= 0 || ball.y >= canvas.height) ball.vy *= -1;
}

// Collision Detection (Player & Ball)
function checkCollisions() {
    for (let p in players) {
        let player = players[p];
        let dx = ball.x - player.x;
        let dy = ball.y - player.y;
        let distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < 20) {
            ball.vx = dx * 0.3;
            ball.vy = dy * 0.3;
        }
    }

    // Goal Detection
    if (ball.x <= 20) {
        scores.B++;
        resetBall();
    }
    if (ball.x >= canvas.width - 20) {
        scores.A++;
        resetBall();
    }
}

// Kick Ball
function kickBall(player) {
    let dx = ball.x - player.x;
    let dy = ball.y - player.y;
    let distance = Math.sqrt(dx * dx + dy * dy);

    if (distance < 30) {
        ball.vx = dx * 0.5;
        ball.vy = dy * 0.5;
    }
}

// Reset Ball after Goal
function resetBall() {
    ball.x = canvas.width / 2;
    ball.y = canvas.height / 2;
    ball.vx = 0;
    ball.vy = 0;
    updateScoreboard();
}

// Update Scoreboard
function updateScoreboard() {
    document.getElementById("teamAScore").textContent = `Team A: ${scores.A}`;
    document.getElementById("teamBScore").textContent = `Team B: ${scores.B}`;
}

// Draw Game Elements
function drawGame() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw Players
    for (let p in players) {
        let player = players[p];
        ctx.fillStyle = player.team === "A" ? "blue" : "red";
        ctx.beginPath();
        ctx.arc(player.x, player.y, 15, 0, Math.PI * 2);
        ctx.fill();
    }

    // Draw Ball
    ctx.fillStyle = "white";
    ctx.beginPath();
    ctx.arc(ball.x, ball.y, 10, 0, Math.PI * 2);
    ctx.fill();
}

update();
