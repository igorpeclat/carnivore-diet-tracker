"""
Carnivore Diet Core - Deterministic Rules Engine

This module is the SOURCE OF TRUTH for all carnivore diet validation.
LLM NEVER overrides these rules.
"""

from enum import Enum
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import re

# =============================================================================
# CARNIVORE LEVEL CLASSIFICATION
# =============================================================================

class CarnivoreLevel(Enum):
    STRICT = "strict"
    RELAXED = "relaxed"
    DIRTY = "dirty"
    NOT_CARNIVORE = "not_carnivore"


# =============================================================================
# FOOD CLASSIFICATION DATABASE (DETERMINISTIC)
# =============================================================================

CARNIVORE_STRICT_ALLOWED: Set[str] = {
    # Beef
    "beef", "steak", "ribeye", "sirloin", "brisket", "ground beef", "beef liver",
    "beef heart", "beef tongue", "beef kidney", "beef fat", "tallow", "bone marrow",
    "picanha", "contra-file", "costela", "alcatra", "maminha", "fraldinha", "acém",
    "patinho", "coxao mole", "coxao duro", "lagarto", "file mignon",
    # Pork
    "pork", "bacon", "pork belly", "pork chop", "pork loin", "ham", "pork fat", "lard",
    "pancetta", "porchetta", "linguica", "lombo",
    # Lamb
    "lamb", "lamb chop", "lamb leg", "lamb shoulder", "mutton", "cordeiro", "carneiro",
    # Goat
    "goat", "cabrito", "bode",
    # Poultry
    "chicken", "chicken thigh", "chicken breast", "chicken liver", "chicken heart",
    "turkey", "duck", "duck fat", "goose", "frango", "peru", "pato",
    # Fish
    "fish", "salmon", "tuna", "sardine", "mackerel", "cod", "halibut", "trout",
    "anchovy", "herring", "tilapia", "sea bass", "swordfish",
    "salmao", "atum", "sardinha", "bacalhau", "tilapia",
    # Seafood
    "shrimp", "crab", "lobster", "oyster", "mussel", "clam", "scallop", "squid",
    "octopus", "camarao", "caranguejo", "lagosta", "ostra", "lula", "polvo",
    # Eggs
    "egg", "eggs", "ovo", "ovos", "egg yolk", "egg white",
    # Animal fats
    "animal fat", "beef fat", "pork fat", "duck fat", "chicken fat", "schmaltz",
    "gordura animal", "banha",
    # Bone broth
    "bone broth", "caldo de osso",
    # Salt & Water
    "salt", "sea salt", "sal", "water", "agua",
}

CARNIVORE_RELAXED_ALLOWED: Set[str] = CARNIVORE_STRICT_ALLOWED | {
    # Dairy
    "butter", "manteiga", "ghee", "clarified butter",
    "hard cheese", "parmesan", "cheddar", "gruyere", "gouda", "pecorino",
    "queijo", "queijo parmesao", "queijo cheddar",
    "heavy cream", "creme de leite", "cream",
    "sour cream",
    # Coffee (black only)
    "black coffee", "cafe preto", "coffee", "cafe",
}

CARNIVORE_RELAXED_WARNING: Set[str] = {
    "garlic", "alho",
    "onion", "cebola",
    "pepper", "pimenta",
    "spices", "temperos",
    "herbs", "ervas",
}

# Always forbidden in any carnivore level
ALWAYS_FORBIDDEN: Set[str] = {
    # Vegetables
    "vegetable", "vegetables", "legume", "legumes", "verdura", "verduras",
    "salad", "salada", "lettuce", "alface", "tomato", "tomate",
    "cucumber", "pepino", "carrot", "cenoura", "broccoli", "brocolis",
    "spinach", "espinafre", "kale", "couve", "cabbage", "repolho",
    "zucchini", "abobrinha", "eggplant", "berinjela", "bell pepper", "pimentao",
    "cauliflower", "couve-flor", "asparagus", "aspargo",
    # Tubers (ALWAYS break carnivore)
    "potato", "batata", "sweet potato", "batata doce", "yam", "inhame",
    "cassava", "mandioca", "macaxeira", "aipim", "taro",
    # Fruits
    "fruit", "fruits", "fruta", "frutas", "apple", "maca", "banana",
    "orange", "laranja", "grape", "uva", "strawberry", "morango",
    "mango", "manga", "pineapple", "abacaxi", "watermelon", "melancia",
    "avocado", "abacate", "lemon", "limao", "lime",
    # Grains
    "grain", "grains", "grao", "graos", "wheat", "trigo", "rice", "arroz",
    "bread", "pao", "pasta", "macarrao", "noodle", "cereal",
    "oat", "aveia", "corn", "milho", "quinoa", "barley", "cevada",
    # Legumes
    "bean", "beans", "feijao", "lentil", "lentilha", "chickpea", "grao de bico",
    "pea", "ervilha", "soy", "soja", "tofu", "tempeh",
    # Sugar
    "sugar", "acucar", "honey", "mel", "syrup", "xarope", "maple",
    "agave", "molasses", "melaco",
    # Seed oils
    "seed oil", "oleo de semente", "vegetable oil", "oleo vegetal",
    "canola oil", "oleo de canola", "soybean oil", "oleo de soja",
    "sunflower oil", "oleo de girassol", "corn oil", "oleo de milho",
    "safflower oil", "cottonseed oil", "grapeseed oil",
    "margarine", "margarina",
    # Processed/Industrial
    "sauce", "molho", "ketchup", "mustard", "mostarda", "mayonnaise", "maionese",
    "soy sauce", "molho de soja", "teriyaki", "bbq sauce",
    # Nuts and seeds
    "nut", "nuts", "nozes", "castanha", "almond", "amendoa", "peanut", "amendoim",
    "walnut", "cashew", "caju", "pistachio", "pistache",
    "seed", "seeds", "semente", "sementes", "chia", "flax", "linhaca",
    "sunflower seed", "semente de girassol", "pumpkin seed",
}

