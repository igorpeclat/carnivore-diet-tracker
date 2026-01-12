import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_NAME = "carnivore_tracker.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_seen TIMESTAMP,
                    preferred_level TEXT DEFAULT 'strict'
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS meal_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    datetime TEXT,
                    ingredients TEXT,
                    quantities TEXT,
                    carnivore_level TEXT,
                    breaks_fast BOOLEAN,
                    warnings TEXT,
                    calories REAL DEFAULT 0,
                    protein_g REAL DEFAULT 0,
                    fat_g REAL DEFAULT 0,
                    carbs_g REAL DEFAULT 0,
                    summary TEXT,
                    source TEXT,
                    processing_level TEXT DEFAULT 'whole',
                    needs_confirmation BOOLEAN DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS fasting_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS symptom_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    datetime TEXT,
                    symptom_type TEXT,
                    severity INTEGER,
                    notes TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS weight_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    datetime TEXT,
                    weight_kg REAL,
                    notes TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS goals (
                    user_id INTEGER PRIMARY KEY,
                    calories INTEGER,
                    protein INTEGER,
                    fat INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS voice_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    time TEXT,
                    transcription TEXT,
                    food_detected BOOLEAN,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )''')
    
    conn.commit()
    conn.close()


def add_user(user_id: int, username: str = None, preferred_level: str = "strict"):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_seen, preferred_level) VALUES (?, ?, ?, ?)", 
            (user_id, username, datetime.now(), preferred_level)
        )
        conn.commit()
    finally:
        conn.close()


def get_user_preferred_level(user_id: int) -> str:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT preferred_level FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row else "strict"
    finally:
        conn.close()


def set_user_preferred_level(user_id: int, level: str):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET preferred_level = ? WHERE user_id = ?", (level, user_id))
        conn.commit()
    finally:
        conn.close()


def set_goals(user_id: int, calories: int, protein: int, fat: int):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR REPLACE INTO goals (user_id, calories, protein, fat) VALUES (?, ?, ?, ?)",
            (user_id, calories, protein, fat)
        )
        conn.commit()
    finally:
        conn.close()


def get_goals(user_id: int) -> Optional[Dict]:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT calories, protein, fat FROM goals WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return {"calories": row[0], "protein": row[1], "fat": row[2]} if row else None
    finally:
        conn.close()


# =============================================================================
# MEAL EVENTS
# =============================================================================

def add_meal_event(
    user_id: int,
    dt: datetime,
    ingredients: List[str],
    quantities: List[str],
    carnivore_level: str,
    breaks_fast: bool,
    warnings: List[str],
    calories: float = 0,
    protein_g: float = 0,
    fat_g: float = 0,
    carbs_g: float = 0,
    summary: str = "",
    source: str = "text",
    processing_level: str = "whole",
    needs_confirmation: bool = False
) -> int:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO meal_events 
                     (user_id, datetime, ingredients, quantities, carnivore_level, breaks_fast, 
                      warnings, calories, protein_g, fat_g, carbs_g, summary, source, 
                      processing_level, needs_confirmation)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, dt.isoformat(), json.dumps(ingredients), json.dumps(quantities),
                   carnivore_level, breaks_fast, json.dumps(warnings), calories, protein_g,
                   fat_g, carbs_g, summary, source, processing_level, needs_confirmation))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def get_meal_events(user_id: int, date: str) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''SELECT id, datetime, ingredients, quantities, carnivore_level, breaks_fast,
                            warnings, calories, protein_g, fat_g, carbs_g, summary, source,
                            processing_level, needs_confirmation
                     FROM meal_events 
                     WHERE user_id = ? AND datetime LIKE ?
                     ORDER BY datetime''', (user_id, f"{date}%"))
        meals = []
        for row in c.fetchall():
            meals.append({
                "id": row[0],
                "datetime": row[1],
                "time": row[1].split("T")[1][:5] if "T" in row[1] else row[1],
                "ingredients": json.loads(row[2]) if row[2] else [],
                "quantities": json.loads(row[3]) if row[3] else [],
                "carnivore_level": row[4],
                "breaks_fast": row[5],
                "warnings": json.loads(row[6]) if row[6] else [],
                "calories": row[7],
                "protein_g": row[8],
                "fat_g": row[9],
                "carbs_g": row[10],
                "summary": row[11],
                "source": row[12],
                "processing_level": row[13],
                "needs_confirmation": row[14],
            })
        return meals
    finally:
        conn.close()


