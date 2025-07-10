import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# --- 24/7 चलाने के लिए वेब सर्वर (Render के लिए) ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080) # Render इसी पोर्ट का उपयोग करता है

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- कॉन्फ़िगरेशन (Render के Environment Variables से) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
DATA_FILE = "loot_submissions.json"

# --- लॉगिंग सेटअप ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- स्टेट्स (बातचीत के चरण) ---
CHECK_JOIN, ASK_NAME, GET_DEAL, GET_SCREENSHOT = range(4)

# --- सहायक फंक्शन्स ---
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(new_entry):
    data = load_data()
    data.append(new_entry)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME.lstrip('@')}", user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

# --- बॉट के फंक्शन्स ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    is_member = await check_membership(user.id, context)
    
    if is_member:
        keyboard = [[InlineKeyboardButton("🚀 सबमिशन शुरू करें", callback_data="start_submission")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_html(
            f"👋 <b>नमस्ते {user.first_name}!</b>\n\nमैं आपका Loot Submit Bot हूँ। 💥\n"
            "अपनी खोजी हुई लूट को सबमिट करने के लिए नीचे दिए गए बटन पर क्लिक करें।",
            reply_markup=reply_markup
        )
        return ASK_NAME
    else:
        keyboard = [
            [InlineKeyboardButton("🔗 चैनल ज्वाइन करें", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton("✅ मैंने ज्वाइन कर लिया है", callback_data="check_join_again")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "नमस्ते! लूट सबमिट करने से पहले, कृपया हमारा टेलीग्राम चैनल ज्वाइन करें।",
            reply_markup=reply_markup
        )
        return CHECK_JOIN

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user = query.from_user

    is_member = await check_membership(user.id, context)
    
    if is_member:
        keyboard = [[InlineKeyboardButton("🚀 सबमिशन शुरू करें", callback_data="start_submission")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"धन्यवाद! अब आप सबमिशन शुरू कर सकते हैं।",
            reply_markup=reply_markup
        )
        return ASK_NAME
    else:
        await query.answer("आपने अभी तक चैनल ज्वाइन नहीं किया है। कृपया पहले चैनल ज्वाइन करें।", show_alert=True)
        return CHECK_JOIN

async def start_submission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="बहुत बढ़िया! चलिए शुरू करते हैं।\n\nसबसे पहले, आपका नाम क्या है?")
    return ASK_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_name = update.message.text
    context.user_data['name'] = user_name
    await update.message.reply_text(
        f"ठीक है, {user_name}!\n\nअब, आपने कौन-सी deal loot की? उसका नाम या प्रोडक्ट का लिंक मुझे भेजें।"
    )
    return GET_DEAL

async def get_deal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    deal_info = update.message.text
    context.user_data['deal'] = deal_info
    await update.message.reply_text(
        "शानदार! अब उस प्रोडक्ट का एक स्क्रीनशॉट भेजिए। 📸"
    )
    return GET_SCREENSHOT

async def get_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    context.user_data['screenshot_id'] = photo_file.file_id
    await update.message.reply_html(
        "🎉 <b>बहुत-बहुत धन्यवाद!</b> 🎉\n\n"
        "आपकी एंट्री सफलतापूर्वक सबमिट हो गई है।\n"
        "विजेता की घोषणा हर <b>रविवार रात 9 बजे</b> हमारे चैनल पर की जाएगी। All the best! 👍"
    )
    user_info = update.effective_user
    submission_details = (
        f"<b>🔥 नया लूट सबमिशन! 🔥</b>\n\n"
        f"<b>सबमिट करने वाला:</b> @{user_info.username or 'N/A'} (ID: {user_info.id})\n"
        f"<b>नाम (जो बताया गया):</b> {context.user_data.get('name')}\n"
        f"<b>डील का विवरण/लिंक:</b>\n{context.user_data.get('deal')}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=submission_details, parse_mode=ParseMode.HTML)
    await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=context.user_data['screenshot_id'])
    
    entry = {
        "user_id": user_info.id,
        "telegram_username": user_info.username,
        "provided_name": context.user_data.get('name'),
        "deal_info": context.user_data.get('deal'),
        "screenshot_file_id": context.user_data.get('screenshot_id'),
        "timestamp": update.message.date.isoformat()
    }
    save_data(entry)
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("कोई बात नहीं। जब आप तैयार हों, तो /start से दोबारा शुरू कर सकते हैं।")
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHECK_JOIN: [CallbackQueryHandler(check_join_callback, pattern="^check_join_again$")],
            ASK_NAME: [
                CallbackQueryHandler(start_submission_callback, pattern="^start_submission$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
            ],
            GET_DEAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_deal)],
            GET_SCREENSHOT: [MessageHandler(filters.PHOTO, get_screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    print(">>> Your service is live 🚀")
    print(f">>> Available at your primary URL https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}")
    
    application.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
