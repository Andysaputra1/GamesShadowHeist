const express = require('express');
const router = express.Router();

const gameRoutes = require('./api/gameRoutes');

router.use('/api/game', gameRoutes);

router.get('/app-status', async (req, res) => {
    const response = {
        app_name: "Shadow Heist Backend",
        status: "OK",
        server_date: new Date(),
    };
    res.status(200).json(response);
});

router.use(function(req, res){
    res.status(404).json({
        status: "ERROR",
        message: "Endpoint API tidak ditemukan (404)"
    });
});

module.exports = router;