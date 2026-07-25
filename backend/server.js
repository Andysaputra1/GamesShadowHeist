const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const mainRoutes = require('./routes/mainRoutes');
app.use('/', mainRoutes);

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "http://localhost:4200", 
    methods: ["GET", "POST"]
  }
});

io.on('connection', (socket) => {
    console.log(`Pemain terkoneksi ke Socket: ${socket.id}`);
    
    socket.on('disconnect', () => {
        console.log(`Pemain keluar: ${socket.id}`);
    });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`🚀 Backend Express berjalan di http://localhost:${PORT}`);
});