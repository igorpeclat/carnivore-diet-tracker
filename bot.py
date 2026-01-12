from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton
import json
import os
import logging
from datetime import datetime
from google import genai
from PIL import Image
from faster_whisper import WhisperModel
import ollama
import database
import report_generator
from dotenv import load_dotenv
import prompts
from carnivore_core import (
    validate_ingredients,
    validate_llm_meal_output,
    CarnivoreLevel,
    get_carnivore_level_emoji,
    get_carnivore_level_description,
    format_validation_message,
    estimate_processing_level,
    check_breaks_fast,
)

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-1.5-flash"

OLLAMA_MODEL = "mistral"

logger.info("Carregando Faster-Whisper (modelo small)...")
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
logger.info("Faster-Whisper carregado!")


def transcribe_audio_whisper(audio_path: str) -> tuple[str, float]:
    logger.info(f"Iniciando transcrição de: {audio_path}")
    start_time = datetime.now()
    try:
        segments, info = whisper_model.transcribe(audio_path, language="pt", beam_size=5, vad_filter=True)
        transcription = " ".join([segment.text.strip() for segment in segments])
        duration = datetime.now() - start_time
        logger.info(f"Transcrição concluída em {duration.total_seconds():.2f}s. Texto: {transcription[:50]}...")
        return transcription if transcription else "Não consegui transcrever o áudio", info.duration
    except Exception as e:
        logger.error(f"Erro na transcrição local: {str(e)}")
        return f"Erro na transcrição local: {str(e)}", 0


def extract_meal_from_text(transcription: str) -> dict:
    logger.info("Extraindo dados de refeição com Ollama...")
    try:
        prompt = prompts.get_meal_extraction_prompt(transcription)
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': prompts.SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ]
        )
        text = response['message']['content'].strip()
        
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        parsed = json.loads(text)
        
        is_valid, errors = validate_llm_meal_output(parsed)
        if not is_valid:
            logger.warning(f"LLM output validation errors: {errors}")
            return {"is_food": False, "errors": errors}
        
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {str(e)}")
        return {"is_food": False, "parse_error": str(e)}
    except Exception as e:
        logger.error(f"Erro no Ollama (Nutrição): {str(e)}")
        return {"is_food": False, "error": str(e)}


def validate_and_classify_meal(llm_output: dict, user_preferred_level: str = "strict") -> dict:
    if not llm_output.get("is_food"):
        return llm_output
    
    ingredients = llm_output.get("ingredients", [])
    forbidden = llm_output.get("forbidden_ingredients", [])
    all_ingredients = ingredients + forbidden
    
    target_level = CarnivoreLevel.STRICT if user_preferred_level == "strict" else CarnivoreLevel.RELAXED
    validation = validate_ingredients(all_ingredients, target_level)
    
    processing = estimate_processing_level(ingredients)
    breaks_fast = check_breaks_fast(llm_output.get("calories", 0))
    
    return {
        **llm_output,
        "carnivore_level": validation.carnivore_level.value,
        "is_valid_carnivore": validation.is_valid,
        "allowed_ingredients": validation.allowed_ingredients,
        "forbidden_ingredients": validation.forbidden_ingredients,
        "warning_ingredients": validation.warning_ingredients,
        "warnings": validation.warnings,
        "processing_level": processing,
        "breaks_fast": breaks_fast,
        "needs_confirmation": validation.needs_confirmation,
        "validation_message": format_validation_message(validation),
    }


def get_carnivore_suggestion(remaining_cal: int, remaining_prot: int, remaining_fat: int) -> str:
    try:
        prompt = prompts.get_suggestion_prompt(remaining_cal, remaining_prot, remaining_fat)
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': prompts.SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ]
        )
        return response['message']['content']
    except Exception:
        return "Picanha com manteiga e sal. Clássico carnívoro."


def get_ai_analysis(text: str) -> str:
    try:
        prompt = prompts.get_guru_analysis_prompt(text)
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': prompts.SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ]
        )
        return response['message']['content']
    except Exception:
        return "Análise indisponível."


def analyze_food_image(image_path: str) -> dict:
    try:
        img = Image.open(image_path)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompts.IMAGE_ANALYSIS_PROMPT, img]
        )
        text = response.text.strip()
        
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "Failed to parse image analysis", "raw": response.text if 'response' in dir() else ""}
    except Exception as e:
        return {"error": f"Vision error: {str(e)}"}


