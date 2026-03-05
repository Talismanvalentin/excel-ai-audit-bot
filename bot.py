import os
import requests
from dotenv import load_dotenv
from excel_analyzer import analyze_excel
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def explain_report(report):

    prompt = f"""
You are a data analyst.

Explain the following spreadsheet issues in simple terms and suggest fixes.

Issues:
{report}
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    data = response.json()

    return data["choices"][0]["message"]["content"]



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📊 AI Excel Error Detector\n\n"
        "Send me an Excel file (.xlsx) and I will analyze it."
    )


async def handle_document(update, context):

    file = await update.message.document.get_file()
    path = "downloads/" + update.message.document.file_name
    await file.download_to_drive(path)
    result = analyze_excel(path)
    ai_report = explain_report(result)
    await update.message.reply_text(ai_report)


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

print("BOT INICIADO ✅")

app.run_polling()