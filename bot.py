import os
import requests
#import asyncio
from dotenv import load_dotenv

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =============================
# CARGAR VARIABLES .ENV
# =============================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

print("TOKEN OK:", TELEGRAM_TOKEN[:10])

# =============================
# FUNCION IA
# =============================

def preguntar_ia(mensaje):

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "arcee-ai/trinity-large-preview:free",
                "messages": [
                    {
                        "role": "system",
                        "content": """Eres el asistente inteligente oficial de H2OyVida,
una empresa especializada en soluciones de ahorro y eficiencia hídrica.

H2OyVida se enfoca en la conservación del agua potable, la reducción
del gasto económico y la concientización ambiental en hogares,
comercios e industrias.

La empresa ofrece dispositivos llamados Aqua Saver,
diseñados para optimizar el flujo y la presión del agua
sin afectar la experiencia del usuario.

Estos dispositivos permiten reducir el consumo de agua
entre un 45% y un 70% dependiendo de la instalación.

Características principales:
- No requieren obras ni modificaciones estructurales.
- Instalación rápida y sencilla.
- Materiales seguros y no tóxicos.
- Larga vida útil.
- Generan ahorro económico directo en la factura.

H2OyVida trabaja con:
hoteles, edificios, restaurantes, empresas e industrias
que buscan reducir costos operativos y mejorar su impacto ambiental.

Objetivos para el cliente:
- Reducir desperdicio de agua.
- Disminuir costos mensuales.
- Mejorar eficiencia operativa.
- Cumplir objetivos de sostenibilidad.

Debes actuar como asesor consultivo profesional.
Guía la conversación hacia una evaluación comercial.

Si el usuario muestra interés en ahorrar agua,
reducir gastos o mejorar eficiencia,
haz preguntas para entender su consumo
y orientar hacia una solución."""
                    },
                    {
                        "role": "user",
                        "content": mensaje
                    }
                ],
            },
            timeout=30
        )

        data = response.json()

        print("IA DEBUG:", data)

        if "choices" in data:
            return data["choices"][0]["message"]["content"]

        if "error" in data:
            return f"Error IA: {data['error']['message']}"

        return "No pude generar respuesta ahora."

    except Exception as e:
        print("IA ERROR:", e)
        return "La IA no está disponible temporalmente."

# =============================
# START
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [["Calcular ahorro"]]

    await update.message.reply_text(
        "💧 Asistente Inteligente de Ahorro de Agua",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        ),
    )


# =============================
# MENSAJES
# =============================

async def mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = update.message.text

    if texto == "Calcular ahorro":
        context.user_data["estado"] = "consumo"

        await update.message.reply_text(
            "¿Cuánto paga por agua al mes?"
        )
        return

    if context.user_data.get("estado") == "consumo":

        try:
            consumo = int(texto)
            ahorro = int(consumo * 0.3)

            await update.message.reply_text(
                f"✅ Ahorro estimado:\n"
                f"${ahorro}/mes\n"
                f"${ahorro*12}/año"
            )

            context.user_data["estado"] = None
            return

        except:
            await update.message.reply_text(
                "Ingrese solo números."
            )
            return

    respuesta = preguntar_ia(texto)
    await update.message.reply_text(respuesta)


# =============================
# APP
# =============================


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, mensajes))

print("BOT INICIADO ✅")

app.run_polling(close_loop=False)