def get_menu_keyboard():
    keyboard = [
        [KeyboardButton("🎙️ Gravar"), KeyboardButton("📸 Foto")],
        [KeyboardButton("🥗 Dieta Hoje"), KeyboardButton("📊 Estatísticas")],
        [KeyboardButton("🍖 Sugestão"), KeyboardButton("📄 Relatório HTML")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def setup_commands(app):
    commands = [
        BotCommand("start", "Início"),
        BotCommand("setgoals", "Definir Metas (kcal prot fat)"),
        BotCommand("setlevel", "Nível carnívoro (strict/relaxed)"),
        BotCommand("stats", "Ver Progresso"),
        BotCommand("metabolic", "Status Metabólico"),
        BotCommand("diet", "Diário"),
        BotCommand("fast", "Iniciar/parar jejum"),
        BotCommand("faststatus", "Status do jejum"),
        BotCommand("symptom", "Registrar sintoma"),
        BotCommand("symptoms", "Sintomas de hoje"),
        BotCommand("weight", "Registrar peso"),
        BotCommand("report", "Relatório (daily/weekly/html)"),
        BotCommand("export", "Exportar (csv/json/html)"),
        BotCommand("recipe", "Gerar receita carnívora"),
        BotCommand("suggest", "Sugestão"),
        BotCommand("plan_tomorrow", "Menu Amanhã"),
        BotCommand("plan_week", "Menu Semanal"),
    ]
    await app.bot.set_my_commands(commands)


async def start(update: Update, context):
    user = update.effective_user
    if user:
        database.add_user(user.id, user.username or "")
        await update.message.reply_text(
            "🦁 *Carnivore Tracker Ativado*\n\n"
            "Sistema determinístico para dieta carnívora.\n\n"
            "*Comandos:*\n"
            "`/setgoals 2000 150 140` → Metas (Kcal, Prot, Fat)\n"
            "`/setlevel strict` → Nível (strict/relaxed)\n"
            "`/stats` → Progresso diário\n"
            "`/suggest` → O que comer agora?\n\n"
            "*Registrar:*\n"
            "• Envie áudio descrevendo refeição\n"
            "• Envie foto da comida\n"
            "• Digite o que comeu\n\n"
            "🥩 Toda refeição é validada contra regras carnívoras.",
            parse_mode="Markdown",
            reply_markup=get_menu_keyboard()
        )


async def set_goals_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(
                "Uso: `/setgoals <kcal> <prot> <gordura>`\n"
                "Ex: `/setgoals 2000 160 140`",
                parse_mode="Markdown"
            )
            return
        
        kcal, prot, fat = map(int, args)
        database.set_goals(user.id, kcal, prot, fat)
        
        ratio = round(fat / prot, 2) if prot > 0 else 0
        await update.message.reply_text(
            f"🎯 *Metas Definidas!*\n\n"
            f"🔥 Calorias: {kcal}\n"
            f"💪 Proteína: {prot}g\n"
            f"🧈 Gordura: {fat}g\n"
            f"📊 Ratio G/P: {ratio}",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("Use apenas números inteiros.")


async def set_level_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    args = context.args
    if not args or args[0].lower() not in ["strict", "relaxed"]:
        await update.message.reply_text(
            "Uso: `/setlevel <strict|relaxed>`\n\n"
            "• *strict*: Apenas carne, ovos, gordura animal, sal, água\n"
            "• *relaxed*: + manteiga, queijos duros, café preto",
            parse_mode="Markdown"
        )
        return
    
    level = args[0].lower()
    database.set_user_preferred_level(user.id, level)
    
    emoji = "🥩" if level == "strict" else "🧈"
    await update.message.reply_text(
        f"{emoji} Nível carnívoro definido: *{level.upper()}*",
        parse_mode="Markdown"
    )


async def stats_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    goals = database.get_goals(user.id)
    stats = database.get_daily_stats(user.id, today)
    
    msg = f"📊 *Estatísticas ({today})*\n\n"
    
    def progress_bar(atual, total):
        if total == 0:
            return "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%"
        perc = min(100, int((atual/total)*100))
        chars = int(perc/10)
        return "🟩" * chars + "⬜" * (10 - chars) + f" {perc}%"
    
    if goals:
        msg += f"🔥 *Kcal*: {stats['total_calories']:.0f}/{goals['calories']}\n"
        msg += progress_bar(stats['total_calories'], goals['calories']) + "\n\n"
        msg += f"💪 *Prot*: {stats['total_protein_g']:.0f}/{goals['protein']}g\n"
        msg += progress_bar(stats['total_protein_g'], goals['protein']) + "\n\n"
        msg += f"🧈 *Gord*: {stats['total_fat_g']:.0f}/{goals['fat']}g\n"
        msg += progress_bar(stats['total_fat_g'], goals['fat']) + "\n\n"
    else:
        msg += f"🔥 *Kcal*: {stats['total_calories']:.0f}\n"
        msg += f"💪 *Prot*: {stats['total_protein_g']:.0f}g\n"
        msg += f"🧈 *Gord*: {stats['total_fat_g']:.0f}g\n\n"
        msg += "_Use /setgoals para ativar metas_\n\n"
    
    if stats['fat_protein_ratio']:
        msg += f"📐 *Ratio G/P*: {stats['fat_protein_ratio']}\n"
    
    msg += f"🍽️ *Refeições*: {stats['meal_count']}\n"
    
    if stats['first_meal_time'] and stats['last_meal_time']:
        msg += f"⏰ *Janela*: {stats['first_meal_time']} - {stats['last_meal_time']}\n"
    
    compliance_emoji = "🥩" if stats['carnivore_compliance'] == 100 else "⚠️"
    msg += f"{compliance_emoji} *Aderência*: {stats['carnivore_compliance']:.0f}%"
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def suggest_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    goals = database.get_goals(user.id)
    
    await update.message.reply_text("🤔 Consultando o Guru Carnívoro...")
    
    if goals:
        stats = database.get_daily_stats(user.id, today)
        rem_kcal = max(0, goals['calories'] - stats['total_calories'])
        rem_prot = max(0, goals['protein'] - stats['total_protein_g'])
        rem_fat = max(0, goals['fat'] - stats['total_fat_g'])
        suggestion = get_carnivore_suggestion(int(rem_kcal), int(rem_prot), int(rem_fat))
    else:
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {'role': 'system', 'content': prompts.SYSTEM_PROMPT},
                    {'role': 'user', 'content': "Sugira uma refeição carnívora clássica. Seja direto."}
                ]
            )
            suggestion = response['message']['content']
        except Exception:
            suggestion = "Ribeye com manteiga e sal. Sem erro."

    await update.message.reply_text(f"🍖 *Sugestão:*\n\n{suggestion}", parse_mode="Markdown")


async def diet_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    meals = database.get_meal_events(user.id, today)
    
    if not meals:
        await update.message.reply_text(
            "🥗 Nada registrado hoje.\nEnvie fotos, áudios ou texto!",
            reply_markup=get_menu_keyboard()
        )
        return
    
    lines = []
    for m in meals:
        level_emoji = get_carnivore_level_emoji(CarnivoreLevel(m['carnivore_level']))
        source_emoji = '📸' if m['source'] == 'photo' else '🎙️' if m['source'] == 'voice' else '📝'
        
        line = f"• {m['time']} {source_emoji} {m['summary']} {level_emoji}"
        line += f"\n   └ P: {m['protein_g']:.0f}g | G: {m['fat_g']:.0f}g | {m['calories']:.0f}kcal"
        
        if m['warnings']:
            line += f"\n   ⚠️ {len(m['warnings'])} aviso(s)"
        
        lines.append(line)
    
    stats = database.get_daily_stats(user.id, today)
    
    msg = f"🦁 *Diário Carnívoro ({today})*\n\n"
    msg += "\n".join(lines)
    msg += f"\n\n━━━━━━━━━━━━━━━\n"
    msg += f"💪 Proteína: {stats['total_protein_g']:.0f}g\n"
    msg += f"🧈 Gordura: {stats['total_fat_g']:.0f}g\n"
    msg += f"🔥 Calorias: {stats['total_calories']:.0f}\n"
    
    if stats['fat_protein_ratio']:
        msg += f"📐 Ratio G/P: {stats['fat_protein_ratio']}"
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def notes_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    notes = database.get_voice_notes(user.id, today)
    
    if not notes:
        await update.message.reply_text("📝 Nenhuma nota hoje.", reply_markup=get_menu_keyboard())
        return
    
    text = "\n\n".join([
        f"• {n['time']} {'🍽️' if n['food_detected'] else '📝'}: {n['transcription'][:100]}..."
        for n in notes
    ])
    await update.message.reply_text(f"🎙️ *Notas {today}*\n\n{text}", parse_mode="Markdown")


async def fast_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    active_fast = database.get_active_fast(user.id)
    now = datetime.now()
    
    if active_fast:
        database.end_fast(user.id, now)
        start_time = datetime.fromisoformat(active_fast['start_time'])
        duration = (now - start_time).total_seconds() / 3600
        
        await update.message.reply_text(
            f"⏹️ *Jejum Encerrado!*\n\n"
            f"⏱️ Duração: {duration:.1f} horas\n"
            f"🕐 Início: {start_time.strftime('%H:%M')}\n"
            f"🕐 Fim: {now.strftime('%H:%M')}",
            parse_mode="Markdown",
            reply_markup=get_menu_keyboard()
        )
    else:
        database.start_fast(user.id, now)
        await update.message.reply_text(
            f"▶️ *Jejum Iniciado!*\n\n"
            f"🕐 Início: {now.strftime('%H:%M')}\n\n"
            f"Use `/fast` novamente para encerrar.",
            parse_mode="Markdown",
            reply_markup=get_menu_keyboard()
        )


async def fast_status_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    active_fast = database.get_active_fast(user.id)
    
    if not active_fast:
        await update.message.reply_text(
            "😴 *Nenhum jejum ativo*\n\n"
            "Use `/fast` para iniciar um jejum.",
            parse_mode="Markdown"
        )
        return
    
    start_time = datetime.fromisoformat(active_fast['start_time'])
    now = datetime.now()
    duration = (now - start_time).total_seconds() / 3600
    
    if duration < 12:
        status_emoji = "🟡"
        status_text = "Jejum inicial"
    elif duration < 16:
        status_emoji = "🟢"
        status_text = "Zona de queima de gordura"
    elif duration < 24:
        status_emoji = "🔥"
        status_text = "Autofagia ativada"
    else:
        status_emoji = "⚡"
        status_text = "Jejum prolongado"
    
    await update.message.reply_text(
        f"⏳ *Jejum em Andamento*\n\n"
        f"{status_emoji} {status_text}\n\n"
        f"⏱️ *Duração:* {duration:.1f} horas\n"
        f"🕐 *Início:* {start_time.strftime('%d/%m %H:%M')}\n\n"
        f"Use `/fast` para encerrar.",
        parse_mode="Markdown"
    )


async def symptom_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    args = context.args
    if not args:
        symptoms_list = (
            "😵 dizziness\n"
            "💪 weakness\n"
            "🤕 headache\n"
            "🦵 cramps\n"
            "🚽 diarrhea\n"
            "🚫 constipation\n"
            "🧠 brain_fog\n"
            "🤢 nausea\n"
            "⚡ high_energy\n"
            "😴 low_energy"
        )
        await update.message.reply_text(
            f"*Registrar Sintoma*\n\n"
            f"Uso: `/symptom <tipo> <severidade 1-5>`\n\n"
            f"*Tipos disponíveis:*\n{symptoms_list}\n\n"
            f"Exemplo: `/symptom headache 3`",
            parse_mode="Markdown"
        )
        return
    
    valid_symptoms = [
        "dizziness", "weakness", "headache", "cramps", "diarrhea",
        "constipation", "brain_fog", "nausea", "high_energy", "low_energy"
    ]
    
    symptom_type = args[0].lower()
    if symptom_type not in valid_symptoms:
        await update.message.reply_text(f"❌ Sintoma inválido. Use `/symptom` para ver opções.")
        return
    
    severity = 3
    if len(args) > 1:
        try:
            severity = int(args[1])
            if not 1 <= severity <= 5:
                severity = 3
        except ValueError:
            severity = 3
    
    database.add_symptom(user.id, datetime.now(), symptom_type, severity)
    
    severity_bar = "🟢" * severity + "⚪" * (5 - severity)
    await update.message.reply_text(
        f"✅ *Sintoma Registrado*\n\n"
        f"🩺 Tipo: {symptom_type}\n"
        f"📊 Severidade: {severity_bar} ({severity}/5)",
        parse_mode="Markdown"
    )


async def symptoms_today_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    symptoms = database.get_symptoms(user.id, today)
    
    if not symptoms:
        await update.message.reply_text(
            "✅ *Nenhum sintoma registrado hoje*\n\n"
            "Use `/symptom <tipo> <1-5>` para registrar.",
            parse_mode="Markdown"
        )
        return
    
    lines = []
    for s in symptoms:
        time = s['datetime'].split('T')[1][:5] if 'T' in s['datetime'] else s['datetime']
        severity_bar = "🟢" * s['severity'] + "⚪" * (5 - s['severity'])
        lines.append(f"• {time} - {s['symptom_type']} {severity_bar}")
    
    await update.message.reply_text(
        f"🩺 *Sintomas de Hoje ({today})*\n\n" + "\n".join(lines),
        parse_mode="Markdown"
    )


async def weight_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    args = context.args
    if not args:
        history = database.get_weight_history(user.id, 7)
        if not history:
            await update.message.reply_text(
                "⚖️ *Registrar Peso*\n\n"
                "Uso: `/weight <kg>`\n"
                "Exemplo: `/weight 85.5`",
                parse_mode="Markdown"
            )
            return
        
        lines = []
        for w in history:
            date = w['datetime'].split('T')[0] if 'T' in w['datetime'] else w['datetime']
            lines.append(f"• {date}: {w['weight_kg']:.1f} kg")
        
        await update.message.reply_text(
            f"⚖️ *Histórico de Peso*\n\n" + "\n".join(lines),
            parse_mode="Markdown"
        )
        return
    
    try:
        weight = float(args[0].replace(',', '.'))
        if not 30 <= weight <= 300:
            await update.message.reply_text("❌ Peso deve estar entre 30 e 300 kg.")
            return
        
        database.add_weight(user.id, datetime.now(), weight)
        
        history = database.get_weight_history(user.id, 2)
        if len(history) >= 2:
            diff = history[0]['weight_kg'] - history[1]['weight_kg']
            trend = "📉" if diff < 0 else "📈" if diff > 0 else "➡️"
            trend_text = f"\n{trend} Variação: {diff:+.1f} kg"
        else:
            trend_text = ""
        
        await update.message.reply_text(
            f"✅ *Peso Registrado*\n\n"
            f"⚖️ {weight:.1f} kg{trend_text}",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ Use um número válido. Ex: `/weight 85.5`")


async def metabolic_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    await update.message.reply_text("🔬 Calculando status metabólico...")
    
    stats = database.get_metabolic_stats(user.id)
    
    keto_bar = "🟢" * (stats['keto_adaptation_score'] // 10) + "⚪" * (10 - stats['keto_adaptation_score'] // 10)
    
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(stats['electrolyte_risk'], "⚪")
    trend_emoji = {"improving": "📈", "stable": "➡️", "declining": "📉", "unknown": "❓"}.get(stats['energy_trend'], "❓")
    
    msg = f"🔬 *Status Metabólico*\n\n"
    
    msg += f"*Adaptação Cetogênica*\n"
    msg += f"{keto_bar} {stats['keto_adaptation_score']}%\n"
    msg += f"📊 {stats['keto_adaptation_label']}\n\n"
    
    msg += f"*Indicadores (30 dias)*\n"
    msg += f"📅 Dias no protocolo: {stats['days_on_protocol']}\n"
    msg += f"🥩 Aderência carnívora: {stats['carnivore_compliance']:.0f}%\n"
    msg += f"{risk_emoji} Risco eletrolítico: {stats['electrolyte_risk']}\n"
    msg += f"{trend_emoji} Tendência energia: {stats['energy_trend']}\n"
    msg += f"⚖️ Peso: {stats['weight_trend']}\n\n"
    
    msg += f"*Médias Diárias (7 dias)*\n"
    msg += f"💪 Proteína: {stats['avg_daily_protein']:.0f}g\n"
    msg += f"🧈 Gordura: {stats['avg_daily_fat']:.0f}g\n"
    msg += f"🔥 Calorias: {stats['avg_daily_calories']:.0f}\n"
    if stats['avg_fat_protein_ratio'] > 0:
        msg += f"📐 Ratio G/P: {stats['avg_fat_protein_ratio']}\n"
    msg += "\n"
    
    if stats['fasting_frequency'] > 0:
        msg += f"*Jejum*\n"
        msg += f"📊 Frequência: {stats['fasting_frequency']:.1f}/semana\n"
        msg += f"⏱️ Média: {stats['avg_fasting_duration']:.1f}h\n\n"
    
    if stats['common_symptoms']:
        msg += f"*Sintomas Comuns*\n"
        for symptom in stats['common_symptoms']:
            msg += f"• {symptom}\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_menu_keyboard())


async def process_meal_input(update: Update, context, text: str, source: str = "text"):
    user = update.effective_user
    if not user:
        return
    
    database.add_user(user.id, user.username or "")
    await update.message.reply_text("🧠 Analisando...")
    
    llm_output = extract_meal_from_text(text)
    
    if not llm_output.get("is_food"):
        database.add_voice_note(user.id, text, False)
        await update.message.reply_text("📝 Nota salva (não identificado como comida).", reply_markup=get_menu_keyboard())
        return
    
    user_level = database.get_user_preferred_level(user.id)
    validated = validate_and_classify_meal(llm_output, user_level)
    
    meal_id = database.add_meal_event(
        user_id=user.id,
        dt=datetime.now(),
        ingredients=validated.get("ingredients", []),
        quantities=validated.get("quantities", []),
        carnivore_level=validated.get("carnivore_level", "strict"),
        breaks_fast=validated.get("breaks_fast", True),
        warnings=validated.get("warnings", []),
        calories=validated.get("calories", 0),
        protein_g=validated.get("protein_g", 0),
        fat_g=validated.get("fat_g", 0),
        carbs_g=validated.get("carbs_g", 0),
        summary=validated.get("summary", "Refeição"),
        source=source,
        processing_level=validated.get("processing_level", "whole"),
        needs_confirmation=validated.get("needs_confirmation", False),
    )
    
    database.add_voice_note(user.id, text, True)
    
    level_emoji = get_carnivore_level_emoji(CarnivoreLevel(validated.get("carnivore_level", "strict")))
    level_desc = get_carnivore_level_description(CarnivoreLevel(validated.get("carnivore_level", "strict")))
    
    msg = f"✅ *Registrado!*\n\n"
    msg += f"🍽️ {validated.get('summary')}\n"
    msg += f"{level_emoji} {level_desc}\n\n"
    msg += f"🔥 {validated.get('calories', 0):.0f} kcal\n"
    msg += f"💪 Proteína: {validated.get('protein_g', 0):.0f}g\n"
    msg += f"🧈 Gordura: {validated.get('fat_g', 0):.0f}g\n"
    
    if validated.get("ingredients"):
        msg += f"\n📋 *Ingredientes:* {', '.join(validated['ingredients'][:5])}"
    
    if validated.get("forbidden_ingredients"):
        msg += f"\n\n❌ *Proibidos detectados:* {', '.join(validated['forbidden_ingredients'])}"
    
    if validated.get("warnings"):
        msg += f"\n\n⚠️ *Avisos:*"
        for w in validated['warnings'][:3]:
            msg += f"\n• {w}"
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_menu_keyboard())


async def handle_voice(update: Update, context):
    voice = update.message.voice
    if not voice:
        return
    
    file = await context.bot.get_file(voice.file_id)
    path = f"/tmp/{voice.file_id}.oga"
    await file.download_to_drive(path)
    
    segments, _ = whisper_model.transcribe(path, language="pt")
    text = " ".join([s.text for s in segments])
    os.remove(path)
    
    await process_meal_input(update, context, text, source="voice")


async def handle_photo(update: Update, context):
    if not update.message.photo:
        return
    
    user = update.effective_user
    if not user:
        return
    
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    path = f"/tmp/{photo.file_id}.jpg"
    await file.download_to_drive(path)
    
    await update.message.reply_text("📸 Analisando imagem...")
    
    analysis = analyze_food_image(path)
    os.remove(path)
    
    if "error" in analysis:
        await update.message.reply_text(f"❌ Erro na análise: {analysis['error']}")
        return
    
    identified = analysis.get("identified_foods", [])
    animal_based = analysis.get("animal_based", [])
    plant_based = analysis.get("plant_based", [])
    carnivore_level = analysis.get("carnivore_level", "strict")
    macros = analysis.get("estimated_macros", {})
    
    user_level = database.get_user_preferred_level(user.id)
    all_ingredients = animal_based + plant_based
    target = CarnivoreLevel.STRICT if user_level == "strict" else CarnivoreLevel.RELAXED
    validation = validate_ingredients(all_ingredients, target)
    
    database.add_meal_event(
        user_id=user.id,
        dt=datetime.now(),
        ingredients=animal_based,
        quantities=[],
        carnivore_level=validation.carnivore_level.value,
        breaks_fast=True,
        warnings=validation.warnings + analysis.get("warnings", []),
        calories=macros.get("calories", 0),
        protein_g=macros.get("protein_g", 0),
        fat_g=macros.get("fat_g", 0),
        carbs_g=0,
        summary=", ".join(identified[:3]) if identified else "Foto analisada",
        source="photo",
        processing_level="whole",
        needs_confirmation=validation.needs_confirmation,
    )
    
    level_emoji = get_carnivore_level_emoji(validation.carnivore_level)
    level_desc = get_carnivore_level_description(validation.carnivore_level)
    
    msg = f"📸 *Análise da Foto*\n\n"
    msg += f"{level_emoji} {level_desc}\n\n"
    
    if identified:
        msg += f"🔍 *Identificado:* {', '.join(identified)}\n"
    
    if animal_based:
        msg += f"🥩 *Animal:* {', '.join(animal_based)}\n"
    
    if plant_based:
        msg += f"❌ *Vegetal:* {', '.join(plant_based)}\n"
    
    msg += f"\n🔥 ~{macros.get('calories', 0)} kcal\n"
    msg += f"💪 ~{macros.get('protein_g', 0)}g proteína\n"
    msg += f"🧈 ~{macros.get('fat_g', 0)}g gordura"
    
    if validation.warnings:
        msg += f"\n\n⚠️ *Avisos:*"
        for w in validation.warnings[:3]:
            msg += f"\n• {w}"
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_menu_keyboard())


async def report_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    args = context.args
    report_type = args[0].lower() if args else "daily"
    
    if report_type == "weekly":
        await send_weekly_report(update, user.id)
    elif report_type == "html":
        await send_html_report(update, user)
    else:
        await send_daily_report(update, user.id)


async def send_daily_report(update: Update, user_id: int):
    today = datetime.now().strftime('%Y-%m-%d')
    stats = database.get_daily_stats(user_id, today)
    meals = database.get_meal_events(user_id, today)
    symptoms = database.get_symptoms(user_id, today)
    active_fast = database.get_active_fast(user_id)
    goals = database.get_goals(user_id)
    
    msg = f"📊 *Relatório Diário*\n_{today}_\n\n"
    
    if not meals:
        msg += "🍽️ Nenhuma refeição registrada hoje.\n\n"
    else:
        msg += f"*Refeições ({stats['meal_count']})*\n"
        for m in meals:
            level_emoji = get_carnivore_level_emoji(CarnivoreLevel(m['carnivore_level']))
            msg += f"• {m['time']} - {m['summary'][:30]} {level_emoji}\n"
        msg += "\n"
    
    msg += f"*Macros*\n"
    msg += f"💪 Proteína: {stats['total_protein_g']:.0f}g"
    if goals:
        msg += f" / {goals['protein']}g"
    msg += f"\n🧈 Gordura: {stats['total_fat_g']:.0f}g"
    if goals:
        msg += f" / {goals['fat']}g"
    msg += f"\n🔥 Calorias: {stats['total_calories']:.0f}"
    if goals:
        msg += f" / {goals['calories']}"
    msg += "\n"
    
    if stats['fat_protein_ratio']:
        msg += f"📐 Ratio G/P: {stats['fat_protein_ratio']}\n"
    
    if stats['first_meal_time'] and stats['last_meal_time']:
        msg += f"\n*Janela Alimentar*\n"
        msg += f"⏰ {stats['first_meal_time']} → {stats['last_meal_time']}\n"
    
    if active_fast:
        start = datetime.fromisoformat(active_fast['start_time'])
        hours = (datetime.now() - start).total_seconds() / 3600
        msg += f"\n*Jejum Ativo*\n"
        msg += f"⏳ {hours:.1f} horas (desde {start.strftime('%H:%M')})\n"
    
    if symptoms:
        msg += f"\n*Sintomas ({len(symptoms)})*\n"
        for s in symptoms[:5]:
            severity_bar = "●" * s['severity'] + "○" * (5 - s['severity'])
            msg += f"• {s['symptom_type']} {severity_bar}\n"
    
    compliance_emoji = "🥩" if stats['carnivore_compliance'] == 100 else "⚠️"
    msg += f"\n{compliance_emoji} *Aderência:* {stats['carnivore_compliance']:.0f}%"
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_menu_keyboard())


