import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.error import BadRequest

# Logging setup for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration (Render पर Environment Variables में सेट करें) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# अपने चैनल का यूजरनेम @ के साथ लिखें (जैसे: '@MyLootChannel') या ID (जैसे: -100123456789)
CHANNEL_ID = os.environ.get("CHANNEL_ID") 

# --- Conversation States ---
# बातचीत के अलग-अलग पड़ाव के लिए States
CHECK_MEMBERSHIP, GET_NAME, GET_DEAL, GET_SCREENSHOT = range(4)

# --- Helper Function: To check if user is in the channel ---
# यह फंक्शन चेक करेगा कि यूजर चैनल का मेंबर है या नहीं
async def is_user_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        # अगर यूजर मेंबर, एडमिन या क्रिएटर है तो True
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            return False
    except BadRequest:
        # अगर बॉट चैनल में एडमिन नहीं है या चैनल प्राइवेट है
        logger.error(f"Error: Bot is not an administrator in the channel {CHANNEL_ID} or channel is incorrect.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while checking membership: {e}")
        return False

# --- Command Handlers ---

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.info(f"User {user.first_name} ({user.id}) started the bot.")
    
    # चेक करें कि यूजर चैनल का मेंबर है या नहीं
    is_member = await is_user_member(context, user.id)

    if is_member:
        # अगर मेंबर है तो सीधा सवालों वाला मैसेज दिखाएँ
        keyboard = [[InlineKeyboardButton("🚀 Let's Go!", callback_data='start_submission')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_html(
            "👇 नीचे दिए गए सवालों का जवाब दीजिए:",
            reply_markup=reply_markup
        )
        return CHECK_MEMBERSHIP
    else:
        # अगर मेंबर नहीं है तो ज्वाइन करने के लिए कहें
        keyboard = [[InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
                    [InlineKeyboardButton("🔄 Joined! Check Again", callback_data='check_join')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_html(
            f"👋 नमस्ते {user.mention_html()}!\n\nमैं आपका <b>Loot Submit Bot</b> हूँ 💥\n\n"
            "आगे बढ़ने के लिए, कृपया हमारा चैनल जॉइन करें।",
            reply_markup=reply_markup
        )
        return CHECK_MEMBERSHIP

# --- Callback Query Handlers (Button Clicks) ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer() # बटन पर लोडिंग बंद करने के लिए
    user_id = query.from_user.id
    
    # अगर यूजर ने "Joined! Check Again" बटन दबाया
    if query.data == 'check_join':
        is_member = await is_user_member(context, user_id)
        if is_member:
            keyboard = [[InlineKeyboardButton("🚀 Let's Go!", callback_data='start_submission')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text="बहुत बढ़िया! आपने चैनल जॉइन कर लिया है।\n\n👇 नीचे दिए गए सवालों का जवाब दीजिए:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return CHECK_MEMBERSHIP
        else:
            await query.answer("आपने अभी तक चैनल जॉइन नहीं किया है। कृपया पहले जॉइन करें।", show_alert=True)
            return CHECK_MEMBERSHIP

    # अगर यूजर ने "Let's Go!" बटन दबाया
    elif query.data == 'start_submission':
        await query.edit_message_text(text="शानदार! चलिए शुरू करते हैं।")
        await query.message.reply_text("आपका नाम क्या है?")
        return GET_NAME

# --- Message Handlers for Conversation ---

# 1. नाम लेना
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_name = update.message.text
    context.user_data['name'] = user_name
    logger.info(f"Name received: {user_name}")
    await update.message.reply_text("बहुत अच्छे! अब बताएँ, आपने कौन-सी deal loot की? \nउसका नाम या link मुझे send करें।")
    return GET_DEAL

# 2. डील का नाम/लिंक लेना
async def get_deal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    deal_info = update.message.text
    context.user_data['deal'] = deal_info
    logger.info(f"Deal received: {deal_info}")
    await update.message.reply_text("अब उस प्रोडक्ट का Screenshot भेजिए 📸")
    return GET_SCREENSHOT

# 3. स्क्रीनशॉट लेना
async def get_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    photo_file = await update.message.photo[-1].get_file()
    # आप चाहें तो फोटो को कहीं सेव या फॉरवर्ड कर सकते हैं
    # await photo_file.download_to_drive('user_screenshot.jpg')
    
    logger.info(f"Screenshot received from {context.user_data.get('name')}")

    # धन्यवाद वाला मैसेज
    await update.message.reply_html(
        "🎉 <b>Thank You So Much!</b> 🎉\n\n"
        "आपकी सबमिशन हमें मिल गयी है। आपने बहुत बढ़िया काम किया! 🙌\n\n"
        "अब बस थोड़ा इंतज़ार करें। विनर का अनाउंसमेंट <b>Sunday रात 9 बजे</b> हमारे चैनल पर होगा।\n\n"
        "Good Luck! 🍀"
    )
    
    # बातचीत का डेटा साफ़ करना
    context.user_data.clear()
    return ConversationHandler.END

# /cancel Command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("कोई बात नहीं। प्रक्रिया रद्द कर दी गई है।")
    context.user_data.clear()
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("BOT_TOKEN or CHANNEL_ID environment variable not set!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHECK_MEMBERSHIP: [
                CallbackQueryHandler(button_handler, pattern='^check_join$'),
                CallbackQueryHandler(button_handler, pattern='^start_submission$')
            ],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_DEAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_deal)],
            GET_SCREENSHOT: [MessageHandler(filters.PHOTO, get_screenshot)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    
    # बॉट को शुरू करें
    application.run_polling()

if __name__ == '__main__':
    main()
