import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters,
    CallbackContext
)
import re

# ===== SETUP AWAL =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== DATA CONFIG =====
TELEGRAM_TOKEN = "TOKEN_ANDA"  # Ganti dengan token bot
ADMIN_CHAT_ID = "ID_ADMIN"     # Chat ID admin untuk alert

# Template keyboard
PARAM_KEYBOARD = [['TD', 'HR'], ['TEMP', 'BB'], ['📤 Kirim Data']]
REPLY_MARKUP = ReplyKeyboardMarkup(PARAM_KEYBOARD, resize_keyboard=True)

# Penyimpanan sementara (bisa diganti database)
user_data = {}

# ===== FUNGSI VALIDASI =====
def validate_parameter(param, value):
    if param == 'TD':
        if not re.match(r'^\d{1,3}/\d{1,3}$', value):
            return "Format TD salah. Contoh: 120/80"
        sistol, diastol = map(int, value.split('/'))
        if sistol > 300 or diastol > 200:
            return "TD tidak valid (maks 300/200)"
    
    elif param == 'HR':
        if not value.isdigit():
            return "HR harus angka"
        hr = int(value)
        if hr < 30 or hr > 200:
            return "HR di luar rentang (30-200)"
    
    elif param == 'TEMP':
        try:
            temp = float(value)
            if temp < 35 or temp > 42:
                return "Suhu tidak normal (35-42°C)"
        except:
            return "Suhu harus angka (contoh: 36.5)"
    
    return None

# ===== FUNGSI KLASIFIKASI RISIKO =====
def classify_risk(data):
    risks = []
    
    if 'TD' in data:
        sistol, diastol = map(int, data['TD'].split('/'))
        if sistol >= 180 or diastol >= 120:
            risks.append("🆘 KRISIS HIPERTENSI")
        elif sistol >= 140 or diastol >= 90:
            risks.append("⚠️ HIPERTENSI STAGE 2")
    
    if 'HR' in data:
        hr = int(data['HR'])
        if hr > 100:
            risks.append("⚠️ DETAK JANTUNG TINGGI")
        elif hr < 60:
            risks.append("⚠️ DETAK JANTUNG RENDAH")
    
    if 'TEMP' in data:
        temp = float(data['TEMP'])
        if temp > 37.5:
            risks.append("⚠️ DEMAM")
    
    return "✅ SEHAT" if not risks else "\n".join(risks)

# ===== HANDLER PERINTAH =====
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_markdown_v2(
        fr"Hai {user.mention_markdown_v2()}\! Selamat datang di *Sistem SIGAR* 🏥\n"
        "Silakan input data kesehatan Anda:",
        reply_markup=REPLY_MARKUP
    )
    # Reset data pengguna
    user_data[user.id] = {}

def handle_parameter(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    
    # Jika pengguna memilih "Kirim Data"
    if text == '📤 Kirim Data':
        if user_id not in user_data or not user_data[user_id]:
            update.message.reply_text("❌ Belum ada data yang dimasukkan")
            return
        
        # Klasifikasi risiko
        risk = classify_risk(user_data[user_id])
        
        # Format laporan
        report = "📋 **Laporan Kesehatan Anda**\n"
        for param, value in user_data[user_id].items():
            report += f"{param}: {value}\n"
        report += f"\n**Hasil Analisis:**\n{risk}"
        
        update.message.reply_markdown(report)
        
        # Kirim alert ke admin jika risiko tinggi
        if "🆘" in risk:
            alert = f"🚨 ALERT! Pengguna {user_id}:\n"
            alert += "\n".join([f"{k}: {v}" for k,v in user_data[user_id].items()])
            context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=alert)
        
        # Reset data
        user_data[user_id] = {}
        return
    
    # Jika pengguna memilih parameter
    if text in ['TD', 'HR', 'TEMP', 'BB']:
        context.user_data['current_param'] = text
        update.message.reply_text(f"Masukkan nilai {text}:\n(Contoh: {'120/80' if text=='TD' else '70'})")
        return

def handle_value(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    current_param = context.user_data.get('current_param')
    
    if not current_param:
        update.message.reply_text("Silakan pilih parameter terlebih dahulu")
        return
    
    # Validasi input
    error_msg = validate_parameter(current_param, text)
    if error_msg:
        update.message.reply_text(error_msg)
        return
    
    # Simpan data
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id][current_param] = text
    del context.user_data['current_param']
    
    update.message.reply_text(
        f"✅ {current_param} = {text} tersimpan\n"
        "Lanjutkan input atau kirim data",
        reply_markup=REPLY_MARKUP
    )

def cancel(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    update.message.reply_text("❌ Input dibatalkan", reply_markup=REPLY_MARKUP)

# ===== MAIN =====
def main() -> None:
    updater = Updater(TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher

    # Handler perintah
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("cancel", cancel))
    
    # Handler pesan
    dispatcher.add_handler(MessageHandler(
        Filters.regex(r'^(TD|HR|TEMP|BB|📤 Kirim Data)$'), 
        handle_parameter
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command, 
        handle_value
    ))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()