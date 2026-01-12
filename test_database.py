import pytest
import os
from datetime import datetime, timedelta

DB_TEST_NAME = "test_carnivore_tracker.db"

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    import database
    monkeypatch.setattr(database, "DB_NAME", DB_TEST_NAME)
    
    if os.path.exists(DB_TEST_NAME):
        os.remove(DB_TEST_NAME)
    
    database.init_db()
    yield
    
    if os.path.exists(DB_TEST_NAME):
        os.remove(DB_TEST_NAME)


class TestUserOperations:
    def test_add_user(self):
        import database
        database.add_user(123, "testuser", "strict")
        level = database.get_user_preferred_level(123)
        assert level == "strict"
    
    def test_add_user_default_level(self):
        import database
        database.add_user(124, "testuser2")
        level = database.get_user_preferred_level(124)
        assert level == "strict"
    
    def test_set_user_level(self):
        import database
        database.add_user(125, "testuser3")
        database.set_user_preferred_level(125, "relaxed")
        level = database.get_user_preferred_level(125)
        assert level == "relaxed"
    
    def test_get_level_nonexistent_user(self):
        import database
        level = database.get_user_preferred_level(99999)
        assert level == "strict"


class TestGoals:
    def test_set_and_get_goals(self):
        import database
        database.add_user(200, "goaluser")
        database.set_goals(200, 2000, 150, 120)
        goals = database.get_goals(200)
        
        assert goals is not None
        assert goals["calories"] == 2000
        assert goals["protein"] == 150
        assert goals["fat"] == 120
    
    def test_get_goals_nonexistent(self):
        import database
        goals = database.get_goals(99999)
        assert goals is None
    
    def test_update_goals(self):
        import database
        database.add_user(201, "goaluser2")
        database.set_goals(201, 2000, 150, 120)
        database.set_goals(201, 2500, 180, 140)
        goals = database.get_goals(201)
        
        assert goals["calories"] == 2500
        assert goals["protein"] == 180


class TestMealEvents:
    def test_add_meal_event(self):
        import database
        database.add_user(300, "mealuser")
        
        meal_id = database.add_meal_event(
            user_id=300,
            dt=datetime.now(),
            ingredients=["beef", "eggs"],
            quantities=["200g", "2 units"],
            carnivore_level="strict",
            breaks_fast=True,
            warnings=[],
            calories=600,
            protein_g=50,
            fat_g=45,
            carbs_g=0,
            summary="Beef and eggs",
            source="text",
        )
        
        assert meal_id is not None
        assert meal_id > 0
    
    def test_get_meal_events(self):
        import database
        database.add_user(301, "mealuser2")
        now = datetime.now()
        
        database.add_meal_event(
            user_id=301,
            dt=now,
            ingredients=["salmon"],
            quantities=["150g"],
            carnivore_level="strict",
            breaks_fast=True,
            warnings=[],
            calories=350,
            protein_g=35,
            fat_g=20,
            summary="Salmon",
            source="photo",
        )
        
        today = now.strftime('%Y-%m-%d')
        meals = database.get_meal_events(301, today)
        
        assert len(meals) == 1
        assert meals[0]["ingredients"] == ["salmon"]
        assert meals[0]["calories"] == 350
        assert meals[0]["source"] == "photo"
    
    def test_get_meals_different_dates(self):
        import database
        database.add_user(302, "mealuser3")
        
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        database.add_meal_event(
            user_id=302, dt=today, ingredients=["beef"], quantities=["100g"],
            carnivore_level="strict", breaks_fast=True, warnings=[], calories=300,
            summary="Today meal", source="text",
        )
        database.add_meal_event(
            user_id=302, dt=yesterday, ingredients=["eggs"], quantities=["3"],
            carnivore_level="strict", breaks_fast=True, warnings=[], calories=200,
            summary="Yesterday meal", source="text",
        )
        
        today_meals = database.get_meal_events(302, today.strftime('%Y-%m-%d'))
        yesterday_meals = database.get_meal_events(302, yesterday.strftime('%Y-%m-%d'))
        
        assert len(today_meals) == 1
        assert len(yesterday_meals) == 1
        assert today_meals[0]["summary"] == "Today meal"
        assert yesterday_meals[0]["summary"] == "Yesterday meal"