def get_daily_stats(user_id: int, date: str) -> Dict:
    meals = get_meal_events(user_id, date)
    
    if not meals:
        return {
            "total_protein_g": 0,
            "total_fat_g": 0,
            "total_calories": 0,
            "meal_count": 0,
            "unique_ingredients": [],
            "first_meal_time": None,
            "last_meal_time": None,
            "carnivore_compliance": 100.0,
        }
    
    total_protein = sum(m["protein_g"] for m in meals)
    total_fat = sum(m["fat_g"] for m in meals)
    total_calories = sum(m["calories"] for m in meals)
    
    all_ingredients = []
    for m in meals:
        all_ingredients.extend(m["ingredients"])
    unique_ingredients = list(set(all_ingredients))
    
    strict_count = sum(1 for m in meals if m["carnivore_level"] == "strict")
    compliance = (strict_count / len(meals)) * 100 if meals else 100.0
    
    times = [m["time"] for m in meals if m["time"]]
    first_time = min(times) if times else None
    last_time = max(times) if times else None
    
    return {
        "total_protein_g": total_protein,
        "total_fat_g": total_fat,
        "total_calories": total_calories,
        "meal_count": len(meals),
        "unique_ingredients": unique_ingredients,
        "first_meal_time": first_time,
        "last_meal_time": last_time,
        "carnivore_compliance": compliance,
        "fat_protein_ratio": round(total_fat / total_protein, 2) if total_protein > 0 else None,
    }


# =============================================================================
# FASTING EVENTS (BACKLOG)
# =============================================================================

def start_fast(user_id: int, start_time: datetime) -> int:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO fasting_events (user_id, start_time) VALUES (?, ?)",
            (user_id, start_time.isoformat())
        )
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def end_fast(user_id: int, end_time: datetime) -> bool:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''UPDATE fasting_events SET end_time = ? 
               WHERE user_id = ? AND end_time IS NULL 
               ORDER BY start_time DESC LIMIT 1''',
            (end_time.isoformat(), user_id)
        )
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()


def get_active_fast(user_id: int) -> Optional[Dict]:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''SELECT id, start_time FROM fasting_events 
               WHERE user_id = ? AND end_time IS NULL 
               ORDER BY start_time DESC LIMIT 1''',
            (user_id,)
        )
        row = c.fetchone()
        if row:
            return {"id": row[0], "start_time": row[1]}
        return None
    finally:
        conn.close()


# =============================================================================
# SYMPTOM EVENTS (BACKLOG)
# =============================================================================

def add_symptom(user_id: int, dt: datetime, symptom_type: str, severity: int, notes: str = "") -> int:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO symptom_events (user_id, datetime, symptom_type, severity, notes) VALUES (?, ?, ?, ?, ?)",
            (user_id, dt.isoformat(), symptom_type, severity, notes)
        )
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def get_symptoms(user_id: int, date: str) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''SELECT id, datetime, symptom_type, severity, notes 
               FROM symptom_events WHERE user_id = ? AND datetime LIKE ?''',
            (user_id, f"{date}%")
        )
        return [
            {"id": r[0], "datetime": r[1], "symptom_type": r[2], "severity": r[3], "notes": r[4]}
            for r in c.fetchall()
        ]
    finally:
        conn.close()


# =============================================================================
# WEIGHT EVENTS (BACKLOG)
# =============================================================================

def add_weight(user_id: int, dt: datetime, weight_kg: float, notes: str = "") -> int:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO weight_events (user_id, datetime, weight_kg, notes) VALUES (?, ?, ?, ?)",
            (user_id, dt.isoformat(), weight_kg, notes)
        )
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def get_weight_history(user_id: int, limit: int = 30) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''SELECT id, datetime, weight_kg, notes FROM weight_events 
               WHERE user_id = ? ORDER BY datetime DESC LIMIT ?''',
            (user_id, limit)
        )
        return [{"id": r[0], "datetime": r[1], "weight_kg": r[2], "notes": r[3]} for r in c.fetchall()]
    finally:
        conn.close()


# =============================================================================
# METABOLIC STATS
# =============================================================================

