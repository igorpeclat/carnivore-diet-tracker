# Carnivore Diet Tracker Bot

Telegram bot para rastreamento de dieta carnívora com validação determinística. Usa IA para parsing, mas **nunca como fonte de verdade** - todas as decisões são validadas por regras estritas do `carnivore_core.py`.

## Arquitetura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Input    │────▶│   LLM (Parser)   │────▶│ carnivore_core  │
│ voice/photo/txt │     │ Ollama/Gemini    │     │ (SOURCE OF TRUTH)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │    database     │
                                                 │    (SQLite)     │
                                                 └─────────────────┘
```

**Princípio:** LLM extrai/sugere → `carnivore_core` valida → só então salva.

## Funcionalidades

### Comandos (19 total)

| Comando | Descrição |
|---------|-----------|
| `/start` | Inicializa o bot |
| `/setgoals <kcal> <prot> <fat>` | Define metas diárias de macros |
| `/setlevel strict\|relaxed` | Define nível de rigor carnívoro |
| `/stats` | Progresso diário com barras visuais |
| `/metabolic` | Score de adaptação cetogênica, risco de eletrólitos, tendências |
| `/diet` | Diário de refeições do dia |
| `/fast` | Inicia/encerra jejum |
| `/faststatus` | Duração atual do jejum com níveis |
| `/symptom <tipo> <1-5>` | Registra sintoma com severidade |
| `/symptoms` | Lista sintomas do dia |
| `/weight <kg>` | Registra peso com tendência |
| `/report [daily\|weekly\|html]` | Relatórios no Telegram |
| `/export <csv\|json\|html> [daily\|weekly]` | Exporta dados |
| `/recipe [preferência]` | Gera receita carnívora |
| `/suggest` | Sugestão baseada em macros restantes |
| `/plan_tomorrow` | Plano de refeições para amanhã |
| `/plan_week` | Plano semanal |
| `/notes` | Visualiza notas de voz |

### Input

- **Voz:** Transcrição local com Faster-Whisper
- **Foto:** Análise de imagem com Gemini API
- **Texto:** Parsing com Ollama/Mistral local

### Níveis Carnívoros

| Nível | Permitido |
|-------|-----------|
| **STRICT** | Apenas carne, peixe, ovos, gordura animal |
| **RELAXED** | + laticínios, café, temperos básicos |
| **DIRTY** | + adoçantes, bacon processado (com aviso) |

### Rastreamento

- Refeições com macros (kcal, proteína, gordura)
- Jejum intermitente (duração, quebras)
- Sintomas (tontura, fraqueza, cãibras, energia, etc.)
- Peso com tendências
- Score de adaptação cetogênica (0-100)

## Estrutura de Arquivos

```
meu_bot/
├── bot.py              # Bot principal (19 comandos)
├── carnivore_core.py   # Regras determinísticas (SOURCE OF TRUTH)
├── database.py         # SQLite - users, meals, fasting, symptoms, weight
├── models.py           # Dataclasses: MealEvent, FastingEvent, etc.
├── prompts.py          # Prompts LLM especializados
├── report_generator.py # HTML/CSV/JSON export com gráficos
├── rag_manifest.json   # Índice de fontes RAG
├── download_carnivore_rag.sh # Script para baixar PDFs
└── rag/                # Base de conhecimento
    ├── recipes/        # Livro de receitas (PDF)
    ├── science/        # Papers científicos
    ├── manual/         # Fontes que requerem download manual
    ├── carnivore_basics.md
    ├── carnivore_recipes.md
    ├── electrolyte_balance.md
    ├── fasting_protocols.md
    ├── keto_adaptation.md
    └── symptom_management.md
```

## Instalação

```bash
git clone https://github.com/igorpeclat/carnivore-diet-tracker.git
cd carnivore-diet-tracker

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Variáveis de Ambiente

Crie `.env`:
```
TELEGRAM_TOKEN=seu_token_do_botfather
GEMINI_API_KEY=sua_chave_gemini
```

### Modelos Locais

```bash
ollama pull mistral
```

### Executar

```bash
python3 bot.py
```

## Dependências

```
python-telegram-bot
google-generativeai
Pillow
faster-whisper
ollama
python-dotenv
```

## RAG (Base de Conhecimento)

Para baixar PDFs de referência:
```bash
./download_carnivore_rag.sh
```

**Importante:** RAG fornece contexto, não autoridade. Todo output passa pelo `carnivore_core.py`.

## Princípios de Design

1. **LLM nunca é fonte de verdade** - apenas parsing/sugestões
2. **Validação determinística** - regras fixas em `carnivore_core.py`
3. **Privacidade** - processamento local quando possível (Whisper, Ollama)
4. **Rastreamento completo** - refeições, jejum, sintomas, peso, adaptação
