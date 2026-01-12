from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton
import json, os, subprocess, asyncio, logging
from datetime import datetime
from google import genai
from PIL import Image
from faster_whisper import WhisperModel
import ollama
import database
import report_generator
from dotenv import load_dotenv

load_dotenv()

# Configuração de Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configura Gemini (mantido para análise de fotos)
client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-1.5-flash"

# Modelo Local Ollama (para texto e raciocínio)
OLLAMA_MODEL = "mistral"

# Carrega Faster-Whisper
logger.info("Carregando Faster-Whisper (modelo small)...")
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
logger.info("Faster-Whisper carregado!")

# --- FUNÇÕES AUXILIARES DE ANÁLISE ---

def transcribe_audio_whisper(audio_path):
    """Transcreve áudio usando Faster-Whisper (local)"""
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

def analyze_transcription_for_food(transcription):
    """Usa Ollama local para analisar comida e extrair macros"""
    logger.info("Iniciando análise de comida com Ollama...")
    try:
        prompt = f"""Você é um assistente focado em DIETA CARNÍVORA e Nutrição.
Analise: "{transcription}"

Se não for comida, marque "is_food": false.
Se for comida, estime Calorias, Proteína e Gordura.

Responda ESTRITAMENTE em JSON:
{{
    "is_food": true/false,
    "summary": "Nome do prato",
    "is_carnivore": true/false,
    "calories": 0,
    "macros": {{ "protein": 0, "fat": 0, "carbs": 0 }}
}}"""

        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        text = response['message']['content'].strip()
        
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"Erro no Ollama (Nutrição): {str(e)}")
        return {"is_food": False, "calories": 0, "macros": {}}

def get_carnivore_suggestion(remaining_cal, remaining_prot, remaining_fat):
    """Pede sugestão ao Ollama baseada no que falta"""
    try:
        prompt = f"""Sou seu aluno da Dieta Carnívora.
Ainda preciso comer hoje:
{remaining_cal} kcal
{remaining_prot}g de proteína
{remaining_fat}g de gordura.

Sugira UMA única refeição carnívora (apenas carne/ovos/laticínios) que se aproxime desses números.
Seja direto e motivador. Dê o nome do prato e por que ele é bom."""
        
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        return "Coma bife com ovos. Não tem erro."

def get_ai_analysis(text):
    """Ollama Reasoning"""
    # ... (manter lógica anterior ou simplificar se necessário)
    try:
        prompt = f"""Guru Carnívoro analisa: "{text}".
Dê veredito curto sobre se é "Puro" (Carnívoro) ou "Lixo" (Plantas).
Dê nota 0-10.
"""
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception:
        return "Análise indisponível."

def analyze_food_image(image_path):
    """Gemini Vision"""
    try:
        img = Image.open(image_path)
        prompt = """Analise imagem. Estime calorias e macros (Proteina, Gordura). É Carnívoro?
Retorne JSON: {"summary": "...", "calories": 0, "protein": 0, "fat": 0, "is_carnivore": true}"""
        response = client.models.generate_content(model=GEMINI_MODEL, contents=[prompt, img])
        return response.text # Gemini retorna texto, precisaria parsear melhor para DB, mas vamos salvar o texto bruto no summary por enquanto se falhar
    except Exception as e:
        return f"Erro Vision: {str(e)}"

# --- COMANDOS DO BOT ---

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
        BotCommand("setgoals", "Definir Metas"),
        BotCommand("stats", "Ver Progresso"),
        BotCommand("diet", "Diário"),
        BotCommand("report", "Baixar Relatório HTML"),
        BotCommand("suggest", "Sugestão"),
    ]
    await app.bot.set_my_commands(commands)

async def start(update: Update, context):
    user = update.effective_user
    database.add_user(user.id, user.username)
    await update.message.reply_text(
        "🦁 *Modo Carnívoro Ativado*\n\n"
        "Comandos:\n"
        "`/setgoals 2000 150 140` -> Define metas (Kcal, Prot, Fat)\n"
        "`/stats` -> Vê seu progresso diário\n"
        "`/suggest` -> O que comer agora?\n\n"
        "Envie Áudio ou Foto para registrar!",
        parse_mode="Markdown", reply_markup=get_menu_keyboard()
    )