def get_fasting_history(user_id: int, days: int = 30) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        c.execute(
            '''SELECT id, start_time, end_time FROM fasting_events 
               WHERE user_id = ? AND end_time IS NOT NULL AND start_time >= ?
               ORDER BY start_time DESC''',
            (user_id, cutoff)
        )
        fasts = []
        for r in c.fetchall():
            start = datetime.fromisoformat(r[1])
            end = datetime.fromisoformat(r[2])
            duration_hours = (end - start).total_seconds() / 3600
            fasts.append({
                "id": r[0],
                "start_time": r[1],
                "end_time": r[2],
                "duration_hours": round(duration_hours, 1)
            })
        return fasts
    finally:
        conn.close()


def get_symptoms_history(user_id: int, days: int = 30) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        c.execute(
            '''SELECT id, datetime, symptom_type, severity, notes 
               FROM symptom_events WHERE user_id = ? AND datetime >= ?
               ORDER BY datetime DESC''',
            (user_id, cutoff)
        )
        return [
            {"id": r[0], "datetime": r[1], "symptom_type": r[2], "severity": r[3], "notes": r[4]}
            for r in c.fetchall()
        ]
    finally:
        conn.close()


def get_meals_history(user_id: int, days: int = 30) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        c.execute(
            '''SELECT id, datetime, ingredients, carnivore_level, calories, protein_g, fat_g, carbs_g
               FROM meal_events WHERE user_id = ? AND datetime >= ?
               ORDER BY datetime DESC''',
            (user_id, cutoff)
        )
        meals = []
        for r in c.fetchall():
            meals.append({
                "id": r[0],
                "datetime": r[1],
                "ingredients": json.loads(r[2]) if r[2] else [],
                "carnivore_level": r[3],
                "calories": r[4],
                "protein_g": r[5],
                "fat_g": r[6],
                "carbs_g": r[7],
            })
        return meals
    finally:
        conn.close()


