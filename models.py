from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum
from carnivore_core import CarnivoreLevel


class SymptomType(Enum):
    DIZZINESS = "dizziness"
    WEAKNESS = "weakness"
    HEADACHE = "headache"
    CRAMPS = "cramps"
    DIARRHEA = "diarrhea"
    CONSTIPATION = "constipation"
    BRAIN_FOG = "brain_fog"
    NAUSEA = "nausea"
    HIGH_ENERGY = "high_energy"
    LOW_ENERGY = "low_energy"


class EventSource(Enum):
    VOICE = "voice"
    PHOTO = "photo"
    TEXT = "text"
    MANUAL = "manual"


@dataclass
class MealEvent:
    user_id: int
    datetime: datetime
    ingredients: List[str]
    quantities: List[str]
    carnivore_level: CarnivoreLevel
    breaks_fast: bool
    warnings: List[str]
    calories: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carbs_g: float = 0
    summary: str = ""
    source: EventSource = EventSource.TEXT
    processing_level: str = "whole"
    needs_confirmation: bool = False
    id: Optional[int] = None
    
    @property
    def fat_protein_ratio(self) -> Optional[float]:
        if self.protein_g == 0:
            return None
        return round(self.fat_g / self.protein_g, 2)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "datetime": self.datetime.isoformat(),
            "ingredients": self.ingredients,
            "quantities": self.quantities,
            "carnivore_level": self.carnivore_level.value,
            "breaks_fast": self.breaks_fast,
            "warnings": self.warnings,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "fat_g": self.fat_g,
            "carbs_g": self.carbs_g,
            "summary": self.summary,
            "source": self.source.value,
            "processing_level": self.processing_level,
            "needs_confirmation": self.needs_confirmation,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MealEvent":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            datetime=datetime.fromisoformat(data["datetime"]),
            ingredients=data.get("ingredients", []),
            quantities=data.get("quantities", []),
            carnivore_level=CarnivoreLevel(data.get("carnivore_level", "strict")),
            breaks_fast=data.get("breaks_fast", True),
            warnings=data.get("warnings", []),
            calories=data.get("calories", 0),
            protein_g=data.get("protein_g", 0),
            fat_g=data.get("fat_g", 0),
            carbs_g=data.get("carbs_g", 0),
            summary=data.get("summary", ""),
            source=EventSource(data.get("source", "text")),
            processing_level=data.get("processing_level", "whole"),
            needs_confirmation=data.get("needs_confirmation", False),
        )


@dataclass
class FastingEvent:
    user_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    id: Optional[int] = None
    
    @property
    def duration_hours(self) -> Optional[float]:
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return round(delta.total_seconds() / 3600, 2)
    
    @property
    def is_active(self) -> bool:
        return self.end_time is None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_hours": self.duration_hours,
        }


@dataclass
class SymptomEvent:
    user_id: int
    datetime: datetime
    symptom_type: SymptomType
    severity: int
    notes: str = ""
    id: Optional[int] = None
    
    def __post_init__(self):
        if not 1 <= self.severity <= 5:
            raise ValueError("Severity must be between 1 and 5")
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "datetime": self.datetime.isoformat(),
            "symptom_type": self.symptom_type.value,
            "severity": self.severity,
            "notes": self.notes,
        }


@dataclass
class WeightEvent:
    user_id: int
    datetime: datetime
    weight_kg: float
    notes: str = ""
    id: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "datetime": self.datetime.isoformat(),
            "weight_kg": self.weight_kg,
            "notes": self.notes,
        }


@dataclass
class DailyStats:
    date: str
    total_protein_g: float = 0
    total_fat_g: float = 0
    total_calories: float = 0
    unique_ingredients: List[str] = field(default_factory=list)
    meal_count: int = 0
    fasting_hours: float = 0
    first_meal_time: Optional[str] = None
    last_meal_time: Optional[str] = None
    carnivore_compliance: float = 100.0
    
    @property
    def fat_protein_ratio(self) -> Optional[float]:
        if self.total_protein_g == 0:
            return None
        return round(self.total_fat_g / self.total_protein_g, 2)
    
    @property
    def processing_score(self) -> str:
        return "whole"
