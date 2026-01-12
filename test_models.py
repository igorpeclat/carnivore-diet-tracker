import pytest
from datetime import datetime, timedelta
from models import (
    MealEvent,
    FastingEvent,
    SymptomEvent,
    WeightEvent,
    DailyStats,
    SymptomType,
    EventSource,
)
from carnivore_core import CarnivoreLevel


class TestMealEvent:
    def test_create_meal_event(self):
        meal = MealEvent(
            user_id=123,
            datetime=datetime.now(),
            ingredients=["beef", "eggs"],
            quantities=["200g", "2"],
            carnivore_level=CarnivoreLevel.STRICT,
            breaks_fast=True,
            warnings=[],
            calories=600,
            protein_g=50,
            fat_g=40,
        )
        
        assert meal.user_id == 123
        assert meal.calories == 600
        assert len(meal.ingredients) == 2
    
    def test_fat_protein_ratio(self):
        meal = MealEvent(
            user_id=123,
            datetime=datetime.now(),
            ingredients=["beef"],
            quantities=["200g"],
            carnivore_level=CarnivoreLevel.STRICT,
            breaks_fast=True,
            warnings=[],
            protein_g=100,
            fat_g=80,
        )
        
        assert meal.fat_protein_ratio == 0.8
    
    def test_fat_protein_ratio_zero_protein(self):
        meal = MealEvent(
            user_id=123,
            datetime=datetime.now(),
            ingredients=["butter"],
            quantities=["50g"],
            carnivore_level=CarnivoreLevel.RELAXED,
            breaks_fast=True,
            warnings=[],
            protein_g=0,
            fat_g=40,
        )
        
        assert meal.fat_protein_ratio is None
    
    def test_to_dict(self):
        now = datetime.now()
        meal = MealEvent(
            user_id=123,
            datetime=now,
            ingredients=["salmon"],
            quantities=["150g"],
            carnivore_level=CarnivoreLevel.STRICT,
            breaks_fast=True,
            warnings=["test warning"],
            calories=300,
            protein_g=30,
            fat_g=20,
            summary="Salmon fillet",
            source=EventSource.PHOTO,
        )
        
        d = meal.to_dict()
        
        assert d["user_id"] == 123
        assert d["carnivore_level"] == "strict"
        assert d["source"] == "photo"
        assert d["warnings"] == ["test warning"]
    
    def test_from_dict(self):
        data = {
            "id": 1,
            "user_id": 456,
            "datetime": "2025-01-12T10:30:00",
            "ingredients": ["eggs", "bacon"],
            "quantities": ["3", "100g"],
            "carnivore_level": "relaxed",
            "breaks_fast": True,
            "warnings": [],
            "calories": 400,
            "protein_g": 25,
            "fat_g": 30,
            "carbs_g": 0,
            "summary": "Breakfast",
            "source": "voice",
        }
        
        meal = MealEvent.from_dict(data)
        
        assert meal.user_id == 456
        assert meal.carnivore_level == CarnivoreLevel.RELAXED
        assert meal.source == EventSource.VOICE
        assert len(meal.ingredients) == 2


class TestFastingEvent:
    def test_create_fasting_event(self):
        fast = FastingEvent(
            user_id=123,
            start_time=datetime.now(),
        )
        
        assert fast.user_id == 123
        assert fast.is_active is True
        assert fast.end_time is None
    
    def test_fasting_duration(self):
        start = datetime(2025, 1, 12, 20, 0)
        end = datetime(2025, 1, 13, 12, 0)
        
        fast = FastingEvent(
            user_id=123,
            start_time=start,
            end_time=end,
        )
        
        assert fast.duration_hours == 16.0
        assert fast.is_active is False
    
    def test_duration_active_fast(self):
        fast = FastingEvent(
            user_id=123,
            start_time=datetime.now(),
        )
        
        assert fast.duration_hours is None
    
    def test_to_dict(self):
        start = datetime(2025, 1, 12, 20, 0)
        end = datetime(2025, 1, 13, 12, 0)
        
        fast = FastingEvent(
            user_id=123,
            start_time=start,
            end_time=end,
            id=5,
        )
        
        d = fast.to_dict()
        
        assert d["id"] == 5
        assert d["duration_hours"] == 16.0
        assert d["end_time"] is not None


