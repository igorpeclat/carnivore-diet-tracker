import pytest
from carnivore_core import (
    CarnivoreLevel,
    ValidationResult,
    validate_ingredients,
    validate_llm_meal_output,
    find_matching_category,
    normalize_ingredient,
    check_breaks_fast,
    calculate_fat_protein_ratio,
    estimate_processing_level,
    get_carnivore_level_emoji,
    get_carnivore_level_description,
    format_validation_message,
    CARNIVORE_STRICT_ALLOWED,
    CARNIVORE_RELAXED_ALLOWED,
    ALWAYS_FORBIDDEN,
    DIRTY_CARNIVORE_ALLOWED,
)


class TestFoodClassification:
    def test_strict_allowed_beef(self):
        category, _ = find_matching_category("beef")
        assert category == "strict_allowed"
    
    def test_strict_allowed_eggs(self):
        category, _ = find_matching_category("eggs")
        assert category == "strict_allowed"
    
    def test_strict_allowed_salmon(self):
        category, _ = find_matching_category("salmon")
        assert category == "strict_allowed"
    
    def test_strict_allowed_bone_broth(self):
        category, _ = find_matching_category("bone broth")
        assert category == "strict_allowed"
    
    def test_strict_allowed_portuguese_picanha(self):
        category, _ = find_matching_category("picanha")
        assert category == "strict_allowed"
    
    def test_strict_allowed_portuguese_ovos(self):
        category, _ = find_matching_category("ovos")
        assert category == "strict_allowed"
    
    def test_relaxed_allowed_butter(self):
        category, _ = find_matching_category("butter")
        assert category == "relaxed_allowed"
    
    def test_relaxed_allowed_coffee(self):
        category, _ = find_matching_category("coffee")
        assert category == "relaxed_allowed"
    
    def test_relaxed_allowed_cheese(self):
        category, _ = find_matching_category("cheddar")
        assert category == "relaxed_allowed"
    
    def test_forbidden_vegetables(self):
        category, _ = find_matching_category("broccoli")
        assert category == "forbidden"
    
    def test_forbidden_grains(self):
        category, _ = find_matching_category("rice")
        assert category == "forbidden"
    
    def test_forbidden_sugar(self):
        category, _ = find_matching_category("sugar")
        assert category == "forbidden"
    
    def test_forbidden_seed_oil(self):
        category, _ = find_matching_category("canola oil")
        assert category == "forbidden"
    
    def test_forbidden_fruits(self):
        category, _ = find_matching_category("banana")
        assert category == "forbidden"
    
    def test_forbidden_potato(self):
        category, _ = find_matching_category("potato")
        assert category == "forbidden"
    
    def test_forbidden_portuguese_arroz(self):
        category, _ = find_matching_category("arroz")
        assert category == "forbidden"
    
    def test_dirty_allowed_hot_dog(self):
        category, _ = find_matching_category("hot dog")
        assert category == "dirty_allowed"
    
    def test_dirty_allowed_salami(self):
        category, _ = find_matching_category("salami")
        assert category == "dirty_allowed"
    
    def test_warning_garlic(self):
        category, _ = find_matching_category("garlic")
        assert category == "warning"
    
    def test_unknown_ingredient(self):
        category, _ = find_matching_category("xyz_unknown_food_123")
        assert category is None


class TestValidateIngredients:
    def test_strict_meal_valid(self):
        result = validate_ingredients(["beef", "eggs", "salt"])
        assert result.is_valid
        assert result.carnivore_level == CarnivoreLevel.STRICT
        assert len(result.forbidden_ingredients) == 0
    
    def test_relaxed_meal_detected(self):
        result = validate_ingredients(["beef", "butter", "coffee"])
        assert result.is_valid
        assert result.carnivore_level == CarnivoreLevel.RELAXED
    
    def test_forbidden_meal_not_carnivore(self):
        result = validate_ingredients(["beef", "rice", "eggs"])
        assert not result.is_valid
        assert result.carnivore_level == CarnivoreLevel.NOT_CARNIVORE
        assert "rice" in result.forbidden_ingredients
    
    def test_dirty_carnivore_detected(self):
        result = validate_ingredients(["hot dog", "eggs"])
        assert result.is_valid
        assert result.carnivore_level == CarnivoreLevel.DIRTY
    
    def test_warning_ingredients(self):
        result = validate_ingredients(["beef", "garlic"])
        assert result.is_valid
        assert "garlic" in result.warning_ingredients
        assert len(result.warnings) > 0
    
    def test_unknown_ingredient_needs_confirmation(self):
        result = validate_ingredients(["beef", "some_random_item"])
        assert result.needs_confirmation
        assert "some_random_item" in result.warning_ingredients
    
    def test_empty_ingredients(self):
        result = validate_ingredients([])
        assert result.is_valid
        assert result.carnivore_level == CarnivoreLevel.STRICT
    
    def test_mixed_forbidden_and_allowed(self):
        result = validate_ingredients(["steak", "potato", "eggs", "bread"])
        assert not result.is_valid
        assert "potato" in result.forbidden_ingredients
        assert "bread" in result.forbidden_ingredients
        assert "steak" in result.allowed_ingredients
        assert "eggs" in result.allowed_ingredients
    
    def test_target_level_strict_with_relaxed_items(self):
        result = validate_ingredients(["beef", "butter"], target_level=CarnivoreLevel.STRICT)
        assert result.is_valid
        assert len(result.warnings) > 0


