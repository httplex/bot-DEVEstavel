#TOKEN = "7493460267:AAFHXDyo1wAL3MYhIKUMiC_0Rj_h80c4kFI"
#CHAT_ID = "-1002425178067" -1002425178067 # Chat ID ou username para quem o bot enviará as mensagensfrom telegram import Bot
import sys
sys.stdout.reconfigure(encoding='utf-8')
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
import schedule
import asyncio
import time
from threading import Thread
from datetime import datetime
import pytz
import json
import os
import pandas as pd
import re
from PIL import Image, ImageDraw, ImageFont

# Obtém o diretório onde o script está localizado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define o caminho correto do JSON
ARQUIVO_DADOS = os.path.join(BASE_DIR, "dados_usuarios.json")

# Função para carregar JSON
def carregar_dados(arquivo):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Função para salvar JSON
def salvar_dados(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# Inicializar os dados carregando dos JSONs
dados_usuarios = carregar_dados(ARQUIVO_DADOS)

# Token e Chat ID do bot
TOKEN = "7493460267:AAFHXDyo1wAL3MYhIKUMiC_0Rj_h80c4kFI"
CHAT_ID = "-1002425178067"

# Bot para envio de mensagens
bot = Bot(token=TOKEN)

# 🔹 Comando `/start`
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "✅ *Bot iniciado com sucesso!*\n\n"
        "📌 Use `/relatorio` para ver o ranking.\n"
    )
    print("🔹 Bot iniciado!")

# 🔹 Função para normalizar números brasileiros
def normalizar_numero(numero):
    if numero:
        # Remove caracteres especiais e mantém apenas números
        numero = re.sub(r"\D", "", numero)

        # Garante que o número tenha o formato correto com +55
        if len(numero) == 11 and numero.startswith("1"):  # Exemplo: 1198765432
            numero = f"+55{numero}"

        # Adiciona o "9" antes dos 8 últimos dígitos se for um número válido sem ele
        if len(numero) == 13 and not numero[4] == "9":  # Exemplo: +551187654321 → +5511987654321
            numero = numero[:4] + "9" + numero[4:]

    return numero