async def send_weekly_report(update: Update, user_id: int):
    summary = database.get_weekly_summary(user_id)
    
    msg = f"📈 *Relatório Semanal*\n_Últimos 7 dias_\n\n"
    
    msg += f"*Resumo Geral*\n"
    msg += f"📅 Dias rastreados: {summary['days_tracked']}\n"
    msg += f"🍽️ Total refeições: {summary['total_meals']}\n"
    msg += f"🥩 Aderência: {summary['compliance']:.0f}%\n\n"
    
    msg += f"*Totais da Semana*\n"
    msg += f"🔥 {summary['total_calories']:.0f} kcal\n"
    msg += f"💪 {summary['total_protein']:.0f}g proteína\n"
    msg += f"🧈 {summary['total_fat']:.0f}g gordura\n\n"
    
    msg += f"*Médias Diárias*\n"
    msg += f"🔥 {summary['avg_daily_calories']:.0f} kcal/dia\n"
    msg += f"💪 {summary['avg_daily_protein']:.0f}g prot/dia\n"
    msg += f"🧈 {summary['avg_daily_fat']:.0f}g gord/dia\n\n"
    
    if summary['fasts_completed'] > 0:
        msg += f"*Jejuns*\n"
        msg += f"✅ {summary['fasts_completed']} completados\n"
        msg += f"⏱️ {summary['total_fasting_hours']:.1f}h total\n\n"
    
    if summary['symptoms_logged'] > 0:
        msg += f"*Sintomas ({summary['symptoms_logged']})*\n"
        for symptom, count in summary['top_symptoms']:
            msg += f"• {symptom}: {count}x\n"
        msg += "\n"
    
    if summary['weight_change'] != 0:
        trend = "📉" if summary['weight_change'] < 0 else "📈"
        msg += f"*Peso*\n{trend} {summary['weight_change']:+.1f} kg\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_menu_keyboard())


