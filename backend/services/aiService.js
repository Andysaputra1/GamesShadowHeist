const axios = require('axios');

const PYTHON_AI_URL = 'http://localhost:8000/api/ai-chat'; // URL FastAPI Python nanti

exports.getAIReply = async (playerMessage) => {
    try {
        // Nembak ke Python
        const response = await axios.post(PYTHON_AI_URL, {
            player_message: playerMessage
        });
        return response.data.reply;
    } catch (error) {
        throw new Error("Koneksi ke Python gagal");
    }
};