def get_user_start_date(user_id: int) -> Optional[str]:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT first_seen FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_metabolic_stats(user_id: int) -> Dict:
    meals = get_meals_history(user_id, 30)
    symptoms = get_symptoms_history(user_id, 30)
    fasts = get_fasting_history(user_id, 30)
    weights = get_weight_history(user_id, 30)
    start_date = get_user_start_date(user_id)
    
    days_on_protocol = 0
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00').split('+')[0])
            days_on_protocol = (datetime.now() - start_dt).days
        except (ValueError, TypeError):
            days_on_protocol = 0
    
    recent_meals = [m for m in meals if m['datetime'] >= (datetime.now() - timedelta(days=7)).isoformat()]
    
    if recent_meals:
        daily_totals: Dict[str, Dict] = {}
        for m in recent_meals:
            day = m['datetime'].split('T')[0]
            if day not in daily_totals:
                daily_totals[day] = {'protein': 0, 'fat': 0, 'calories': 0, 'count': 0}
            daily_totals[day]['protein'] += m['protein_g']
            daily_totals[day]['fat'] += m['fat_g']
            daily_totals[day]['calories'] += m['calories']
            daily_totals[day]['count'] += 1
        
        days_with_data = len(daily_totals)
        total_protein = sum(d['protein'] for d in daily_totals.values())
        total_fat = sum(d['fat'] for d in daily_totals.values())
        total_calories = sum(d['calories'] for d in daily_totals.values())
        
        avg_daily_protein = round(total_protein / days_with_data, 1) if days_with_data else 0
        avg_daily_fat = round(total_fat / days_with_data, 1) if days_with_data else 0
        avg_daily_calories = round(total_calories / days_with_data, 0) if days_with_data else 0
        avg_fat_protein_ratio = round(avg_daily_fat / avg_daily_protein, 2) if avg_daily_protein > 0 else 0
    else:
        avg_daily_protein = 0
        avg_daily_fat = 0
        avg_daily_calories = 0
        avg_fat_protein_ratio = 0
    
    if meals:
        strict_meals = sum(1 for m in meals if m['carnivore_level'] == 'strict')
        carnivore_compliance = round((strict_meals / len(meals)) * 100, 1)
    else:
        carnivore_compliance = 100.0
    
    if fasts:
        fasting_frequency = round(len(fasts) / 4.3, 1)
        avg_fasting_duration = round(sum(f['duration_hours'] for f in fasts) / len(fasts), 1)
    else:
        fasting_frequency = 0
        avg_fasting_duration = 0
    
    electrolyte_symptoms = ['dizziness', 'weakness', 'cramps', 'headache']
    energy_symptoms = ['high_energy', 'low_energy', 'brain_fog']
    
    if symptoms:
        symptom_frequency = round(len(symptoms) / 4.3, 1)
        
        symptom_counts: Dict[str, int] = {}
        electrolyte_symptom_count = 0
        recent_energy_scores: List[int] = []
        
        for s in symptoms:
            stype = s['symptom_type']
            symptom_counts[stype] = symptom_counts.get(stype, 0) + 1
            
            if stype in electrolyte_symptoms:
                electrolyte_symptom_count += s['severity']
            
            if stype in energy_symptoms:
                if stype == 'high_energy':
                    recent_energy_scores.append(s['severity'])
                else:
                    recent_energy_scores.append(-s['severity'])
        
        common_symptoms = sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        common_symptoms = [s[0] for s in common_symptoms]
        
        if electrolyte_symptom_count > 15:
            electrolyte_risk = "high"
        elif electrolyte_symptom_count > 5:
            electrolyte_risk = "medium"
        else:
            electrolyte_risk = "low"
        
        if recent_energy_scores:
            avg_energy = sum(recent_energy_scores) / len(recent_energy_scores)
            if avg_energy > 1:
                energy_trend = "improving"
            elif avg_energy < -1:
                energy_trend = "declining"
            else:
                energy_trend = "stable"
        else:
            energy_trend = "unknown"
    else:
        symptom_frequency = 0
        common_symptoms = []
        electrolyte_risk = "low"
        energy_trend = "unknown"
    
    if len(weights) >= 2:
        recent_weight = weights[0]['weight_kg']
        oldest_weight = weights[-1]['weight_kg']
        weight_change = round(recent_weight - oldest_weight, 1)
        
        if weight_change < -0.5:
            weight_trend = f"losing ({weight_change:+.1f} kg)"
        elif weight_change > 0.5:
            weight_trend = f"gaining ({weight_change:+.1f} kg)"
        else:
            weight_trend = "stable"
    else:
        weight_trend = "insufficient data"
    
    keto_score = 0
    
    if days_on_protocol >= 30:
        keto_score += 30
    elif days_on_protocol >= 14:
        keto_score += 20
    elif days_on_protocol >= 7:
        keto_score += 10
    else:
        keto_score += days_on_protocol
    
    keto_score += int(carnivore_compliance * 0.25)
    
    if 0.8 <= avg_fat_protein_ratio <= 2.0:
        keto_score += 20
    elif 0.5 <= avg_fat_protein_ratio <= 2.5:
        keto_score += 10
    
    if electrolyte_risk == "low":
        keto_score += 15
    elif electrolyte_risk == "medium":
        keto_score += 7
    
    if avg_fasting_duration >= 16:
        keto_score += 10
    elif avg_fasting_duration >= 12:
        keto_score += 5
    
    keto_adaptation_score = min(100, keto_score)
    
    return {
        "keto_adaptation_score": keto_adaptation_score,
        "keto_adaptation_label": _get_keto_label(keto_adaptation_score),
        "electrolyte_risk": electrolyte_risk,
        "energy_trend": energy_trend,
        "days_on_protocol": days_on_protocol,
        "avg_daily_protein": avg_daily_protein,
        "avg_daily_fat": avg_daily_fat,
        "avg_daily_calories": avg_daily_calories,
        "avg_fat_protein_ratio": avg_fat_protein_ratio,
        "fasting_frequency": fasting_frequency,
        "avg_fasting_duration": avg_fasting_duration,
        "symptom_frequency": symptom_frequency,
        "common_symptoms": common_symptoms,
        "weight_trend": weight_trend,
        "carnivore_compliance": carnivore_compliance,
    }


def _get_keto_label(score: int) -> str:
    if score >= 80:
        return "Likely Fat-Adapted"
    elif score >= 60:
        return "Adapting Well"
    elif score >= 40:
        return "Early Adaptation"
    elif score >= 20:
        return "Beginning Transition"
    else:
        return "Not Yet Adapted"


