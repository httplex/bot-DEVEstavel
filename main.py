import os
import json
import time
import schedule
import pytz
import asyncio
from threading import Thread
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
from appwrite.client import Client
from appwrite.services.databases import Databases

# 🔹 Token do bot e chat ID
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TOKEN)

# 🔹 Configuração do Appwrite
client = Client()
client.set_endpoint("https://cloud.appwrite.io/v1")  # Substituir pelo endpoint do seu Appwrite
client.set_project("679ec825003109b1dc49")  # ID do projeto
client.set_key("standard_ff51eae676622efcc1041c84688e46a5284a0ab89bc75998cba61ab59d367f96e167b1b972dd3d74d6603bce78a81d0addcf8bfba94ef668bf684e4525ed9b9eb697755ce6289cd48c377132b7c6e8acda983824b3911540ff10af4cbd1c0ff52957c2a889046f63a17e10e1104ef82079dcec6d1c707115cb2e0b9bb843e916")
database = Databases(client)

# 🔹 IDs do banco e da coleção
database_id = "67a181ae00117541a360"  # ID do banco no Appwrite
collection_id = "67a25399002c05c91fcc"  # ID da coleção onde os dados serão salvos

# 🔹 Comando /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("✅ Bot iniciado!\n\n📌 Use `/ranking` para ver o ranking.")

# 🔹 Processa mensagens recebidas
async def receber_mensagem(update: Update, context: CallbackContext):
    try:
        mensagem = update.message.text
        user = update.message.from_user
        nome_usuario = f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name
        telegram_id = str(user.id)

        if mensagem.startswith("/"):
            return  # Ignorar comandos não implementados

        # Expressão regular para capturar mensagens com formato `23/63%`
        import re
        padrao = r"(\d+)/(\d+)%"
        match = re.search(padrao, mensagem)

        if match:
            acertos_dia = int(match.group(1))
            percentual_dia = float(match.group(2))

            salvar_dados_no_appwrite(nome_usuario, telegram_id, acertos_dia, percentual_dia)

            await update.message.reply_text(f"📊 {nome_usuario}, seus dados foram atualizados no banco!")
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

# 🔹 Função para salvar ou atualizar os dados no Appwrite
def salvar_dados_no_appwrite(nome_usuario, telegram_id, acertos_dia, percentual_dia):
    try:
        fuso_brasilia = pytz.timezone("America/Sao_Paulo")
        data_atual = datetime.now(fuso_brasilia).strftime("%Y-%m-%d")

        response = database.list_documents(
            database_id=database_id,
            collection_id=collection_id,
            queries=[f"equal('telefone', '{telegram_id}')"]
        )

        if response["documents"]:
            document_id = response["documents"][0]["$id"]
            ultima_data = response["documents"][0].get("ultima_data", "")

            if ultima_data != data_atual:
                total_questoes = response["documents"][0]["questoes"]
                nova_porcentagem = (
                    (response["documents"][0]["percentual"] * total_questoes) +
                    (response["documents"][0]["percentual_do_dia"] * response["documents"][0]["questoes_do_dia"])
                ) / total_questoes if total_questoes > 0 else percentual_dia

                database.update_document(
                    database_id=database_id,
                    collection_id=collection_id,
                    document_id=document_id,
                    data={
                        "questoes": total_questoes + response["documents"][0]["questoes_do_dia"],
                        "percentual": round(nova_porcentagem, 2),
                        "questoes_do_dia": acertos_dia,
                        "percentual_do_dia": percentual_dia,
                        "dias": response["documents"][0]["dias"] + 1,
                        "ultima_data": data_atual,
                    }
                )
            else:
                database.update_document(
                    database_id=database_id,
                    collection_id=collection_id,
                    document_id=document_id,
                    data={
                        "questoes_do_dia": acertos_dia,
                        "percentual_do_dia": percentual_dia,
                    }
                )
        else:
            database.create_document(
                database_id=database_id,
                collection_id=collection_id,
                document_id="unique()",
                data={
                    "nome": nome_usuario,
                    "telefone": telegram_id,
                    "dias": 1,
                    "questoes": 0,
                    "questoes_do_dia": acertos_dia,
                    "percentual": percentual_dia,
                    "percentual_do_dia": percentual_dia,
                    "ultima_data": data_atual,
                }
            )

        print(f"📊 Dados de {nome_usuario} foram atualizados no Appwrite!")

    except Exception as e:
        print(f"Erro ao salvar dados no Appwrite: {str(e)}")

# 🔹 Comando /relatorio (testa a exibição do ranking antes de enviar)
async def relatorio(update: Update, context: CallbackContext):
    await gerar_ranking(update, context)

# 🔹 Comando para gerar ranking e criar a imagem
async def gerar_ranking(update: Update, context: CallbackContext):
    try:
        response = database.list_documents(database_id, collection_id)
        usuarios = [
            {
                "nome": doc["nome"],
                "dias": doc["dias"],
                "questoes": doc["questoes"],
                "percentual": doc["percentual"]
            }
            for doc in response["documents"]
        ]

        usuarios = sorted(usuarios, key=lambda x: (-x["dias"], -x["questoes"]))

        medalhas = ["🥇", "🥈", "🥉"]

        mensagem = "🏆 *RANKING FINAL DO DIA* 🏆\n\n"
        for i, user in enumerate(usuarios[:10]):
            medalha = medalhas[i] if i < 3 else ""
            mensagem += f"{medalha} {user['nome']} - {user['dias']} dias - {user['questoes']} questões - {user['percentual']}%\n"

        await bot.send_message(chat_id=CHAT_ID, text=mensagem, parse_mode="Markdown")

    except Exception as e:
        print(f"Erro ao gerar ranking: {str(e)}")

# 🔹 Função para resetar os dias e enviar ranking às 23h
def reset_diario():
    fuso_brasilia = pytz.timezone("America/Sao_Paulo")
    data_atual = datetime.now(fuso_brasilia).strftime("%Y-%m-%d")

    response = database.list_documents(database_id, collection_id)
    for doc in response["documents"]:
        if doc.get("ultima_data", "") != data_atual:
            database.update_document(
                database_id=database_id,
                collection_id=collection_id,
                document_id=doc["$id"],
                data={"dias": 0}
            )

    # Envia o ranking final antes do reset
    app = ApplicationBuilder().token(TOKEN).build()
    app.run_coroutine(gerar_ranking(None, None))

# 🔹 Agendar reset diário
def agendar_reset():
    schedule.every().day.at("23:00").do(reset_diario)

# 🔹 Inicia o agendamento em paralelo
def run_schedule():
    agendar_reset()
    while True:
        schedule.run_pending()
        time.sleep(1)

Thread(target=run_schedule).start()

# 🔹 Inicializa o bot
async def setup_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ranking", gerar_ranking))
    app.add_handler(CommandHandler("relatorio", relatorio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_mensagem))

    print("🚀 Bot rodando no Appwrite...")
    await app.run_polling()

# 🔹 Função Main para o Appwrite
async def main(context):
    asyncio.create_task(setup_bot())  # Executa sem bloquear o Appwrite
    return context.res.send("Bot rodando!")