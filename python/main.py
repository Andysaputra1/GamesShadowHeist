from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pickle
import skfuzzy as fuzz
from skfuzzy import control as ctrl 
import numpy as np
import requests

import os
from dotenv import load_dotenv

load_dotenv()

def calculate_npc_threat(role, kekayaan_saat_ini, jumlah_tuduhan, total_polisi):
    kekayaan = ctrl.Antecedent(np.arange(0, 10001, 1), 'kekayaan')
    tekanan_sosial = ctrl.Antecedent(np.arange(0, 11, 1), 'tekanan_sosial')
    ancaman = ctrl.Consequent(np.arange(0, 101, 1), 'ancaman')

    kekayaan['miskin'] = fuzz.trimf(kekayaan.universe, [0, 0, 4000])
    kekayaan['menengah'] = fuzz.trimf(kekayaan.universe, [2000, 5000, 8000])
    kekayaan['kaya'] = fuzz.trimf(kekayaan.universe, [6000, 10000, 10000])

    tekanan_sosial['aman'] = fuzz.trimf(tekanan_sosial.universe, [0, 0, 3])
    tekanan_sosial['waspada'] = fuzz.trimf(tekanan_sosial.universe, [2, 5, 8])
    tekanan_sosial['bahaya'] = fuzz.trimf(tekanan_sosial.universe, [6, 10, 10])

    ancaman['rendah'] = fuzz.trimf(ancaman.universe, [0, 0, 40])
    ancaman['sedang'] = fuzz.trimf(ancaman.universe, [30, 50, 70])
    ancaman['tinggi'] = fuzz.trimf(ancaman.universe, [60, 100, 100])

    rules = [
        ctrl.Rule(tekanan_sosial['bahaya'], ancaman['tinggi']),
        ctrl.Rule(kekayaan['kaya'] & tekanan_sosial['aman'], ancaman['sedang']),
        ctrl.Rule(kekayaan['kaya'] & tekanan_sosial['waspada'], ancaman['tinggi']),
        ctrl.Rule(kekayaan['menengah'] & tekanan_sosial['aman'], ancaman['rendah']),
        ctrl.Rule(kekayaan['menengah'] & tekanan_sosial['waspada'], ancaman['sedang']),
        ctrl.Rule(kekayaan['miskin'] & tekanan_sosial['aman'], ancaman['rendah']),
        ctrl.Rule(kekayaan['miskin'] & tekanan_sosial['waspada'], ancaman['rendah']),
        ctrl.Rule(tekanan_sosial['waspada'], ancaman['sedang']),
    ]
    
    tipe_ancaman_ctrl = ctrl.ControlSystem(rules)
    simulasi = ctrl.ControlSystemSimulation(tipe_ancaman_ctrl)

    simulasi.input['kekayaan'] = kekayaan_saat_ini
    
    multiplier = 1.2 if total_polisi >= 2 else 1.0
    simulasi.input['tekanan_sosial'] = min(jumlah_tuduhan * multiplier, 10)

    simulasi.compute()
    base_threat = simulasi.output['ancaman']

    if role in ['gangster', 'ketua_gangster']:
        final_threat = min(base_threat + 10, 100) 
    else:
        final_threat = base_threat 

    return final_threat

app = FastAPI(title="Shadow Heist AI Engine")

try:
    with open("models/intent_classifier.pkl", "rb") as f:
        nlu_model = pickle.load(f)
except Exception as e:
    print("Warning: Model NLU gagal diload! Pastikan path folder benar.", e)

class ChatRequest(BaseModel):
    player_message: str  
    kekayaan_saat_ini: int
    jumlah_tuduhan: int
    total_polisi: int
    role: str           

@app.post("/api/ai-chat")
async def generate_ai_response(req: ChatRequest):
    try:
        intent = nlu_model.predict([req.player_message])[0]
        intent = "defending"
        
        threat_level = calculate_npc_threat(req.role, req.kekayaan_saat_ini, req.jumlah_tuduhan, req.total_polisi)
        threat_level = 75.5

        prompt = f"""
        Kamu adalah NPC di game Shadow Heist. 
        Pemain berkata: "{req.player_message}"
        Niat pemain terdeteksi sebagai: {intent}.
        Tingkat kepanikanmu saat ini: {threat_level:.2f}%.
        Balas chat pemain ini dengan gaya bahasa gamer Indonesia!
        """

        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        payload = {
            "model": "deepseek-r1:14b",
            "prompt": prompt,
            "stream": False
        }
                
        response = requests.post(ollama_url, json=payload)
        response_data = response.json()
        final_reply = response_data.get("response", "Sinyal radio terganggu...")

        return {
            "success": True,
            "intent_detected": intent,
            "threat_level": round(threat_level, 2),
            "reply": final_reply
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))