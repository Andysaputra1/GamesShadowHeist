from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import httpx
import os

app = FastAPI(title="Shadow AI Engine")

# 1. State Management (Penyimpanan Chat Sementara)
# Untuk produksi, sebaiknya gunakan database (Redis/PostgreSQL). Ini menggunakan memory runtime.
game_chat_history = []

# 2. Setup Global Model
svm_model = None
suspicion_sim = None
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama_server:11434/api/generate")

# Mapping nilai agresivitas berdasarkan label intent dari SVM
INTENT_SCORE_MAP = {
    "accusing": 90,
    "persuading": 80,
    "bluffing": 75,
    "deflecting": 60,
    "probing": 50,
    "claiming": 40,
    "defending": 30,
    "neutral": 10
}

def init_fuzzy_logic():
    agresivitas = ctrl.Antecedent(np.arange(0, 101, 1), 'agresivitas_chat')
    durasi_diam = ctrl.Antecedent(np.arange(0, 101, 1), 'durasi_diam')
    curiga = ctrl.Consequent(np.arange(0, 101, 1), 'tingkat_curiga')

    agresivitas['pasif'] = fuzz.trimf(agresivitas.universe, [0, 0, 40])
    agresivitas['netral'] = fuzz.trimf(agresivitas.universe, [30, 50, 70])
    agresivitas['agresif'] = fuzz.trimf(agresivitas.universe, [60, 100, 100])

    durasi_diam['bawel'] = fuzz.trimf(durasi_diam.universe, [0, 0, 30])
    durasi_diam['normal'] = fuzz.trimf(durasi_diam.universe, [20, 50, 80])
    durasi_diam['bungkam'] = fuzz.trimf(durasi_diam.universe, [70, 100, 100])

    curiga['aman'] = fuzz.trimf(curiga.universe, [0, 0, 40])
    curiga['sus'] = fuzz.trimf(curiga.universe, [30, 50, 70])
    curiga['bahaya'] = fuzz.trimf(curiga.universe, [60, 100, 100])

    rule1 = ctrl.Rule(agresivitas['agresif'] & durasi_diam['bawel'], curiga['sus'])
    rule2 = ctrl.Rule(agresivitas['pasif'] & durasi_diam['bungkam'], curiga['bahaya'])
    rule3 = ctrl.Rule(agresivitas['netral'] & durasi_diam['normal'], curiga['aman'])
    rule4 = ctrl.Rule(agresivitas['agresif'] & durasi_diam['bungkam'], curiga['bahaya'])
    rule5 = ctrl.Rule(agresivitas['netral'] & durasi_diam['bawel'], curiga['aman'])
    
    suspicion_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5])
    return ctrl.ControlSystemSimulation(suspicion_ctrl)

@app.on_event("startup")
def load_models():
    global svm_model, suspicion_sim
    try:
        svm_model = joblib.load("models/intent_classifier.pkl")
        print("Model SVM berhasil dimuat.")
    except Exception as e:
        print(f"Gagal memuat model SVM: {e}")
    
    suspicion_sim = init_fuzzy_logic()
    print("Sistem Fuzzy Logic berhasil diinisialisasi.")

class ChatRequest(BaseModel):
    player_name: str
    message: str
    silence_percentage: int  # Persentase durasi diam pemain (0-100) yang dikirim dari frontend

@app.post("/api/analyze")
async def analyze_chat(req: ChatRequest):
    if not svm_model or not suspicion_sim:
        raise HTTPException(status_code=500, detail="Model belum siap.")

    # 1. Simpan ke histori
    game_chat_history.append(f"{req.player_name}: {req.message}")

    # 2. Klasifikasi Intent dengan SVM
    predicted_intent = svm_model.predict([req.message])[0]
    
    # 3. Hitung Agresivitas & Masukkan ke Fuzzy Logic
    aggressiveness_score = INTENT_SCORE_MAP.get(predicted_intent, 10)
    
    suspicion_sim.input['agresivitas_chat'] = aggressiveness_score
    suspicion_sim.input['durasi_diam'] = req.silence_percentage
    suspicion_sim.compute()
    
    sus_score = suspicion_sim.output['tingkat_curiga']
    
    if sus_score >= 60:
        sus_status = "BAHAYA"
    elif sus_score >= 40:
        sus_status = "SUS"
    else:
        sus_status = "AMAN"

    # 4. Susun Prompt untuk LLM (Deepseek)
    history_text = "\n".join(game_chat_history[-10:]) # Ambil 10 chat terakhir agar konteks tidak terlalu panjang
    
    prompt = f"""
Kamu adalah AI Host dalam game deduksi sosial (seperti Mafia/Town of Salem).
Berikut adalah percakapan terakhir para pemain:
{history_text}

Analisis sistem terhadap pemain '{req.player_name}':
- Pesan terakhir: "{req.message}"
- Intent pesan (SVM): {predicted_intent}
- Tingkat Kecurigaan (Fuzzy Logic): {sus_score:.2f} ({sus_status})

Berikan respons singkat (maksimal 2 kalimat) sebagai AI Host yang mengomentari tingkah laku '{req.player_name}' berdasarkan status '{sus_status}' dan intent '{predicted_intent}'. Jangan sebutkan angka skor secara mentah, gunakan gaya bahasa misterius.
"""

    # 5. Panggil Ollama secara asinkron
    llm_reply = "AI Host sedang offline."
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": "deepseek-r1:1.5b",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30.0
            )
            if response.status_code == 200:
                llm_reply = response.json().get("response", "").strip()
    except Exception as e:
        print(f"Error memanggil Ollama: {e}")

    return {
        "intent": predicted_intent,
        "fuzzy": {
            "aggressiveness": aggressiveness_score,
            "suspicion_score": round(sus_score, 2),
            "status": sus_status
        },
        "llm_response": llm_reply
    }

@app.delete("/api/reset")
def reset_history():
    global game_chat_history
    game_chat_history = []
    return {"message": "Histori chat game berhasil di-reset."}