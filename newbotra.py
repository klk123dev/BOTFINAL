import requests
import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import socket
import threading

# ===== CONFIGURACIÓN ANTICONFLICTOS =====
try:
    # Bloqueo para evitar múltiples instancias
    lock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    lock.bind('\0ticketbot_lock')
except socket.error:
    print("🛑 ¡Ya hay una instancia en ejecución!")
    exit(1)

# Configuración
TOKEN = "7220704086:AAHIooBbtT-Tei70ZodcsJY35RdE-Vp-oTA"  # 👈 Reemplaza esto
monitored_events = {}

# Logging mejorado
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# ===== FUNCIONES PRINCIPALES =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎟️ **Monitor de Eventos RA**\n\n"
        "Envía la URL de un evento SOLD OUT para monitorearlo cada 5 segundos."
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    url = update.message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("⚠️ URL debe comenzar con http:// o https://")
        return
    
    monitored_events[chat_id] = url
    await update.message.reply_text(f"🔍 Monitoreando:\n{url}")
    
    threading.Thread(
        target=check_availability,
        args=(chat_id, url),
        daemon=True
    ).start()

def check_availability(chat_id: int, url: str):
    bot = Bot(token=TOKEN)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    while chat_id in monitored_events:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if not any(
                kw in response.text.lower() 
                for kw in ["sold out", "agotado", "no tickets"]
            ):
                asyncio.run(
                    bot.send_message(
                        chat_id=chat_id,
                        text=f"🚨 ¡ENTRADAS DISPONIBLES! 🎟️\n{url}"
                    )
                )
                del monitored_events[chat_id]
                break
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error en {url}: {str(e)}")
            time.sleep(30)

# ===== CONFIGURACIÓN DEL BOT =====
def main():
    application = Application.builder() \
        .token(TOKEN) \
        .concurrent_updates(True) \
        .post_init(lambda _: logger.info("✅ Bot iniciado correctamente")) \
        .build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # Configuración especial para Render
    application.run_polling(
        close_loop=False,
        stop_signals=None,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()