async def send_html_report(update: Update, user):
    username = user.username or "Carnivore"
    today = datetime.now().strftime('%Y-%m-%d')
    
    meals = database.get_meals(user.id, today)
    
    if not meals:
        await update.message.reply_text("Sem dados hoje para gerar relatório HTML! 🦁")
        return

    await update.message.reply_text("📄 Gerando relatório HTML...")
    
    total_prot = sum(m['macros'].get('protein', 0) for m in meals)
    total_fat = sum(m['macros'].get('fat', 0) for m in meals)
    total_kcal = sum(m['calories'] for m in meals)
    totals = {'protein': total_prot, 'fat': total_fat, 'calories': total_kcal}
    
    path = report_generator.generate_daily_report(username, today, meals, totals)
    
    await update.message.reply_document(
        document=open(path, 'rb'),
        filename=f"Relatorio_Carnivoro_{today}.html",
        caption=f"🦁 Seu relatório de {today}"
    )
    
    os.remove(path)


async def export_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "📤 *Exportar Dados*\n\n"
            "Uso: `/export <formato> [período]`\n\n"
            "*Formatos:*\n"
            "• `csv` - Planilha\n"
            "• `json` - Dados estruturados\n"
            "• `html` - Relatório visual\n\n"
            "*Períodos:*\n"
            "• `daily` - Hoje (padrão)\n"
            "• `weekly` - Últimos 7 dias\n\n"
            "Exemplo: `/export csv weekly`",
            parse_mode="Markdown"
        )
        return
    
    format_type = args[0].lower()
    period = args[1].lower() if len(args) > 1 else "daily"
    username = user.username or "Carnivore"
    
    if format_type not in ['csv', 'json', 'html']:
        await update.message.reply_text("❌ Formato inválido. Use: csv, json ou html")
        return
    
    await update.message.reply_text(f"📤 Exportando {format_type.upper()}...")
    
    if period == "weekly":
        summary = database.get_weekly_summary(user.id)
        meals = database.get_meals_history(user.id, 7)
    else:
        today = datetime.now().strftime('%Y-%m-%d')
        meals = database.get_meal_events(user.id, today)
        summary = database.get_daily_stats(user.id, today)
    
    if format_type == "csv":
        path = report_generator.export_to_csv(username, meals, period)
        filename = f"carnivore_export_{period}.csv"
    elif format_type == "json":
        export_data = {
            "meals": meals,
            "summary": summary,
        }
        path = report_generator.export_to_json(username, export_data, period)
        filename = f"carnivore_export_{period}.json"
    else:
        if period == "weekly":
            path = report_generator.generate_weekly_report(username, summary)
        else:
            today = datetime.now().strftime('%Y-%m-%d')
            totals = {
                'protein': summary.get('total_protein_g', 0),
                'fat': summary.get('total_fat_g', 0),
                'calories': summary.get('total_calories', 0),
            }
            path = report_generator.generate_daily_report(username, today, meals, totals)
        filename = f"carnivore_report_{period}.html"
    
    await update.message.reply_document(
        document=open(path, 'rb'),
        filename=filename,
        caption=f"🦁 Exportação {format_type.upper()} ({period})"
    )
    
    os.remove(path)


