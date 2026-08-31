from flask import Flask
from flask_socketio import SocketIO, emit
import joblib
# Import fungsi fuzzy logic yang kita buat sebelumnya
from fuzzy_logic import calculate_player_suspicion 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rahasia_hitman'
socketio = SocketIO(app, cors_allowed_origins="*")

# 1. Load Model NLU sekali saat server nyala
print("Loading NLU Model...")
intent_model = joblib.load("models/intent_classifier.pkl")

# 2. Database Sementara (Game State)
game_state = {
    "phase": "day",
    "players": {
        "PemainA": {"role": "civilian", "status": "active", "sus_score": 0, "agresivitas": 0},
        "PemainB": {"role": "hitman", "status": "active", "sus_score": 0, "agresivitas": 0},
        "PemainC": {"role": "spy", "status": "hostage", "sus_score": 0, "agresivitas": 0}, # Kena Hostage malam sebelumnya
    }
}

# 3. Menerima chat dari Frontend
@socketio.on('send_chat')
def handle_chat(data):
    sender = data['username']
    text = data['message']
    
    player_info = game_state["players"].get(sender)
    
    # MEKANIK INTI: Jika dia Hostage atau kena Gag Order, chat TIDAK dikirim!
    if player_info["status"] in ["hostage", "gagged"]:
        # Kasih tau frontend-nya dia sendiri bahwa chatnya gagal
        emit('system_alert', {"msg": "Suara Anda hilang..."}, to=data['socket_id'])
        return

    # Prediksi intent menggunakan SVM
    intent = intent_model.predict([text])[0]
    
    # Jika intent-nya menuduh, naikkan poin agresivitas untuk Fuzzy Logic nanti
    if intent == "menuduh":
        game_state["players"][sender]["agresivitas"] += 10
        
    # Broadcast chat ke SEMUA pemain yang connect
    emit('receive_chat', {'sender': sender, 'message': text}, broadcast=True)

# 4. Fungsi Hitman menggunakan "Gag Order" saat fase siang
@socketio.on('use_gag_order')
def handle_gag_order(data):
    target = data['target']
    # Ubah status target diam-diam
    game_state["players"][target]["status"] = "gagged"
    
    # Beri sinyal ke frontend target untuk mendisable kolom chat-nya
    # (Hanya target yang tahu dia digag)
    emit('status_changed', {"status": "gagged"}, room=target)

# 5. Menuju Fase Tribunal (Jalankan Fuzzy Logic)
@socketio.on('start_tribunal')
def start_tribunal():
    for player, stats in game_state["players"].items():
        # Asumsikan kita hitung durasi diam dari timer (misal dari frontend atau tracker backend)
        durasi_diam = 80 if stats["status"] == "gagged" else 20 
        
        # Jalankan Fuzzy Logic
        skor_curiga, _ = calculate_player_suspicion(stats["agresivitas"], durasi_diam)
        game_state["players"][player]["sus_score"] = skor_curiga
        
    # Kirim data kecurigaan ke semua orang untuk voting
    emit('tribunal_data', game_state["players"], broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)