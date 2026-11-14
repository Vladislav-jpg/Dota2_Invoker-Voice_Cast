import sys
import json
import queue
import time
import keyboard
import mouse
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# ================= НАСТРОЙКИ =================
# Используем аппаратные скан-коды кнопок. 
# Им безразлично, какая раскладка включена.
# 16 = Q (Й), 17 = W (Ц), 18 = E (У), 19 = R (К), 32 = D (В)
KEYS = {
    "Q": 16, 
    "W": 17, 
    "E": 18, 
    "INVOKE": 19, 
    "SLOT1": 32
}

KEY_DELAY = 0.035
CAST_DELAY = 0.090
CLICK_DELAY = 0.060
CLICK_AFTER_CAST = False 

# Словарь: Фраза -> (Сферы, Применять на себя)[cite: 2]
SPELLS = {
    "cold_snap": ("qqq", False),
    "ghost_walk": ("qqw", False),
    "ice_wall": ("qqe", False),
    "emp": ("www", False),
    "tornado": ("wwq", False),
    "alacrity": ("wwe", False),
    "sun_strike": ("eee", False),
    "forge_spirit": ("eeq", False),
    "chaos_meteor": ("eew", False),
    "deafening_blast": ("qwe", False),
    "cataclysm": ("eee", True),
}

# Фразы, адаптированные под словарь Vosk[cite: 9]
PHRASES = {
    "колд с нэп": "cold_snap", "холод": "cold_snap", "заморозка": "cold_snap",
    "гост волк": "ghost_walk", "походка призрака": "ghost_walk",
    "айс вол": "ice_wall", "стенка": "ice_wall",
    "эмп": "emp", "и эм пи": "emp", "импульс": "emp",
    "торнадо": "tornado", "ветра": "tornado",
    "ала кри ти": "alacrity", "ускорение": "alacrity",
    "сан страйк": "sun_strike", "солнечный удар": "sun_strike",
    "морж спирит": "forge_spirit", "форс спирит": "forge_spirit", "духи": "forge_spirit",
    "котлета": "chaos_meteor", "метеор": "chaos_meteor", "хаос метеор": "chaos_meteor",
    "де фен инг бласт": "deafening_blast", "бласт": "deafening_blast",
    "катаклизма": "cataclysm", "ката клизм": "cataclysm", "катаклизм": "cataclysm"
}
# =============================================

def cast_spell(spell_id):
    if spell_id not in SPELLS: return
    combo, is_self_cast = SPELLS[spell_id]
    
    # 1. Нажимаем сферы по скан-кодам
    for orb in combo:
        keyboard.send(KEYS[orb.upper()])
        time.sleep(KEY_DELAY)
        
    # 2. Invoke
    keyboard.send(KEYS["INVOKE"])
    time.sleep(CAST_DELAY)
    
    # 3. Каст
    if is_self_cast:
        # Для Cataclysm зажимаем Alt отдельно, чтобы Dota успела его зарегистрировать[cite: 2, 10]
        keyboard.press('alt')
        time.sleep(0.01)
        keyboard.send(KEYS["SLOT1"])
        time.sleep(0.01)
        keyboard.release('alt')
    else:
        keyboard.send(KEYS["SLOT1"])
        if CLICK_AFTER_CAST:
            time.sleep(CLICK_DELAY)
            mouse.click('left')

q = queue.Queue()
def audio_callback(indata, frames, time, status):
    if status: print(status, file=sys.stderr)
    q.put(bytes(indata))

def main():
    print("Загрузка модели распознавания...")
    try:
        model = Model("model")
    except Exception as e:
        print("Ошибка: папка 'model' не найдена.")
        return

    vocab = list(PHRASES.keys())
    vocab_json = json.dumps(vocab + ["[unk]"], ensure_ascii=False)
    rec = KalKaldiRecognizer(model, 16000, vocab_json)

    print("✅ Голосовой каст готов! Говорите названия способностей.")
    print("Нажмите Ctrl+C для выхода.")

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                text = res.get("text", "")
                
                if text:
                    for phrase, spell_id in PHRASES.items():
                        if phrase in text:
                            print(f"[{time.strftime('%H:%M:%S')}] Распознано: {phrase} -> Каст: {spell_id}")
                            cast_spell(spell_id)
                            break 

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nВыход...")