async def recipe_command(update: Update, context):
    user = update.effective_user
    if not user:
        return
    
    args = context.args
    preference = " ".join(args) if args else ""
    
    await update.message.reply_text("👨‍🍳 Criando receita carnívora...")
    
    user_level = database.get_user_preferred_level(user.id)
    
    prompt = f"""Gere uma receita carnívora {'estrita' if user_level == 'strict' else 'relaxada'}.

{'Preferência do usuário: ' + preference if preference else 'Sem preferência específica.'}

REGRAS OBRIGATÓRIAS:
- Máximo 4 ingredientes
- APENAS origem animal: carne, ovos, manteiga, banha, bacon
- PROIBIDO: vegetais, grãos, frutas, molhos, especiarias (exceto sal)
- Preferência por carne bovina ou de ruminantes
- Foco em simplicidade e saciedade

Responda em JSON:
{{
    "name": "Nome da receita",
    "ingredients": ["ingrediente1 com quantidade", "ingrediente2 com quantidade"],
    "steps": ["passo1", "passo2", "passo3"],
    "time_minutes": 20,
    "carnivore_level": "strict",
    "estimated_macros": {{
        "calories": 800,
        "protein_g": 50,
        "fat_g": 60
    }},
    "tips": "Dica opcional"
}}"""
    
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': prompts.SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ]
        )
        text = response['message']['content'].strip()
        
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        recipe = json.loads(text)
        
        msg = f"🍖 *{recipe.get('name', 'Receita Carnívora')}*\n\n"
        
        msg += "📋 *Ingredientes:*\n"
        for ing in recipe.get('ingredients', []):
            msg += f"• {ing}\n"
        
        msg += "\n👨‍🍳 *Preparo:*\n"
        for i, step in enumerate(recipe.get('steps', []), 1):
            msg += f"{i}. {step}\n"
        
        macros = recipe.get('estimated_macros', {})
        msg += f"\n📊 *Macros estimados:*\n"
        msg += f"🔥 {macros.get('calories', 0)} kcal\n"
        msg += f"💪 {macros.get('protein_g', 0)}g proteína\n"
        msg += f"🧈 {macros.get('fat_g', 0)}g gordura\n"
        
        if recipe.get('time_minutes'):
            msg += f"\n⏱️ Tempo: ~{recipe['time_minutes']} min"
        
        if recipe.get('tips'):
            msg += f"\n\n💡 *Dica:* {recipe['tips']}"
        
        level_emoji = "🥩" if recipe.get('carnivore_level') == 'strict' else "🧈"
        msg += f"\n\n{level_emoji} Nível: {recipe.get('carnivore_level', 'strict').upper()}"
        
    except json.JSONDecodeError:
        msg = f"🍖 *Receita Carnívora*\n\n{response['message']['content']}"
    except Exception as e:
        msg = f"❌ Erro ao gerar receita: {str(e)}\n\nTente novamente ou especifique uma preferência: `/recipe picanha`"
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_menu_keyboard())


