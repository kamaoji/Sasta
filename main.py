import os
import logging
from telegram import Update, ChatMember
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from telegram.error import TelegramError

# Enable logging (Good practice for debugging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Yeh values aapko Environment Variables me set karni hongi
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME") # Example: "@mychannel"
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Conversation states
ASK_NAME, ASK_DEAL, ASK_SCREENSHOT = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        # FIX: Using the library's built-in async method instead of 'requests'
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user.id)
        
        # Check if the user is a member, administrator, or creator
        if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
            raise TelegramError("User not a member")

    except TelegramError:
        # This will catch errors if the bot is not an admin in the channel or user is not a member
        join_link = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
        await update.message.reply_text(
            f"❌ इस बॉट का उपयोग करने के लिए, पहले हमारे चैनल को जॉइन करें:\n"
            f"👉 {join_link}\n\n"
            f"ज्वाइन करने के बाद, दोबारा /start टाइप करें।"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"An error occurred in start command: {e}")
        await update.message.reply_text("कुछ समस्या आ गई है। कृपया बाद में प्रयास करें।")
        return ConversationHandler.END

    await update.message.reply_text("स्वागत है! 🙏\n\n👇 नीचे दिए गए सवालों का जवाब दीजिए:\n\n1) अपना नाम बताइए:")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("2) आपने कौन-सी deal लूटी? उसका नाम या लिंक भेजिए:")
    return ASK_DEAL

async def ask_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["deal"] = update.message.text
    await update.message.reply_text("3) बहुत बढ़िया! अब उस deal का Screenshot भेजिए 📸")
    return ASK_SCREENSHOT

async def ask_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if a photo was sent
    if not update.message.photo:
        await update.message.reply_text("❌ यह एक फोटो नहीं है। कृपया एक स्क्रीनशॉट भेजें।")
        return ASK_SCREENSHOT # Stay in the same state

    photo_id = update.message.photo[-1].file_id
    name = context.user_data.get("name", "N/A")
    deal = context.user_data.get("deal", "N/A")

    caption_text = (
        f"🎉 **नई लूट एंट्री** 🎉\n\n"
        f"👤 **नाम:** {name}\n"
        f"🛍️ **डील:** {deal}"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID, 
        photo=photo_id,
        caption=caption_text,
        parse_mode='Markdown'
    )
    
    await update.message.reply_text(
        "✅ धन्यवाद! आपकी एंट्री हमें मिल गई है।\n"
        "🏆 विजेता की घोषणा रविवार रात 9 बजे की जाएगी!"
    )

    # Clear user_data after conversation ends
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⛔️ प्रक्रिया रद्द कर दी गई है।")
    # Clear user_data on cancel
    context.user_data.clear()
    return ConversationHandler.END

def main():
    if not all([BOT_TOKEN, CHANNEL_USERNAME, ADMIN_ID]):
        logger.error("BOT_TOKEN, CHANNEL_USERNAME, and ADMIN_ID environment variables must be set.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_DEAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deal)],
            ASK_SCREENSHOT: [MessageHandler(filters.PHOTO & ~filters.COMMAND, ask_screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        # Add a timeout for the conversation
        conversation_timeout=600 # 10 minutes
    )

    app.add_handler(conv_handler)
    
    # Add cancel command handler globally as well
    app.add_handler(CommandHandler("cancel", cancel))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
