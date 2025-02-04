import json
from appwrite.client import Client
from appwrite.services.databases import Databases

# Configuração do cliente Appwrite
client = Client()
client.set_endpoint("https://cloud.appwrite.io/v1")  # Substituir pelo endpoint do seu Appwrite
client.set_project("679ec825003109b1dc49")  # Substituir pelo ID do seu projeto
client.set_key("standard_ff51eae676622efcc1041c84688e46a5284a0ab89bc75998cba61ab59d367f96e167b1b972dd3d74d6603bce78a81d0addcf8bfba94ef668bf684e4525ed9b9eb697755ce6289cd48c377132b7c6e8acda983824b3911540ff10af4cbd1c0ff52957c2a889046f63a17e10e1104ef82079dcec6d1c707115cb2e0b9bb843e916")  # Substituir pela API Key

# Instância do banco de dados
database = Databases(client)

# IDs do banco e da coleção
database_id = "67a181ae00117541a360"  # Substituir pelo ID do banco
collection_id = "67a25399002c05c91fcc"  # Substituir pelo ID da coleção

# JSON dos usuários
json_data = ''' SEU_JSON_AQUI '''
usuarios = json.loads(json_data)

# Função para formatar telefone
def formatar_telefone(telefone):
    return telefone.replace("+", "") if telefone else telefone  # Remove '+' se existir

# Inserindo os dados no Appwrite
for nome, dados in usuarios.items():
    try:
        response = database.create_document(
            database_id=database_id,
            collection_id=collection_id,
            document_id="unique()",  # Gera um ID único automaticamente
            data={
                "nome": nome,
                "dias": dados["dias"],
                "questoes": dados["questoes"],
                "questoes_do_dia": dados["questoes_do_dia"],
                "percentual": dados["percentual"],
                "percentual_do_dia": dados["percentual_do_dia"],
                "telefone": formatar_telefone(dados["telefone"]),  # Remove o '+'
                "ultima_data": dados["ultima_data"],
            }
        )
        print(f"Usuário {nome} inserido com sucesso!")
    except Exception as e:
        print(f"Erro ao inserir usuário {nome}: {str(e)}")