# Dirty carnivore allows these (processed but still animal-based)
DIRTY_CARNIVORE_ALLOWED: Set[str] = {
    "processed meat", "carne processada",
    "hot dog", "salsicha", "sausage", "linguica industrializada",
    "deli meat", "frios", "bologna", "mortadela",
    "industrial cheese", "queijo processado", "cheese spread",
    "jerky", "charque", "carne seca",
    "pepperoni", "salami", "salame",
}


# =============================================================================
# VALIDATION ENGINE
# =============================================================================

@dataclass
class ValidationResult:
    """Result of food validation against carnivore rules"""
    is_valid: bool
    carnivore_level: CarnivoreLevel
    allowed_ingredients: List[str]
    forbidden_ingredients: List[str]
    warning_ingredients: List[str]
    warnings: List[str]
    breaks_fast: bool = False
    needs_confirmation: bool = False
    ruleset_version: str = "1.0.0"


def normalize_ingredient(ingredient: str) -> str:
    """Normalize ingredient for matching"""
    return ingredient.lower().strip()


def find_matching_category(ingredient: str) -> tuple[Optional[str], Optional[Set[str]]]:
    """Find which category an ingredient belongs to"""
    normalized = normalize_ingredient(ingredient)
    
    # Check exact matches first
    if normalized in ALWAYS_FORBIDDEN:
        return "forbidden", ALWAYS_FORBIDDEN
    if normalized in CARNIVORE_STRICT_ALLOWED:
        return "strict_allowed", CARNIVORE_STRICT_ALLOWED
    if normalized in CARNIVORE_RELAXED_ALLOWED:
        return "relaxed_allowed", CARNIVORE_RELAXED_ALLOWED
    if normalized in CARNIVORE_RELAXED_WARNING:
        return "warning", CARNIVORE_RELAXED_WARNING
    if normalized in DIRTY_CARNIVORE_ALLOWED:
        return "dirty_allowed", DIRTY_CARNIVORE_ALLOWED
    
    # Check partial matches (ingredient contains known food)
    for forbidden in ALWAYS_FORBIDDEN:
        if forbidden in normalized or normalized in forbidden:
            return "forbidden", ALWAYS_FORBIDDEN
    
    for strict in CARNIVORE_STRICT_ALLOWED:
        if strict in normalized or normalized in strict:
            return "strict_allowed", CARNIVORE_STRICT_ALLOWED
    
    for relaxed in CARNIVORE_RELAXED_ALLOWED:
        if relaxed in normalized or normalized in relaxed:
            return "relaxed_allowed", CARNIVORE_RELAXED_ALLOWED
    
    return None, None


def validate_ingredients(ingredients: List[str], target_level: CarnivoreLevel = CarnivoreLevel.STRICT) -> ValidationResult:
    """
    Validate a list of ingredients against carnivore rules.
    
    This is the CORE validation function. LLM output MUST pass through this.
    """
    allowed = []
    forbidden = []
    warnings = []
    warning_ingredients = []
    
    detected_level = CarnivoreLevel.STRICT
    
    for ingredient in ingredients:
        category, _ = find_matching_category(ingredient)
        
        if category == "forbidden":
            forbidden.append(ingredient)
            detected_level = CarnivoreLevel.NOT_CARNIVORE
            
        elif category == "strict_allowed":
            allowed.append(ingredient)
            
        elif category == "relaxed_allowed":
            allowed.append(ingredient)
            if target_level == CarnivoreLevel.STRICT:
                warnings.append(f"'{ingredient}' is only allowed in RELAXED mode")
                warning_ingredients.append(ingredient)
            if detected_level == CarnivoreLevel.STRICT:
                detected_level = CarnivoreLevel.RELAXED
                
        elif category == "warning":
            warning_ingredients.append(ingredient)
            warnings.append(f"'{ingredient}' should be used sparingly")
            if detected_level == CarnivoreLevel.STRICT:
                detected_level = CarnivoreLevel.RELAXED
                
        elif category == "dirty_allowed":
            allowed.append(ingredient)
            warnings.append(f"'{ingredient}' is processed - considered DIRTY carnivore")
            detected_level = CarnivoreLevel.DIRTY
            
        else:
            # Unknown ingredient - needs confirmation
            warnings.append(f"Unknown ingredient '{ingredient}' - needs verification")
            warning_ingredients.append(ingredient)
    
    # Determine final validity
    is_valid = len(forbidden) == 0
    needs_confirmation = len(warning_ingredients) > 0 and len(forbidden) == 0
    
    return ValidationResult(
        is_valid=is_valid,
        carnivore_level=detected_level,
        allowed_ingredients=allowed,
        forbidden_ingredients=forbidden,
        warning_ingredients=warning_ingredients,
        warnings=warnings,
        needs_confirmation=needs_confirmation,
    )


