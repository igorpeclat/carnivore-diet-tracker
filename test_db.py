import database
from datetime import datetime
import os

# Clean up previous test
if os.path.exists("nutri_bot.db"):
    os.remove("nutri_bot.db")

print("Initializing DB...")
database.init_db()

user_id = 12345
print(f"Adding user {user_id}...")
database.add_user(user_id, "test_user")

print("Adding meal...")
database.add_meal(user_id, "3 ovos e bacon", 500, "text")

print("Adding voice note...")
database.add_voice_note(user_id, "Comi carne moida", True)

today = datetime.now().strftime('%Y-%m-%d')
print(f"Retrieving data for {today}...")

meals = database.get_meals(user_id, today)
print("Meals:", meals)

notes = database.get_voice_notes(user_id, today)
print("Notes:", notes)

if len(meals) == 1 and meals[0]['is_carnivore']:
    print("SUCCESS: Meal saved and identified as carnivore!")
else:
    print("FAILURE: Meal check failed.")

if len(notes) == 1:
    print("SUCCESS: Note saved!")
else:
    print("FAILURE: Note check failed.")