def get_weekly_summary(user_id: int) -> Dict:
    meals = get_meals_history(user_id, 7)
    symptoms = get_symptoms_history(user_id, 7)
    fasts = get_fasting_history(user_id, 7)
    weights = get_weight_history(user_id, 7)
    
    daily_breakdown: Dict[str, Dict] = {}
    for m in meals:
        day = m['datetime'].split('T')[0]
        if day not in daily_breakdown:
            daily_breakdown[day] = {'calories': 0, 'protein': 0, 'fat': 0, 'meals': 0, 'strict': 0}
        daily_breakdown[day]['calories'] += m['calories']
        daily_breakdown[day]['protein'] += m['protein_g']
        daily_breakdown[day]['fat'] += m['fat_g']
        daily_breakdown[day]['meals'] += 1
        if m['carnivore_level'] == 'strict':
            daily_breakdown[day]['strict'] += 1
    
    days_with_data = len(daily_breakdown)
    total_meals = sum(d['meals'] for d in daily_breakdown.values())
    total_strict = sum(d['strict'] for d in daily_breakdown.values())
    total_calories = sum(d['calories'] for d in daily_breakdown.values())
    total_protein = sum(d['protein'] for d in daily_breakdown.values())
    total_fat = sum(d['fat'] for d in daily_breakdown.values())
    
    symptom_counts: Dict[str, int] = {}
    for s in symptoms:
        stype = s['symptom_type']
        symptom_counts[stype] = symptom_counts.get(stype, 0) + 1
    
    total_fasting_hours = sum(f['duration_hours'] for f in fasts)
    
    weight_change = 0.0
    if len(weights) >= 2:
        weight_change = weights[0]['weight_kg'] - weights[-1]['weight_kg']
    
    return {
        "days_tracked": days_with_data,
        "total_meals": total_meals,
        "total_calories": round(total_calories, 0),
        "total_protein": round(total_protein, 0),
        "total_fat": round(total_fat, 0),
        "avg_daily_calories": round(total_calories / days_with_data, 0) if days_with_data else 0,
        "avg_daily_protein": round(total_protein / days_with_data, 0) if days_with_data else 0,
        "avg_daily_fat": round(total_fat / days_with_data, 0) if days_with_data else 0,
        "compliance": round((total_strict / total_meals) * 100, 1) if total_meals else 100.0,
        "fasts_completed": len(fasts),
        "total_fasting_hours": round(total_fasting_hours, 1),
        "symptoms_logged": len(symptoms),
        "top_symptoms": sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:3],
        "weight_change": round(weight_change, 1),
        "daily_breakdown": daily_breakdown,
    }


# =============================================================================
# VOICE NOTES (legacy compatibility)
# =============================================================================

def add_voice_note(user_id: int, transcription: str, food_detected: bool):
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


def get_voice_notes(user_id: int, date: str) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "SELECT time, transcription, food_detected FROM voice_notes WHERE user_id = ? AND date = ?",
            (user_id, date)
        )
        return [{"time": row[0], "transcription": row[1], "food_detected": row[2]} for row in c.fetchall()]
    finally:
        conn.close()


# =============================================================================
# LEGACY COMPATIBILITY (for existing bot.py until migrated)
# =============================================================================

def add_meal(user_id: int, summary: str, calories: int, source: str, macros: Dict = None):
    now = datetime.now()
    protein = macros.get("protein", 0) if macros else 0
    fat = macros.get("fat", 0) if macros else 0
    
    add_meal_event(
        user_id=user_id,
        dt=now,
        ingredients=[],
        quantities=[],
        carnivore_level="strict",
        breaks_fast=True,
        warnings=[],
        calories=calories,
        protein_g=protein,
        fat_g=fat,
        carbs_g=macros.get("carbs", 0) if macros else 0,
        summary=summary,
        source=source,
    )


def get_meals(user_id: int, date: str) -> List[Dict]:
    meals = get_meal_events(user_id, date)
    return [
        {
            "time": m["time"],
            "summary": m["summary"],
            "calories": m["calories"],
            "source": m["source"],
            "is_carnivore": m["carnivore_level"] != "not_carnivore",
            "macros": {"protein": m["protein_g"], "fat": m["fat_g"], "carbs": m["carbs_g"]},
        }
        for m in meals
    ]


init_db()
