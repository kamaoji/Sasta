import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler

BOT_TOKEN = os.getenv("7917012747:AAEJ5qNz9mGjPnBS8GBX6KnNrRApNc2f3jw")
CHANNEL_USERNAME = os.getenv("@SastaLootMandi")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

ASK_NAME, ASK_DEAL, ASK_SCREENSHOT = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={CHANNEL_USERNAME}&user_id={user_id}"
    res = requests.get(url).json()

    if res["result"]["status"] not in ["member", "administrator", "creator"]:
        join_link = f"https://t.me/{CHANNEL_USERNAME[1:]}"
        await update.message.reply_text(f"❌ पहले हमारे चैनल को जॉइन करें:\n👉 {join_link}\n\nफिर /start टाइप करें")
        return ConversationHandler.END

    await update.message.reply_text("👇 नीचे दिए गए सवालों का जवाब दीजिए:\n\n1) अपना नाम बताइए:")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("2) आपने कौन-सी deal loot की? नाम या लिंक भेजिए:")
    return ASK_DEAL

async def ask_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["deal"] = update.message.text
    await update.message.reply_text("3) अब उस deal का Screenshot भेजिए 📸")
    return ASK_SCREENSHOT

async def ask_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = update.message.photo[-1].file_id
    name = context.user_data["name"]
    deal = context.user_data["deal"]

    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id,
        caption=f"New Loot Entry:\nName: {name}\nDeal: {deal}")
    await update.message.reply_text("✅ धन्यवाद! आपकी entry मिल गई।\n🏆 Winner Sunday रात 9 बजे घोषित होगा!")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⛔️ Process canceled.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_DEAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deal)],
            ASK_SCREENSHOT: [MessageHandler(filters.PHOTO, ask_screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
