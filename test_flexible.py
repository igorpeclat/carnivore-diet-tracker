import database
import json
from datetime import datetime
import os

# Reset DB
if os.path.exists("nutri_bot.db"):
    os.remove("nutri_bot.db")
database.init_db()

user_id = 222
database.add_user(user_id, "NoGoalsUser")

# Ensure no goals set
goals = database.get_goals(user_id)
assert goals is None

# Add meal
database.add_meal(user_id, "Ovos Mexidos", 300, "text", macros={"protein": 20, "fat": 25})

# Get stats directly simulates what stats_command does (logic wise)
today = datetime.now().strftime('%Y-%m-%d')
meals = database.get_meals(user_id, today)
total_kcal = sum(m['calories'] for m in meals)

print(f"User without goals consumed: {total_kcal} kcal")
assert total_kcal == 300

print("SUCCESS: Flexible goals logic verified.")