# 🔹 Processar envios de usuários e associar números ao Telegram
async def receber_dados(update: Update, context: CallbackContext):
    try:
        mensagem = update.message.text
        user = update.message.from_user

        # 🔹 Verifica se o bot foi mencionado na mensagem
        if context.bot.username not in mensagem:
            return  # Se não foi mencionado, ignora a mensagem

        # Obtém o nome real do usuário (primeiro nome + sobrenome se disponível)
        nome_usuario = f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name

        # Obtém e normaliza o número de telefone (se disponível no Telegram)
        telefone = None
        if hasattr(user, "phone_number") and user.phone_number:
            telefone = normalizar_numero(user.phone_number)

        # Obtém a data atual no fuso horário de Brasília
        fuso_brasilia = pytz.timezone("America/Sao_Paulo")
        data_atual = datetime.now(fuso_brasilia).strftime("%Y-%m-%d")

        # 🔹 Garantir que todos os usuários tenham `ultima_data` preenchida corretamente
        for usuario, dados in dados_usuarios.items():
            if "ultima_data" not in dados or not dados["ultima_data"]:
                dados_usuarios[usuario]["ultima_data"] = data_atual  # Define a data atual se estiver vazia

        # 🔹 Remover números de telefone inválidos (exemplo: "+5500000000...")
        for usuario, dados in dados_usuarios.items():
            telefone_salvo = dados.get("telefone", "")
            if telefone_salvo and "000000000" in telefone_salvo:  # Se o telefone for inválido, remove
                dados_usuarios[usuario]["telefone"] = None

        # Verifica se o telefone já existe na base e associa ao nome
        usuario_existente = None
        for usuario, dados in dados_usuarios.items():
            telefone_salvo = normalizar_numero(dados.get("telefone"))
            if telefone_salvo == telefone:
                usuario_existente = usuario
                break

        if usuario_existente:
            nome_usuario = usuario_existente  # Mantém o nome original do WhatsApp

        # Separa os dados enviados (formato correto: `@SeLigaDEV 23/63%`)
        padrao = rf"@{context.bot.username} (\d+)/(\d+)%"
        match = re.search(padrao, mensagem)

        if match:
            acertos_dia = int(match.group(1))  # Número de questões acertadas no envio
            percentual_dia = float(match.group(2))  # Porcentagem enviada pelo usuário

            if nome_usuario in dados_usuarios:
                # Obtém a última data registrada
                ultima_data = dados_usuarios[nome_usuario].get("ultima_data", data_atual)

                # Se for um novo dia, incrementa a contagem de dias consecutivos
                if ultima_data != data_atual:
                    dados_usuarios[nome_usuario]["dias"] += 1

                # Recupera os dados antigos
                questoes_anteriores = dados_usuarios[nome_usuario]["questoes"]
                porcentagem_anterior = dados_usuarios[nome_usuario]["percentual"]

                # Atualiza corretamente o total de questões
                dados_usuarios[nome_usuario]["questoes"] += acertos_dia  # Somente a soma dos acertos

                # Recalcula a porcentagem correta (MÉDIA PONDERADA)
                total_questoes = dados_usuarios[nome_usuario]["questoes"]

                if total_questoes > 0:
                    nova_porcentagem = ((porcentagem_anterior * questoes_anteriores) + (percentual_dia * acertos_dia)) / total_questoes
                else:
                    nova_porcentagem = percentual_dia  # Caso inicial

                # Garante que a porcentagem esteja entre 0% e 100%
                nova_porcentagem = min(max(nova_porcentagem, 0), 100)
                nova_porcentagem = round(nova_porcentagem, 2)

                dados_usuarios[nome_usuario]["percentual"] = nova_porcentagem
                dados_usuarios[nome_usuario]["ultima_data"] = data_atual  # Atualiza a última data
            else:
                # Se o usuário não estava no JSON, cria um novo cadastro
                nova_porcentagem = round(percentual_dia, 2)

                dados_usuarios[nome_usuario] = {
                    "dias": 1,
                    "questoes": acertos_dia,  # Total de questões = total de acertos enviados
                    "percentual": nova_porcentagem,  # Usa a porcentagem enviada pelo usuário
                    "ultima_data": data_atual,  # Registra a primeira data
                    "telefone": telefone  # Salva o telefone do usuário
                }

            salvar_dados(ARQUIVO_DADOS, dados_usuarios)

            # Resposta confirmando a atualização
            await update.message.reply_text(
                f"📊 {nome_usuario}, seus dados foram atualizados:\n"
                f"- **Dias consecutivos**: {dados_usuarios[nome_usuario]['dias']}\n"
                f"- **Total de Questões**: {dados_usuarios[nome_usuario]['questoes']}\n"
                f"- **Média de Acertos**: {nova_porcentagem:.2f}%"
            )
        else:
            return  # Não responde nada se o formato estiver errado

    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")


# 🔹 Função para zerar dias consecutivos se o usuário não enviar mensagem até as 23h (Horário de Brasília)
def zerar_dias_consecutivos():
    fuso_brasilia = pytz.timezone("America/Sao_Paulo")
    data_atual = datetime.now(fuso_brasilia).strftime("%Y-%m-%d")

    for usuario, dados in dados_usuarios.items():
        ultima_data = dados.get("ultima_data", "")

        # Se a última data registrada for diferente da data atual, significa que o usuário não enviou nada hoje
        if ultima_data != data_atual:
            dados_usuarios[usuario]["dias"] = 0  # Zera os dias consecutivos

    salvar_dados(ARQUIVO_DADOS, dados_usuarios)  # Salva os dados atualizados no JSON

# 🔹 Agendar verificação às 23h (Horário de Brasília) para resetar dias consecutivos
def agendar_reset_dias():
    fuso_brasilia = pytz.timezone("America/Sao_Paulo")
    horario_reset = datetime.now(fuso_brasilia).replace(hour=23, minute=0, second=0, microsecond=0)

    # Converte para o horário UTC, pois o `schedule` trabalha no horário do sistema
    horario_reset_utc = horario_reset.astimezone(pytz.utc).strftime("%H:%M")

    schedule.every().day.at(horario_reset_utc).do(zerar_dias_consecutivos)

# 🔹 Inicia a verificação automática de reset diário às 23h de Brasília
def run_schedule():
    agendar_reset_dias()  # Agenda o reset dos dias consecutivos
    while True:
        schedule.run_pending()
        time.sleep(1)


# 🔹 Função para gerar a imagem do ranking
from PIL import Image, ImageDraw, ImageFont

# 🔹 Caminhos das imagens das medalhas (use imagens reais de medalhas)
MEDALHAS = {
    1: "medalha_ouro.png",   # 🥇
    2: "medalha_prata.png",  # 🥈
    3: "medalha_bronze.png"  # 🥉
}