class TestSymptomEvent:
    def test_create_symptom_event(self):
        symptom = SymptomEvent(
            user_id=123,
            datetime=datetime.now(),
            symptom_type=SymptomType.DIZZINESS,
            severity=3,
            notes="After standing up quickly",
        )
        
        assert symptom.severity == 3
        assert symptom.symptom_type == SymptomType.DIZZINESS
    
    def test_severity_validation_valid(self):
        for sev in range(1, 6):
            symptom = SymptomEvent(
                user_id=123,
                datetime=datetime.now(),
                symptom_type=SymptomType.HEADACHE,
                severity=sev,
            )
            assert symptom.severity == sev
    
    def test_severity_validation_too_low(self):
        with pytest.raises(ValueError):
            SymptomEvent(
                user_id=123,
                datetime=datetime.now(),
                symptom_type=SymptomType.HEADACHE,
                severity=0,
            )
    
    def test_severity_validation_too_high(self):
        with pytest.raises(ValueError):
            SymptomEvent(
                user_id=123,
                datetime=datetime.now(),
                symptom_type=SymptomType.HEADACHE,
                severity=6,
            )
    
    def test_to_dict(self):
        now = datetime.now()
        symptom = SymptomEvent(
            user_id=123,
            datetime=now,
            symptom_type=SymptomType.CRAMPS,
            severity=4,
            notes="Leg cramps",
            id=10,
        )
        
        d = symptom.to_dict()
        
        assert d["symptom_type"] == "cramps"
        assert d["severity"] == 4
        assert d["notes"] == "Leg cramps"


class TestWeightEvent:
    def test_create_weight_event(self):
        weight = WeightEvent(
            user_id=123,
            datetime=datetime.now(),
            weight_kg=85.5,
            notes="Morning weight",
        )
        
        assert weight.weight_kg == 85.5
    
    def test_to_dict(self):
        now = datetime.now()
        weight = WeightEvent(
            user_id=123,
            datetime=now,
            weight_kg=82.3,
            id=15,
        )
        
        d = weight.to_dict()
        
        assert d["weight_kg"] == 82.3
        assert d["id"] == 15


class TestDailyStats:
    def test_create_daily_stats(self):
        stats = DailyStats(
            date="2025-01-12",
            total_protein_g=150,
            total_fat_g=120,
            total_calories=1800,
            meal_count=3,
        )
        
        assert stats.total_calories == 1800
        assert stats.meal_count == 3
    
    def test_fat_protein_ratio(self):
        stats = DailyStats(
            date="2025-01-12",
            total_protein_g=150,
            total_fat_g=120,
        )
        
        assert stats.fat_protein_ratio == 0.8
    
    def test_fat_protein_ratio_zero_protein(self):
        stats = DailyStats(
            date="2025-01-12",
            total_protein_g=0,
            total_fat_g=50,
        )
        
        assert stats.fat_protein_ratio is None
    
    def test_default_values(self):
        stats = DailyStats(date="2025-01-12")
        
        assert stats.total_calories == 0
        assert stats.meal_count == 0
        assert stats.fasting_hours == 0
        assert stats.carnivore_compliance == 100.0
        assert stats.unique_ingredients == []


class TestEnums:
    def test_symptom_types(self):
        assert SymptomType.DIZZINESS.value == "dizziness"
        assert SymptomType.HIGH_ENERGY.value == "high_energy"
        assert SymptomType.BRAIN_FOG.value == "brain_fog"
    
    def test_event_sources(self):
        assert EventSource.VOICE.value == "voice"
        assert EventSource.PHOTO.value == "photo"
        assert EventSource.TEXT.value == "text"
        assert EventSource.MANUAL.value == "manual"
    
    def test_carnivore_levels(self):
        assert CarnivoreLevel.STRICT.value == "strict"
        assert CarnivoreLevel.RELAXED.value == "relaxed"
        assert CarnivoreLevel.DIRTY.value == "dirty"
        assert CarnivoreLevel.NOT_CARNIVORE.value == "not_carnivore"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
