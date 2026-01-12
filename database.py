import sqlite3
import json
from datetime import datetime

DB_NAME = "nutri_bot.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabela de Usuários
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_seen TIMESTAMP
                )''')

    # Tabela de Refeições
    c.execute('''CREATE TABLE IF NOT EXISTS meals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    time TEXT,
                    summary TEXT,
                    calories INTEGER,
                    source TEXT,
                    is_carnivore BOOLEAN DEFAULT 0,
                    macros TEXT, -- JSON string
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    # Tabela de Notas de Voz
    c.execute('''CREATE TABLE IF NOT EXISTS voice_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    time TEXT,
                    transcription TEXT,
                    food_detected BOOLEAN,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    # Tabela de Metas
    c.execute('''CREATE TABLE IF NOT EXISTS goals (
                    user_id INTEGER PRIMARY KEY,
                    calories INTEGER,
                    protein INTEGER,
                    fat INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')
    
    conn.commit()
    conn.close()

def add_user(user_id, username=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen) VALUES (?, ?, ?)", 
                  (user_id, username, datetime.now()))
        conn.commit()
    finally:
        conn.close()

def set_goals(user_id, calories, protein, fat):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO goals (user_id, calories, protein, fat) VALUES (?, ?, ?, ?)",
                  (user_id, calories, protein, fat))
        conn.commit()
    finally:
        conn.close()

def get_goals(user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT calories, protein, fat FROM goals WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return {"calories": row[0], "protein": row[1], "fat": row[2]} if row else None
    finally:
        conn.close()

def add_meal(user_id, summary, calories, source, macros=None):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')
    
    # Simples verificação de "Carnivore" baseado no texto, pode ser melhorado sem AI
    is_carnivore = any(word in summary.lower() for word in ['carne', 'ovo', 'bacon', 'peixe', 'frango'])
    
    try:
        c.execute('''INSERT INTO meals (user_id, date, time, summary, calories, source, is_carnivore, macros)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, date_str, time_str, summary, calories, source, is_carnivore, json.dumps(macros) if macros else None))
        conn.commit()
    finally:
        conn.close()

def get_meals(user_id, date):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT time, summary, calories, source, is_carnivore, macros FROM meals WHERE user_id = ? AND date = ?", (user_id, date))
        meals = []
        for row in c.fetchall():
            macros = json.loads(row[5]) if row[5] else {}
            meals.append({
                "time": row[0], "summary": row[1], "calories": row[2], 
                "source": row[3], "is_carnivore": row[4], "macros": macros
            })
        return meals
    finally:
        conn.close()

def add_voice_note(user_id, transcription, food_detected):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')
    
    try:
        c.execute('''INSERT INTO voice_notes (user_id, date, time, transcription, food_detected)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, date_str, time_str, transcription, food_detected))
        conn.commit()
    finally:
        conn.close()

def get_voice_notes(user_id, date):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT time, transcription, food_detected FROM voice_notes WHERE user_id = ? AND date = ?", (user_id, date))
        return [{"time": row[0], "transcription": row[1], "food_detected": row[2]} for row in c.fetchall()]
    finally:
        conn.close()

# Inicializa ao importar
init_db()