# 🔹 Função para gerar a imagem do ranking com as medalhas ao lado dos nomes
def gerar_imagem_ranking():
    try:
        # Ordena os usuários pelo número de dias (do maior para o menor)
        ranking = sorted(dados_usuarios.items(), key=lambda x: x[1]["dias"], reverse=True)

        if not ranking:  # Se não houver usuários, evita erro ao tentar acessar os três primeiros
            return None, []

        # Configuração da imagem
        largura, altura = 600, 50 + len(ranking) * 40
        img = Image.new("RGB", (largura, altura), color="white")
        draw = ImageDraw.Draw(img)

        # Carregar fonte
        try:
            fonte = ImageFont.truetype("arial.ttf", size=20)
        except IOError:
            fonte = ImageFont.load_default()

        # Cabeçalho
        y_offset = 10
        colunas = ["Candidatos", "Dias", "#Q", "%"]
        x_positions = [50, 250, 350, 450]  # Ajustado para dar espaço às medalhas
        for i, coluna in enumerate(colunas):
            draw.text((x_positions[i], y_offset), coluna, fill="black", font=fonte)

        # Adicionando os dados do ranking ordenados por dias
        y_offset += 30
        for i, (usuario, dados) in enumerate(ranking, start=1):
            percentual_formatado = f"{dados['percentual']:0.2f}%"

            valores = [usuario, str(dados["dias"]), str(dados["questoes"]), percentual_formatado]

            # Desenhar medalha ao lado dos três primeiros colocados
            if i <= 3:
                medalha_path = MEDALHAS.get(i)
                if medalha_path and os.path.exists(medalha_path):
                    medalha = Image.open(medalha_path).resize((25, 25))  # Redimensiona a medalha
                    img.paste(medalha, (10, y_offset))  # Coloca a medalha na posição correta

            # Escrever os dados na imagem
            for j, valor in enumerate(valores):
                draw.text((x_positions[j], y_offset), valor, fill="black", font=fonte)
            y_offset += 30

        # Salva a imagem
        image_path = "ranking.png"
        img.save(image_path)

        # Retorna a imagem e os três primeiros colocados (garantindo que existam)
        top3 = ranking[:3] if len(ranking) >= 3 else ranking
        return image_path, top3  

    except Exception as e:
        print(f"Erro ao gerar imagem do ranking: {e}")
        return None, []


# 🔹 Função para gerar e enviar ranking manualmente (/relatorio) ou automaticamente às 23h
async def gerar_e_enviar_ranking(update: Update = None, context: CallbackContext = None):
    resultado = gerar_imagem_ranking()

    if not resultado or resultado[0] is None:
        if update:
            await update.message.reply_text("Nenhum dado foi enviado ainda. 😞")
        return

    image_path, top3 = resultado

    with open(image_path, "rb") as image_file:
        await bot.send_photo(chat_id=CHAT_ID, photo=image_file, caption="📊 *Ranking de Desempenho*")

    # Mensagem de parabéns para os três primeiros colocados
    if top3:
        mensagem_podio = "\n".join([
            f"🥇 *{top3[0][0]}* - Ouro!" if len(top3) > 0 else "",
            f"🥈 *{top3[1][0]}* - Prata!" if len(top3) > 1 else "",
            f"🥉 *{top3[2][0]}* - Bronze!" if len(top3) > 2 else "",
        ]).strip()

        if mensagem_podio:
            await bot.send_message(chat_id=CHAT_ID, text=f"🎉 Parabéns aos três primeiros colocados! 🚀\n\n{mensagem_podio}", parse_mode="Markdown")



# 🔹 Agendar envio do relatório automaticamente às 23h (Horário de Brasília)
def agendar_relatorio_diario():
    fuso_brasilia = pytz.timezone("America/Sao_Paulo")
    horario_relatorio = datetime.now(fuso_brasilia).replace(hour=23, minute=0, second=0, microsecond=0)

    # Converte para UTC para o `schedule`
    horario_relatorio_utc = horario_relatorio.astimezone(pytz.utc).strftime("%H:%M")

    schedule.every().day.at(horario_relatorio_utc).do(lambda: asyncio.run(gerar_e_enviar_ranking()))

# 🔹 Função principal do bot
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("relatorio", gerar_e_enviar_ranking))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_dados))

    Thread(target=run_schedule).start()
    app.run_polling()

# 🔹 Inicia a verificação de horários
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