class TestDailyStats:
    def test_daily_stats_with_meals(self):
        import database
        database.add_user(400, "statsuser")
        now = datetime.now()
        
        database.add_meal_event(
            user_id=400, dt=now, ingredients=["beef"], quantities=["200g"],
            carnivore_level="strict", breaks_fast=True, warnings=[],
            calories=500, protein_g=50, fat_g=35, summary="Beef", source="text",
        )
        database.add_meal_event(
            user_id=400, dt=now + timedelta(minutes=30), ingredients=["eggs"], quantities=["4"],
            carnivore_level="strict", breaks_fast=True, warnings=[],
            calories=300, protein_g=24, fat_g=20, summary="Eggs", source="text",
        )
        
        stats = database.get_daily_stats(400, now.strftime('%Y-%m-%d'))
        
        assert stats["total_calories"] == 800
        assert stats["total_protein_g"] == 74
        assert stats["total_fat_g"] == 55
        assert stats["meal_count"] == 2
        assert stats["carnivore_compliance"] == 100.0
    
    def test_daily_stats_empty(self):
        import database
        database.add_user(401, "emptyuser")
        stats = database.get_daily_stats(401, datetime.now().strftime('%Y-%m-%d'))
        
        assert stats["total_calories"] == 0
        assert stats["meal_count"] == 0
        assert stats["carnivore_compliance"] == 100.0
    
    def test_daily_stats_compliance(self):
        import database
        database.add_user(402, "complianceuser")
        now = datetime.now()
        
        database.add_meal_event(
            user_id=402, dt=now, ingredients=["beef"], quantities=["200g"],
            carnivore_level="strict", breaks_fast=True, warnings=[],
            calories=500, summary="Beef", source="text",
        )
        database.add_meal_event(
            user_id=402, dt=now + timedelta(minutes=30), ingredients=["beef", "rice"], quantities=["200g", "100g"],
            carnivore_level="not_carnivore", breaks_fast=True, warnings=["rice is forbidden"],
            calories=700, summary="Beef with rice", source="text",
        )
        
        stats = database.get_daily_stats(402, now.strftime('%Y-%m-%d'))
        assert stats["carnivore_compliance"] == 50.0


class TestFastingEvents:
    def test_start_and_end_fast(self):
        import database
        database.add_user(500, "fastuser")
        start = datetime.now()
        
        fast_id = database.start_fast(500, start)
        assert fast_id > 0
        
        active = database.get_active_fast(500)
        assert active is not None
        assert active["id"] == fast_id
        
        end = start + timedelta(hours=16)
        success = database.end_fast(500, end)
        assert success
        
        active = database.get_active_fast(500)
        assert active is None
    
    def test_no_active_fast(self):
        import database
        database.add_user(501, "nofastuser")
        active = database.get_active_fast(501)
        assert active is None
    
    def test_fasting_history(self):
        import database
        database.add_user(502, "fasthistoryuser")
        
        start1 = datetime.now() - timedelta(days=2)
        database.start_fast(502, start1)
        database.end_fast(502, start1 + timedelta(hours=16))
        
        start2 = datetime.now() - timedelta(days=1)
        database.start_fast(502, start2)
        database.end_fast(502, start2 + timedelta(hours=18))
        
        history = database.get_fasting_history(502, 7)
        assert len(history) == 2
        assert history[0]["duration_hours"] == 18.0
        assert history[1]["duration_hours"] == 16.0


class TestSymptomEvents:
    def test_add_symptom(self):
        import database
        database.add_user(600, "symptomuser")
        now = datetime.now()
        
        symptom_id = database.add_symptom(600, now, "dizziness", 3, "After standing up")
        assert symptom_id > 0
    
    def test_get_symptoms(self):
        import database
        database.add_user(601, "symptomuser2")
        now = datetime.now()
        
        database.add_symptom(601, now, "headache", 4)
        database.add_symptom(601, now + timedelta(hours=1), "weakness", 2)
        
        symptoms = database.get_symptoms(601, now.strftime('%Y-%m-%d'))
        assert len(symptoms) == 2
        
        types = [s["symptom_type"] for s in symptoms]
        assert "headache" in types
        assert "weakness" in types
    
    def test_symptoms_history(self):
        import database
        database.add_user(602, "symptomhistoryuser")
        
        for i in range(5):
            dt = datetime.now() - timedelta(days=i)
            database.add_symptom(602, dt, "cramps", 2 + i % 3)
        
        history = database.get_symptoms_history(602, 30)
        assert len(history) == 5