async def set_goals_command(update: Update, context):
    try:
        # /setgoals 2000 150 140
        args = context.args
        if len(args) != 3:
            await update.message.reply_text("Uso correto: /setgoals <kcal> <prot> <gordura>\nEx: /setgoals 2000 160 140")
            return
        
        kcal, prot, fat = map(int, args)
        database.set_goals(update.effective_user.id, kcal, prot, fat)
        await update.message.reply_text(f"🎯 *Metas Definidas!*\n\n🔥 Calorias: {kcal}\n💪 Proteína: {prot}g\n🧈 Gordura: {fat}g", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("Por favor use apenas números.")

async def stats_command(update: Update, context):
    user_id = update.effective_user.id
    today = datetime.now().strftime('%Y-%m-%d')
    
    goals = database.get_goals(user_id)
    meals = database.get_meals(user_id, today)
    
    total_kcal = sum(m['calories'] for m in meals)
    total_prot = sum(m['macros'].get('protein', 0) for m in meals)
    total_fat = sum(m['macros'].get('fat', 0) for m in meals)
    
    msg = f"📊 *Consumo de Hoje ({today})*\n\n"
    
    if goals:
        # Modo com Metas
        def barra(atual, total):
            if total == 0: return "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%"
            perc = min(100, int((atual/total)*100))
            chars = int(perc/10)
            return "🟩" * chars + "⬜" * (10 - chars) + f" {perc}%"

        msg += f"🔥 *Kcal*: {total_kcal}/{goals['calories']}\n{barra(total_kcal, goals['calories'])}\n\n"
        msg += f"💪 *Prot*: {total_prot}/{goals['protein']}g\n{barra(total_prot, goals['protein'])}\n\n"
        msg += f"🧈 *Gord*: {total_fat}/{goals['fat']}g\n{barra(total_fat, goals['fat'])}\n\n"
        
        if total_prot >= goals['protein']:
            msg += "🏆 Meta de proteína batida!"
    else:
        # Modo sem Metas (Apenas Rastreamento)
        msg += "⚠️ _Sem metas definidas (use /setgoals para ativar)_\n\n"
        msg += f"🔥 *Kcal*: {total_kcal}\n"
        msg += f"💪 *Prot*: {total_prot}g\n"
        msg += f"🧈 *Gord*: {total_fat}g\n"
        msg += "\n🦁 *Continue firme no Carnívoro!*"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def suggest_command(update: Update, context):
    user_id = update.effective_user.id
    today = datetime.now().strftime('%Y-%m-%d')
    goals = database.get_goals(user_id)
    
    await update.message.reply_text("🤔 Consultando o Guru...")
    
    if goals:
        meals = database.get_meals(user_id, today)
        total_kcal = sum(m['calories'] for m in meals)
        total_prot = sum(m['macros'].get('protein', 0) for m in meals)
        total_fat = sum(m['macros'].get('fat', 0) for m in meals)
        
        rem_kcal = max(0, goals['calories'] - total_kcal)
        rem_prot = max(0, goals['protein'] - total_prot)
        rem_fat = max(0, goals['fat'] - total_fat)
        
        suggestion = get_carnivore_suggestion(rem_kcal, rem_prot, rem_fat)
    else:
        # Sugestão Genérica
        try:
            prompt = "Sugira uma refeição carnívora clássica e deliciosa. Dê uma dica curta."
            response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
            suggestion = response['message']['content']
        except:
            suggestion = "Ribeye com manteiga e sal. Clássico."

    await update.message.reply_text(f"🍖 *Sugestão do Guru:*\n\n{suggestion}", parse_mode="Markdown")

async def diet_command(update: Update, context):
    user_id = update.effective_user.id
    today = datetime.now().strftime('%Y-%m-%d')
    meals = database.get_meals(user_id, today)
    
    if not meals:
        await update.message.reply_text("🥗 Nada registrado hoje. Envie fotos ou áudios!", reply_markup=get_menu_keyboard())
        return
    
    # Monta o relatório
    lines = []
    total_prot = 0
    total_fat = 0
    
    for m in meals:
        prot = m['macros'].get('protein', 0)
        fat = m['macros'].get('fat', 0)
        total_prot += prot
        total_fat += fat
        
        icon = '📸' if m['source']=='photo' else '🎙️'
        carnivore_tag = '🥩' if m['is_carnivore'] else '⚠️'
        
        lines.append(f"• {m['time']} {icon} {m['summary']} {carnivore_tag}\n   └ P: {prot}g | G: {fat}g")

    summary = "\n".join(lines)
    
    msg = f"🦁 *Diário Carnívoro ({today})*\n\n{summary}\n\n"
    msg += f"💪 *Total Proteína*: {total_prot}g\n"
    msg += f"🧈 *Total Gordura*: {total_fat}g"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def notes_command(update: Update, context):
    user_id = update.effective_user.id
    logger.info(f"Consultando notas para user_id: {user_id}")
    today = datetime.now().strftime('%Y-%m-%d')
    notes = database.get_voice_notes(user_id, today)
    
    if not notes:
        await update.message.reply_text("📝 Nenhuma nota hoje.", reply_markup=get_menu_keyboard())
        return
    
    text = "\n\n".join([f"• {n['time']} {'🍽️' if n['food_detected'] else '📝'}: {n['transcription'][:100]}..." for n in notes])
    await update.message.reply_text(f"🎙️ *Notas {today}*\n\n{text}", parse_mode="Markdown")

async def process_text_or_voice(update: Update, context, text, duration=0):
    user_id = update.effective_user.id
    database.add_user(user_id, update.effective_user.username)
    
    await update.message.reply_text("🧠 Processando...")
    
    # Análise estruturada
    info = analyze_transcription_for_food(text)
    
    if info.get("is_food"):
        database.add_meal(
            user_id,
            info.get("summary", "Refeição"),
            info.get("calories", 0),
            "audio" if duration > 0 else "text",
            macros=info.get("macros", {})
        )
        # Salvar nota também
        database.add_voice_note(user_id, text, True)
        
        await update.message.reply_text(
            f"✅ *Registrado:*\n"
            f"🍽️ {info.get('summary')}\n"
            f"🔥 {info.get('calories')} kcal | P: {info.get('macros', {}).get('protein',0)}g | G: {info.get('macros', {}).get('fat',0)}g",
            parse_mode="Markdown", reply_markup=get_menu_keyboard()
        )
    else:
        # Apenas nota
        database.add_voice_note(user_id, text, False)
        await update.message.reply_text("📝 Nota salva.", reply_markup=get_menu_keyboard())

async def handle_voice(update: Update, context):
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    path = f"/tmp/{voice.file_id}.oga"
    await file.download_to_drive(path)
    # Whisper
    segments, _ = whisper_model.transcribe(path, language="pt")
    text = " ".join([s.text for s in segments])
    os.remove(path)
    await process_text_or_voice(update, context, text, duration=1)

async def handle_photo(update: Update, context):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    path = f"/tmp/{photo.file_id}.jpg"
    await file.download_to_drive(path)
    
    await update.message.reply_text("📸 Analisando...")
    # Aqui idealmente usaríamos o JSON do Gemini se ele retornasse estruturado
    # Para simplificar agora, vamos usar um placeholder ou parser simples
    analysis_text = analyze_food_image(path)
    os.remove(path)
    
    # Tenta extrair JSON do texto do Gemini se possível, senão salva texto bruto
    user_id = update.effective_user.id
    database.add_meal(user_id, "Foto (Ver Detalhes)", 0, "photo", macros={"raw": analysis_text})
    
    await update.message.reply_text(f"📸 *Análise da Foto:*\n{analysis_text}", parse_mode="Markdown")

import report_generator

# ... imports ...

async def report_command(update: Update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Carnivore"
    today = datetime.now().strftime('%Y-%m-%d')
    
    meals = database.get_meals(user_id, today)
    
    if not meals:
        await update.message.reply_text("Sem dados hoje para gerar relatório! 🦁")
        return

    await update.message.reply_text("📄 Gerando relatório HTML...")
    
    # Calcula totais
    total_prot = sum(m['macros'].get('protein', 0) for m in meals)
    total_fat = sum(m['macros'].get('fat', 0) for m in meals)
    total_kcal = sum(m['calories'] for m in meals)
    totals = {'protein': total_prot, 'fat': total_fat, 'calories': total_kcal}
    
    # Gera
    path = report_generator.generate_daily_report(username, today, meals, totals)
    
    # Envia
    await update.message.reply_document(
        document=open(path, 'rb'),
        filename=f"Relatorio_Carnivoro_{today}.html",
        caption=f"🦁 Seu relatório de {today}"
    )
    
    # Limpa
    os.remove(path)

async def handle_text(update: Update, context):
    txt = update.message.text
    if txt.startswith("/"): return
    if txt == "📊 Estatísticas": await stats_command(update, context)
    elif txt == "🍖 Sugestão": await suggest_command(update, context)
    elif txt == "🥗 Dieta Hoje": await diet_command(update, context)
    elif txt == "📄 Relatório HTML": await report_command(update, context)
    elif txt == "🎙️ Gravar": await update.message.reply_text("Envie um áudio agora!")
    elif txt == "📸 Foto": await update.message.reply_text("Envie uma foto agora!")
    else: await process_text_or_voice(update, context, txt)

# ... (Menu Update) ...
def get_menu_keyboard():
    keyboard = [
        [KeyboardButton("🎙️ Gravar"), KeyboardButton("📸 Foto")],
        [KeyboardButton("🥗 Dieta Hoje"), KeyboardButton("📊 Estatísticas")],
        [KeyboardButton("🍖 Sugestão"), KeyboardButton("📄 Relatório HTML")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_meal_plan(duration):
    """Gera plano de refeições com Ollama"""
    topic = "UM DIA (Amanhã)" if duration == "day" else "UMA SEMANA (7 dias)"
    prompt = f"""Você é um Chef e Nutricionista Carnívoro.
Crie um plano de refeições estrito (apenas carne, ovos, bacon, laticínios, água) para {topic}.
Estruture com emojis.
Seja criativo com os cortes de carne (Contra-filé, Picanha, Costela, etc).
Para cada dia/refeição, estime as calorias aproximadas.
Formato Markdown limpo."""
    
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except Exception as e:
        return f"Erro ao gerar plano: {str(e)}"

async def plan_tomorrow_command(update: Update, context):
    await update.message.reply_text("👨‍🍳 Criando menu perfeito para amanhã...")
    plan = get_meal_plan("day")
    await update.message.reply_text(f"📅 *Seu Menu para Amanhã:*\n\n{plan}", parse_mode="Markdown")

async def plan_week_command(update: Update, context):
    await update.message.reply_text("👨‍🍳 Elaborando estratégia semanal (isso pode levar alguns segundos)...")
    plan = get_meal_plan("week")
    await update.message.reply_text(f"🗓️ *Plano Semanal Carnívoro:*\n\n{plan}", parse_mode="Markdown")

async def setup_commands(app):
    commands = [
        BotCommand("start", "Início"),
        BotCommand("setgoals", "Definir Metas"),
        BotCommand("stats", "Ver Progresso"),
        BotCommand("diet", "Diário"),
        BotCommand("report", "Baixar Relatório HTML"),
        BotCommand("plan_tomorrow", "Menu Amanhã"),
        BotCommand("plan_week", "Menu Semanal"),
    ]
    await app.bot.set_my_commands(commands)
async def post_init(app):
    await setup_commands(app)
if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setgoals", set_goals_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("suggest", suggest_command))
    app.add_handler(CommandHandler("diet", diet_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("plan_tomorrow", plan_tomorrow_command))
    app.add_handler(CommandHandler("plan_week", plan_week_command))
    app.add_handler(CommandHandler("notes", notes_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot Rodando!")
    app.run_polling()