class TestValidateLLMMealOutput:
    def test_valid_output(self):
        output = {
            "summary": "Steak with eggs",
            "ingredients": ["steak", "eggs"],
            "calories": 600,
            "macros": {"protein": 50, "fat": 40}
        }
        is_valid, errors = validate_llm_meal_output(output)
        assert is_valid
        assert len(errors) == 0
    
    def test_missing_summary(self):
        output = {
            "ingredients": ["steak"],
            "calories": 500
        }
        is_valid, errors = validate_llm_meal_output(output)
        assert not is_valid
        assert any("summary" in e for e in errors)
    
    def test_missing_ingredients(self):
        output = {
            "summary": "Steak",
            "calories": 500
        }
        is_valid, errors = validate_llm_meal_output(output)
        assert not is_valid
        assert any("ingredients" in e for e in errors)
    
    def test_missing_calories(self):
        output = {
            "summary": "Steak",
            "ingredients": ["steak"]
        }
        is_valid, errors = validate_llm_meal_output(output)
        assert not is_valid
        assert any("calories" in e for e in errors)
    
    def test_invalid_calories_type(self):
        output = {
            "summary": "Steak",
            "ingredients": ["steak"],
            "calories": "five hundred"
        }
        is_valid, errors = validate_llm_meal_output(output)
        assert not is_valid
        assert any("number" in e for e in errors)
    
    def test_negative_calories(self):
        output = {
            "summary": "Steak",
            "ingredients": ["steak"],
            "calories": -100
        }
        is_valid, errors = validate_llm_meal_output(output)
        assert not is_valid
        assert any("negative" in e for e in errors)
    
    def test_invalid_ingredients_type(self):
        output = {
            "summary": "Steak",
            "ingredients": "steak",
            "calories": 500
        }
        is_valid, errors = validate_llm_meal_output(output)
        assert not is_valid
        assert any("list" in e for e in errors)
    
    def test_not_dict(self):
        is_valid, errors = validate_llm_meal_output("invalid")
        assert not is_valid
        assert any("dictionary" in e for e in errors)


class TestHelperFunctions:
    def test_normalize_ingredient(self):
        assert normalize_ingredient("  BEEF  ") == "beef"
        assert normalize_ingredient("Salmon") == "salmon"
    
    def test_check_breaks_fast_positive(self):
        assert check_breaks_fast(100) is True
    
    def test_check_breaks_fast_zero(self):
        assert check_breaks_fast(0) is False
    
    def test_fat_protein_ratio(self):
        assert calculate_fat_protein_ratio(80, 100) == 0.8
        assert calculate_fat_protein_ratio(150, 100) == 1.5
    
    def test_fat_protein_ratio_zero_protein(self):
        assert calculate_fat_protein_ratio(80, 0) is None
    
    def test_processing_level_whole(self):
        level = estimate_processing_level(["beef", "eggs"])
        assert level == "whole"
    
    def test_processing_level_processed(self):
        level = estimate_processing_level(["beef", "hot dog", "eggs"])
        assert level == "processed"
    
    def test_carnivore_emoji_strict(self):
        assert get_carnivore_level_emoji(CarnivoreLevel.STRICT) == "🥩"
    
    def test_carnivore_emoji_not_carnivore(self):
        assert get_carnivore_level_emoji(CarnivoreLevel.NOT_CARNIVORE) == "❌"
    
    def test_carnivore_description_strict(self):
        desc = get_carnivore_level_description(CarnivoreLevel.STRICT)
        assert "Estrito" in desc
    
    def test_format_validation_message(self):
        result = ValidationResult(
            is_valid=False,
            carnivore_level=CarnivoreLevel.NOT_CARNIVORE,
            allowed_ingredients=["beef"],
            forbidden_ingredients=["rice"],
            warning_ingredients=[],
            warnings=["rice is forbidden"],
        )
        msg = format_validation_message(result)
        assert "❌" in msg
        assert "rice" in msg


class TestFoodSets:
    def test_strict_set_not_empty(self):
        assert len(CARNIVORE_STRICT_ALLOWED) > 50
    
    def test_relaxed_superset_of_strict(self):
        assert CARNIVORE_STRICT_ALLOWED.issubset(CARNIVORE_RELAXED_ALLOWED)
    
    def test_forbidden_and_allowed_disjoint(self):
        assert CARNIVORE_STRICT_ALLOWED.isdisjoint(ALWAYS_FORBIDDEN)
        assert CARNIVORE_RELAXED_ALLOWED.isdisjoint(ALWAYS_FORBIDDEN)
    
    def test_dirty_and_forbidden_disjoint(self):
        assert DIRTY_CARNIVORE_ALLOWED.isdisjoint(ALWAYS_FORBIDDEN)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
