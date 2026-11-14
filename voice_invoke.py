import sys
import json
import queue
import time
import random
import keyboard
import mouse
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# ================= НАСТРОЙКИ =================
# Аппаратные скан-коды (не зависят от раскладки РУС/ENG)
# 16 = Q, 17 = W, 18 = E, 19 = R, 32 = D
KEYS = {
    "Q": 16, 
    "W": 17, 
    "E": 18, 
    "INVOKE": 19, 
    "SLOT1": 32
}

# Базовые тайминги (в секундах)
KEY_DELAY = 0.035
CAST_DELAY = 0.090
CLICK_DELAY = 0.060

# Обычный каст (True) или Quickcast (False)
CLICK_AFTER_CAST = False 

# Словарь: Идентификатор -> (Комбинация сфер, Применять на себя)
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

# Расширенный словарь фраз (включая сленг и реплики героя)
PHRASES = {
    # Cold Snap
    "колд с нэп": "cold_snap", "холод": "cold_snap", "заморозка": "cold_snap",
    "стан": "cold_snap", "мороз": "cold_snap", "длительная дрожь": "cold_snap", "хрупкость льда": "cold_snap",
    
    # Ghost Walk
    "гост волк": "ghost_walk", "походка призрака": "ghost_walk", 
    "инвиз": "ghost_walk", "невидимость": "ghost_walk", "дух летаргии": "ghost_walk",
    
    # Ice Wall
    "айс вол": "ice_wall", "стенка": "ice_wall", "ледяная стена": "ice_wall", 
    "лед": "ice_wall", "бастион горести": "ice_wall", "белая пустошь": "ice_wall",
    
    # EMP
    "эмп": "emp", "и эм пи": "emp", "импульс": "emp", 
    "мана": "emp", "взрыв маны": "emp", "пульс шима ре": "emp",
    
    # Tornado
    "торнадо": "tornado", "ветра": "tornado", "ветер": "tornado", 
    "вихрь": "tornado", "мои враги парят": "tornado", "когти торна руса": "tornado",
    
    # Alacrity
    "ала кри ти": "alacrity", "ускорение": "alacrity", 
    "баф": "alacrity", "скорость": "alacrity", "истинная скорость": "alacrity", "алакрити":"alacrity",
    
    # Sun Strike
    "сан страйк": "sun_strike", "солнечный удар": "sun_strike", 
    "луч": "sun_strike", "удар сверху": "sun_strike", "экспорт трио нис": "sun_strike",
    
    # Forge Spirit
    "морж спирит": "forge_spirit", "форс спирит": "forge_spirit", "духи": "forge_spirit", 
    "голем": "forge_spirit", "суммоны": "forge_spirit", "элемент али горя": "forge_spirit", "форжи":"forge_spirit" ,
    "форджи": "forge_spirit",
    
    # Chaos Meteor
    "котлета": "chaos_meteor", "метеор": "chaos_meteor", "хаос метеор": "chaos_meteor", 
    "камень": "chaos_meteor", "огонь небес": "chaos_meteor", "небесное инферно": "chaos_meteor",
    
    # Deafening Blast
    "де фен инг бласт": "deafening_blast", "бласт": "deafening_blast", 
    "волна": "deafening_blast", "толчок": "deafening_blast", "звуковой бум": "deafening_blast",
    
    # Cataclysm
    "катаклизма": "cataclysm", "ката клизм": "cataclysm", "катаклизм": "cataclysm"
}
# =============================================

def human_sleep(base_delay, variance=0.008):
    """
    Создает случайную задержку на основе нормального распределения Гаусса.
    Это имитирует человеческую неидеальность при нажатии клавиш.
    """
    delay = random.gauss(base_delay, variance)
    # Гарантируем, что задержка не станет отрицательной или слишком маленькой
    time.sleep(max(0.015, delay))

def cast_spell(spell_id):
    if spell_id not in SPELLS: return
    combo, is_self_cast = SPELLS[spell_id]
    
    # 1. Нажимаем сферы (с плавающей задержкой)
    for orb in combo:
        keyboard.send(KEYS[orb.upper()])
        human_sleep(KEY_DELAY)
        
    # 2. Invoke
    keyboard.send(KEYS["INVOKE"])
    # Чуть больший разброс перед применением самой способности
    human_sleep(CAST_DELAY, 0.015)
    
    # 3. Каст
    if is_self_cast:
        # Alt нажимается отдельно для Cataclysm
        keyboard.press('alt')
        human_sleep(0.015, 0.003)
        keyboard.send(KEYS["SLOT1"])
        human_sleep(0.015, 0.003)
        keyboard.release('alt')
    else:
        keyboard.send(KEYS["SLOT1"])
        if CLICK_AFTER_CAST:
            human_sleep(CLICK_DELAY, 0.010)
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
        print("Ошибка: папка 'model' не найдена. Убедитесь, что скачали vosk-model-small-ru-0.22.")
        return

    # Ограничиваем словарь модели только нужными фразами
    vocab = list(PHRASES.keys())
    vocab_json = json.dumps(vocab + ["[unk]"], ensure_ascii=False)
    rec = KaldiRecognizer(model, 16000, vocab_json)

    print("✅ Голосовой каст готов! Микрофон слушается в реальном времени.")
    print("Нажмите Ctrl+C для выхода.")

    # Непрерывное прослушивание аудиопотока
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
                            print(f"[{time.strftime('%H:%M:%S')}] Услышано: '{phrase}' -> Каст: {spell_id}")
                            cast_spell(spell_id)
                            break 

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nВыход...")