class TestWeightEvents:
    def test_add_weight(self):
        import database
        database.add_user(700, "weightuser")
        now = datetime.now()
        
        weight_id = database.add_weight(700, now, 85.5, "Morning weight")
        assert weight_id > 0
    
    def test_weight_history(self):
        import database
        database.add_user(701, "weighthistoryuser")
        
        for i in range(10):
            dt = datetime.now() - timedelta(days=i)
            database.add_weight(701, dt, 85.0 - i * 0.1)
        
        history = database.get_weight_history(701, 30)
        assert len(history) == 10
        assert history[0]["weight_kg"] == 85.0
        assert history[9]["weight_kg"] == 84.1


class TestMetabolicStats:
    def test_metabolic_stats_comprehensive(self):
        import database
        database.add_user(800, "metabolicuser")
        now = datetime.now()
        
        for i in range(7):
            dt = now - timedelta(days=i)
            database.add_meal_event(
                user_id=800, dt=dt, ingredients=["beef"], quantities=["200g"],
                carnivore_level="strict", breaks_fast=True, warnings=[],
                calories=500, protein_g=50, fat_g=35, summary="Beef", source="text",
            )
        
        for i in range(3):
            dt = now - timedelta(days=i * 2)
            database.add_symptom(800, dt, "dizziness", 2)
        
        start = now - timedelta(days=3)
        database.start_fast(800, start)
        database.end_fast(800, start + timedelta(hours=16))
        
        database.add_weight(800, now, 85.0)
        database.add_weight(800, now - timedelta(days=7), 86.0)
        
        stats = database.get_metabolic_stats(800)
        
        assert "keto_adaptation_score" in stats
        assert "electrolyte_risk" in stats
        assert "energy_trend" in stats
        assert "carnivore_compliance" in stats
        assert stats["carnivore_compliance"] == 100.0
    
    def test_metabolic_stats_empty(self):
        import database
        database.add_user(801, "emptymetabolicuser")
        
        stats = database.get_metabolic_stats(801)
        
        assert stats["keto_adaptation_score"] >= 0
        assert stats["electrolyte_risk"] == "low"


class TestWeeklySummary:
    def test_weekly_summary(self):
        import database
        database.add_user(900, "weeklyuser")
        now = datetime.now()
        
        for i in range(5):
            dt = now - timedelta(days=i)
            database.add_meal_event(
                user_id=900, dt=dt, ingredients=["beef"], quantities=["200g"],
                carnivore_level="strict", breaks_fast=True, warnings=[],
                calories=500, protein_g=50, fat_g=35, summary=f"Day {i}", source="text",
            )
        
        summary = database.get_weekly_summary(900)
        
        assert summary["days_tracked"] == 5
        assert summary["total_meals"] == 5
        assert summary["total_calories"] == 2500
        assert summary["compliance"] == 100.0


class TestLegacyCompatibility:
    def test_legacy_add_meal(self):
        import database
        database.add_user(1000, "legacyuser")
        
        database.add_meal(1000, "Steak dinner", 600, "text", {"protein": 50, "fat": 40})
        
        today = datetime.now().strftime('%Y-%m-%d')
        meals = database.get_meals(1000, today)
        
        assert len(meals) == 1
        assert meals[0]["summary"] == "Steak dinner"
        assert meals[0]["calories"] == 600
        assert meals[0]["macros"]["protein"] == 50
    
    def test_legacy_get_meals(self):
        import database
        database.add_user(1001, "legacyuser2")
        now = datetime.now()
        
        database.add_meal_event(
            user_id=1001, dt=now, ingredients=["salmon"], quantities=["150g"],
            carnivore_level="strict", breaks_fast=True, warnings=[],
            calories=350, protein_g=35, fat_g=20, carbs_g=0,
            summary="Salmon fillet", source="photo",
        )
        
        meals = database.get_meals(1001, now.strftime('%Y-%m-%d'))
        
        assert len(meals) == 1
        assert meals[0]["is_carnivore"] is True
        assert meals[0]["macros"]["protein"] == 35


class TestVoiceNotes:
    def test_add_voice_note(self):
        import database
        database.add_user(1100, "voiceuser")
        
        database.add_voice_note(1100, "I ate some steak", True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        notes = database.get_voice_notes(1100, today)
        
        assert len(notes) == 1
        assert notes[0]["transcription"] == "I ate some steak"
        assert notes[0]["food_detected"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
