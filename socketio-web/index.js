const express = require("express");
const {Server} = require("socket.io");
const http = require("http");

const app = express();
const server = http.createServer(app);
const io = new Server(server);

io.on('connection', (socket) => {
  socket.on('data', (msg) => {
    socket.broadcast.emit('data', msg);
  });
});

app.use(express.static("static"));

server.listen(9000);