def get_meal_plan(duration: str) -> str:
    topic = "UM DIA (Amanhã)" if duration == "day" else "UMA SEMANA (7 dias)"
    prompt = f"""Crie um plano de refeições carnívoro estrito para {topic}.

REGRAS:
- Apenas: carne, ovos, bacon, manteiga, banha, sal, água
- Proibido: vegetais, grãos, frutas, molhos
- Varie os cortes (Picanha, Contra-filé, Costela, etc)
- Estime calorias por refeição
- Use emojis
- Formato Markdown limpo"""
    
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': prompts.SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ]
        )
        return response['message']['content']
    except Exception as e:
        return f"Erro ao gerar plano: {str(e)}"


async def plan_tomorrow_command(update: Update, context):
    await update.message.reply_text("👨‍🍳 Criando menu carnívoro para amanhã...")
    plan = get_meal_plan("day")
    await update.message.reply_text(f"📅 *Menu para Amanhã:*\n\n{plan}", parse_mode="Markdown")


async def plan_week_command(update: Update, context):
    await update.message.reply_text("👨‍🍳 Elaborando estratégia semanal...")
    plan = get_meal_plan("week")
    await update.message.reply_text(f"🗓️ *Plano Semanal:*\n\n{plan}", parse_mode="Markdown")


async def handle_text(update: Update, context):
    if not update.message:
        return
    
    txt = update.message.text
    if not txt or txt.startswith("/"):
        return
    
    button_handlers = {
        "📊 Estatísticas": stats_command,
        "🍖 Sugestão": suggest_command,
        "🥗 Dieta Hoje": diet_command,
        "📄 Relatório HTML": report_command,
    }
    
    if txt in button_handlers:
        await button_handlers[txt](update, context)
    elif txt == "🎙️ Gravar":
        await update.message.reply_text("Envie um áudio agora!")
    elif txt == "📸 Foto":
        await update.message.reply_text("Envie uma foto da comida!")
    else:
        await process_meal_input(update, context, txt, source="text")


async def post_init(app):
    await setup_commands(app)


if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setgoals", set_goals_command))
    app.add_handler(CommandHandler("setlevel", set_level_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("metabolic", metabolic_command))
    app.add_handler(CommandHandler("suggest", suggest_command))
    app.add_handler(CommandHandler("diet", diet_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("recipe", recipe_command))
    app.add_handler(CommandHandler("plan_tomorrow", plan_tomorrow_command))
    app.add_handler(CommandHandler("plan_week", plan_week_command))
    app.add_handler(CommandHandler("notes", notes_command))
    app.add_handler(CommandHandler("fast", fast_command))
    app.add_handler(CommandHandler("faststatus", fast_status_command))
    app.add_handler(CommandHandler("symptom", symptom_command))
    app.add_handler(CommandHandler("symptoms", symptoms_today_command))
    app.add_handler(CommandHandler("weight", weight_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🦁 Carnivore Tracker Bot Rodando!")
    app.run_polling()