def check_breaks_fast(calories: float) -> bool:
    """Determine if food intake breaks a fast"""
    return calories > 0


def calculate_fat_protein_ratio(fat_g: float, protein_g: float) -> Optional[float]:
    """Calculate fat to protein ratio (important for carnivore)"""
    if protein_g == 0:
        return None
    return round(fat_g / protein_g, 2)


def estimate_processing_level(ingredients: List[str]) -> str:
    """
    Estimate how processed a meal is.
    Returns: 'whole', 'minimally_processed', 'processed', 'ultra_processed'
    """
    dirty_count = sum(1 for i in ingredients if normalize_ingredient(i) in DIRTY_CARNIVORE_ALLOWED)
    
    if dirty_count == 0:
        if len(ingredients) <= 3:
            return "whole"
        return "minimally_processed"
    elif dirty_count <= len(ingredients) / 2:
        return "processed"
    else:
        return "ultra_processed"


# =============================================================================
# SCHEMA VALIDATION (for LLM outputs)
# =============================================================================

MEAL_SCHEMA = {
    "type": "object",
    "required": ["summary", "ingredients", "calories", "macros"],
    "properties": {
        "summary": {"type": "string"},
        "ingredients": {"type": "array", "items": {"type": "string"}},
        "calories": {"type": "number", "minimum": 0},
        "macros": {
            "type": "object",
            "properties": {
                "protein": {"type": "number", "minimum": 0},
                "fat": {"type": "number", "minimum": 0},
                "carbs": {"type": "number", "minimum": 0}
            }
        },
        "quantities": {"type": "array", "items": {"type": "string"}}
    }
}


def validate_llm_meal_output(output: dict) -> tuple[bool, List[str]]:
    """
    Validate that LLM output conforms to expected schema.
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    if not isinstance(output, dict):
        return False, ["Output must be a dictionary"]
    
    # Check required fields
    for field in ["summary", "ingredients", "calories"]:
        if field not in output:
            errors.append(f"Missing required field: {field}")
    
    # Validate types
    if "summary" in output and not isinstance(output["summary"], str):
        errors.append("'summary' must be a string")
    
    if "ingredients" in output:
        if not isinstance(output["ingredients"], list):
            errors.append("'ingredients' must be a list")
        elif not all(isinstance(i, str) for i in output["ingredients"]):
            errors.append("All ingredients must be strings")
    
    if "calories" in output:
        if not isinstance(output["calories"], (int, float)):
            errors.append("'calories' must be a number")
        elif output["calories"] < 0:
            errors.append("'calories' cannot be negative")
    
    if "macros" in output:
        if not isinstance(output["macros"], dict):
            errors.append("'macros' must be a dictionary")
        else:
            for macro in ["protein", "fat"]:
                if macro in output["macros"]:
                    if not isinstance(output["macros"][macro], (int, float)):
                        errors.append(f"'{macro}' must be a number")
    
    return len(errors) == 0, errors


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_carnivore_level_emoji(level: CarnivoreLevel) -> str:
    """Get emoji representation of carnivore level"""
    return {
        CarnivoreLevel.STRICT: "🥩",
        CarnivoreLevel.RELAXED: "🧈",
        CarnivoreLevel.DIRTY: "⚠️",
        CarnivoreLevel.NOT_CARNIVORE: "❌",
    }.get(level, "❓")


def get_carnivore_level_description(level: CarnivoreLevel) -> str:
    """Get human-readable description of carnivore level"""
    return {
        CarnivoreLevel.STRICT: "Carnivore Estrito",
        CarnivoreLevel.RELAXED: "Carnivore Relaxado",
        CarnivoreLevel.DIRTY: "Carnivore Sujo",
        CarnivoreLevel.NOT_CARNIVORE: "Quebrou Carnivore",
    }.get(level, "Desconhecido")


def format_validation_message(result: ValidationResult) -> str:
    """Format validation result for Telegram message"""
    emoji = get_carnivore_level_emoji(result.carnivore_level)
    level_desc = get_carnivore_level_description(result.carnivore_level)
    
    lines = [f"{emoji} *{level_desc}*"]
    
    if result.forbidden_ingredients:
        lines.append(f"\n❌ *Proibido:* {', '.join(result.forbidden_ingredients)}")
    
    if result.warning_ingredients:
        lines.append(f"\n⚠️ *Atenção:* {', '.join(result.warning_ingredients)}")
    
    if result.warnings:
        lines.append("\n📝 *Avisos:*")
        for w in result.warnings[:3]:  # Limit to 3 warnings
            lines.append(f"  • {w}")
    
    return "\n".join(lines)
