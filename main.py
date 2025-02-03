#TOKEN = "7493460267:AAFHXDyo1wAL3MYhIKUMiC_0Rj_h80c4kFI"
#CHAT_ID = "-1002425178067" -1002425178067 # Chat ID ou username para quem o bot enviará as mensagensfrom telegram import Bot
from flask import Flask, request
import os
import requests
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
import schedule
import asyncio
import time
from threading import Thread
from datetime import datetime
import pytz
import json
import re
from PIL import Image, ImageDraw, ImageFont

# 🔹 Inicializa o Flask
app = Flask(__name__)

# 🔹 Token do bot e chat ID
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TOKEN)

# 🔹 Definição dos arquivos de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(BASE_DIR, "dados_usuarios.json")

# 🔹 Função para carregar e salvar JSONs
def carregar_dados(arquivo):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_dados(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# 🔹 Inicializar os dados carregando do JSON
dados_usuarios = carregar_dados(ARQUIVO_DADOS)

# 🔹 Comando `/start`
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "✅ *Bot iniciado com sucesso!*\n\n"
        "📌 Use `/relatorio` para ver o ranking.\n"
    )
    print("🔹 Bot iniciado!")

# 🔹 Processar envios de usuários e associar números ao Telegram
async def receber_dados(update: Update, context: CallbackContext):
    try:
        mensagem = update.message.text
        user = update.message.from_user
        nome_usuario = f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name

        # Obtém a data atual no fuso horário de Brasília
        fuso_brasilia = pytz.timezone("America/Sao_Paulo")
        data_atual = datetime.now(fuso_brasilia).strftime("%Y-%m-%d")

        # Expressão regular para capturar mensagens com formato `@botname 23/63%`
        padrao = rf"@{context.bot.username} (\d+)/(\d+)%"
        match = re.search(padrao, mensagem)

        if match:
            acertos_dia = int(match.group(1))
            percentual_dia = float(match.group(2))

            if nome_usuario in dados_usuarios:
                ultima_data = dados_usuarios[nome_usuario].get("ultima_data", "")

                # Se for um novo dia, atualiza os dados corretamente
                if ultima_data != data_atual:
                    if "questoes_do_dia" in dados_usuarios[nome_usuario]:
                        dados_usuarios[nome_usuario]["questoes"] += dados_usuarios[nome_usuario]["questoes_do_dia"]

                    if "percentual_do_dia" in dados_usuarios[nome_usuario]:
                        total_questoes = dados_usuarios[nome_usuario]["questoes"]
                        if total_questoes > 0:
                            nova_porcentagem = (
                                (dados_usuarios[nome_usuario]["percentual"] * total_questoes) +
                                (dados_usuarios[nome_usuario]["percentual_do_dia"] * dados_usuarios[nome_usuario]["questoes_do_dia"])
                            ) / total_questoes
                            dados_usuarios[nome_usuario]["percentual"] = round(nova_porcentagem, 2)

                    dados_usuarios[nome_usuario]["questoes_do_dia"] = acertos_dia
                    dados_usuarios[nome_usuario]["percentual_do_dia"] = percentual_dia
                    dados_usuarios[nome_usuario]["dias"] += 1
                else:
                    dados_usuarios[nome_usuario]["questoes_do_dia"] = acertos_dia
                    dados_usuarios[nome_usuario]["percentual_do_dia"] = percentual_dia

                dados_usuarios[nome_usuario]["ultima_data"] = data_atual  
            else:
                dados_usuarios[nome_usuario] = {
                    "dias": 1,
                    "questoes": 0,
                    "questoes_do_dia": acertos_dia,
                    "percentual": percentual_dia,
                    "percentual_do_dia": percentual_dia,
                    "ultima_data": data_atual,
                }

            salvar_dados(ARQUIVO_DADOS, dados_usuarios)

            await update.message.reply_text(f"📊 {nome_usuario}, seus dados foram atualizados!")
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

# 🔹 Webhook para receber mensagens do Telegram
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    update = Update.de_json(data, bot)
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Adiciona os handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_dados))
    
    # Processa a atualização recebida
    application.process_update(update)
    
    return {"status": "ok"}

# 🔹 Função para resetar os dias consecutivos às 23h
def zerar_dias_consecutivos():
    fuso_brasilia = pytz.timezone("America/Sao_Paulo")
    data_atual = datetime.now(fuso_brasilia).strftime("%Y-%m-%d")

    for usuario, dados in dados_usuarios.items():
        if dados.get("ultima_data", "") != data_atual:
            dados_usuarios[usuario]["dias"] = 0

    salvar_dados(ARQUIVO_DADOS, dados_usuarios)

# 🔹 Agendar reset diário
def agendar_reset_dias():
    fuso_brasilia = pytz.timezone("America/Sao_Paulo")
    horario_reset = datetime.now(fuso_brasilia).replace(hour=23, minute=0, second=0, microsecond=0)
    horario_reset_utc = horario_reset.astimezone(pytz.utc).strftime("%H:%M")

    schedule.every().day.at(horario_reset_utc).do(zerar_dias_consecutivos)

# 🔹 Inicia o agendamento em paralelo
def run_schedule():
    agendar_reset_dias()
    while True:
        schedule.run_pending()
        time.sleep(1)

# 🔹 Inicia a thread do agendamento
Thread(target=run_schedule).start()

# 🔹 Executa o Flask no Appwrite
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
