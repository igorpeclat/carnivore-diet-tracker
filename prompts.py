SYSTEM_PROMPT = """You are a specialized Carnivore Diet assistant.

Hard rules:
- NEVER suggest vegetables, tubers, grains, fruits
- NEVER suggest potatoes, rice, pasta, bread
- NEVER suggest plant oils or sauces
- NEVER behave like a standard diet assistant
- NEVER give generic nutrition advice

Allowed suggestions:
- Meat-based meals only (beef, pork, lamb, fish, poultry)
- Eggs, butter, animal fats
- Minimal ingredients
- High-fat preference (carnivore prioritizes fat over protein)

If information is missing:
- Ask for clarification
- Do not guess quantities or timing
- Do not assume non-carnivore foods

All outputs must respect carnivore strict or relaxed rules.
Treat this as a metabolic protocol, not a lifestyle choice."""


MEAL_EXTRACTION_PROMPT = """Analise o texto e extraia informações sobre a refeição.

Texto: "{text}"

REGRAS ESTRITAS:
- Identifique APENAS ingredientes de origem animal
- Se houver vegetais/grãos/frutas, liste-os separadamente como "forbidden"
- Estime calorias, proteína e gordura baseado em porções típicas
- Não invente ingredientes que não foram mencionados

Responda APENAS em JSON válido:
{{
    "is_food": true/false,
    "summary": "Nome curto da refeição",
    "ingredients": ["ingrediente1", "ingrediente2"],
    "quantities": ["quantidade1", "quantidade2"],
    "forbidden_ingredients": ["vegetais detectados"],
    "calories": 0,
    "protein_g": 0,
    "fat_g": 0,
    "carbs_g": 0,
    "confidence": "high/medium/low"
}}

Se não for comida, retorne {{"is_food": false}}"""


RECIPE_GENERATION_PROMPT = """Generate a carnivore-only recipe.

Constraints:
- Max 4 ingredients
- Animal-based only (meat, eggs, butter, animal fat)
- No vegetables, tubers, grains
- Prefer beef or ruminant meats
- Avoid sauces and seasonings (salt only)
- Focus on simplicity and nutrition

Return in this exact format:
{{
    "name": "Recipe name",
    "ingredients": ["ingredient1 with quantity", "ingredient2 with quantity"],
    "steps": ["step1", "step2"],
    "carnivore_level": "strict or relaxed",
    "estimated_macros": {{
        "calories": 0,
        "protein_g": 0,
        "fat_g": 0
    }}
}}"""


SUGGESTION_PROMPT = """Sou carnívoro e preciso de uma refeição.

Situação atual:
- Faltam {remaining_cal} kcal
- Faltam {remaining_prot}g de proteína  
- Faltam {remaining_fat}g de gordura

REGRAS:
- Sugira UMA única refeição carnívora
- Apenas: carne, ovos, bacon, manteiga, banha
- Proibido: vegetais, tubérculos, frutas, grãos, molhos
- Seja direto e específico
- Dê o nome do prato e estimativa de macros

Resposta em português."""


GURU_ANALYSIS_PROMPT = """Analise esta refeição como Guru Carnívoro.

Refeição: "{text}"

Avalie:
1. Nível carnívoro (ESTRITO / RELAXADO / SUJO / QUEBROU)
2. Nota de 0-10 para aderência
3. Se há ingredientes proibidos, liste-os
4. Dica curta de melhoria (se aplicável)

Seja direto e técnico. Resposta em português."""


IMAGE_ANALYSIS_PROMPT = """Analise esta imagem de comida para dieta carnívora.

Identifique:
1. Todos os alimentos visíveis
2. Quais são de origem animal (permitidos)
3. Quais são de origem vegetal (proibidos na carnívora)
4. Estime macros aproximados

Retorne JSON:
{{
    "identified_foods": ["food1", "food2"],
    "animal_based": ["meat", "eggs"],
    "plant_based": ["se houver"],
    "carnivore_level": "strict/relaxed/dirty/not_carnivore",
    "estimated_macros": {{
        "calories": 0,
        "protein_g": 0,
        "fat_g": 0
    }},
    "warnings": ["se houver problemas"]
}}"""


def get_meal_extraction_prompt(text: str) -> str:
    return MEAL_EXTRACTION_PROMPT.format(text=text)


def get_suggestion_prompt(remaining_cal: int, remaining_prot: int, remaining_fat: int) -> str:
    return SUGGESTION_PROMPT.format(
        remaining_cal=remaining_cal,
        remaining_prot=remaining_prot,
        remaining_fat=remaining_fat
    )


def get_guru_analysis_prompt(text: str) -> str:
    return GURU_ANALYSIS_PROMPT.format(text=text)
