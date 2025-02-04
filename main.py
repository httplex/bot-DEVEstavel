from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
import os
from appwrite.client import Client
from appwrite.services.databases import Databases
from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
from flask import Flask, request

# 🔹 Inicializa o Flask
app = Flask(__name__)

# 🔹 Token do bot e chat ID
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TOKEN)

# 🔹 Configuração do Appwrite
client = Client()
client.set_endpoint("https://cloud.appwrite.io/v1")  # Substituir pelo endpoint do seu Appwrite
client.set_project("679ec825003109b1dc49")  # ID do projeto
#Key que tive que criar no appwrite
client.set_key("standard_ff51eae676622efcc1041c84688e46a5284a0ab89bc75998cba61ab59d367f96e167b1b972dd3d74d6603bce78a81d0addcf8bfba94ef668bf684e4525ed9b9eb697755ce6289cd48c377132b7c6e8acda983824b3911540ff10af4cbd1c0ff52957c2a889046f63a17e10e1104ef82079dcec6d1c707115cb2e0b9bb843e916")
database = Databases(client)

# 🔹 IDs do banco e da coleção
database_id = "67a181ae00117541a360"  # ID do banco no Appwrite
collection_id = "67a25399002c05c91fcc"  # ID da coleção onde os dados serão salvos

# 🔹 Comando /start para iniciar o bot
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "✅ *Bot iniciado com sucesso!*\n\n"
        "📌 Use `/ranking` para ver o ranking.\n"
    )
    print("🔹 Bot iniciado!")

# 🔹 Função para gerar ranking e enviar como imagem
async def gerar_ranking(update: Update, context: CallbackContext):
    try:
        response = database.list_documents(database_id, collection_id)
        usuarios = sorted(
            [
                {"nome": doc["nome"], "dias": doc["dias"], "questoes": doc["questoes"], "percentual": doc["percentual"]}
                for doc in response["documents"]
            ],
            key=lambda x: (-x["dias"], -x["questoes"])
        )

        medalha_ouro = Image.open("imagem/medalha_ouro.png").resize((50, 50))
        medalha_prata = Image.open("imagem/medalha_prata.png").resize((50, 50))
        medalha_bronze = Image.open("imagem/medalha_bronze.png").resize((50, 50))
        medalhas = [medalha_ouro, medalha_prata, medalha_bronze]

        largura = 600
        altura = 100 + (len(usuarios) * 40)
        img = Image.new("RGB", (largura, altura), "white")
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("arial.ttf", 20)

        draw.text((50, 20), "🏆 RANKING DOS CANDIDATOS 🏆", fill="black", font=font)
        draw.text((50, 60), "Candidato", fill="black", font=font)
        draw.text((300, 60), "Dias", fill="black", font=font)
        draw.text((380, 60), "#Q", fill="black", font=font)
        draw.text((460, 60), "%", fill="black", font=font)

        y = 100
        for i, user in enumerate(usuarios):
            if i < 3:
                img.paste(medalhas[i], (10, y - 10))
            draw.text((50, y), user["nome"], fill="black", font=font)
            draw.text((300, y), str(user["dias"]), fill="black", font=font)
            draw.text((380, y), str(user["questoes"]), fill="black", font=font)
            draw.text((460, y), f"{user['percentual']}%", fill="black", font=font)
            y += 40

        image_stream = io.BytesIO()
        img.save(image_stream, format="PNG")
        image_stream.seek(0)

        await bot.send_photo(chat_id=update.effective_chat.id, photo=image_stream)

    except Exception as e:
        print(f"Erro ao gerar ranking: {str(e)}")

# 🔹 Função principal compatível com o Appwrite
def main(context=None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ranking", gerar_ranking))

    print("Bot rodando no Appwrite...")
    loop.run_until_complete(app.run_polling())