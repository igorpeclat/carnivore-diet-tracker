import database
import json
from datetime import datetime

# Reset DB for test
import os
if os.path.exists("nutri_bot.db"):
    os.remove("nutri_bot.db")
database.init_db()

user_id = 111
print("Setting goals...")
database.set_goals(user_id, 2000, 150, 120)

goals = database.get_goals(user_id)
print(f"Goals: {goals}")
assert goals['calories'] == 2000
assert goals['protein'] == 150

print("Adding meal with macros...")
macros = {"protein": 50, "fat": 40}
database.add_meal(user_id, "Bife com ovo", 600, "text", macros=macros)

today = datetime.now().strftime('%Y-%m-%d')
meals = database.get_meals(user_id, today)
print(f"Meals: {meals}")

total_prot = sum(m['macros'].get('protein', 0) for m in meals)
print(f"Total Protein: {total_prot}")
assert total_prot == 50

print("SUCCESS: Goals and Stats logic verified in DB.")
