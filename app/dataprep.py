import requests
import pandas as pd
import PyPDF2
from io import BytesIO
import os
import google.generativeai as genai
from dotenv import load_dotenv
import time
import json

def get_deputados():
    '''
    Retorna um DataFrame com a relação de deputados com mandato ativo em 2024.
   '''

    url_base = "https://dadosabertos.camara.leg.br/api/v2"
    url = f"{url_base}/deputados"
    response = requests.get(url)
    dados = response.json()['dados']

    df = pd.DataFrame(dados)
    df.to_parquet(r'C:\Users\RodrigoPintoMesquita\Documents\GitHub\DR4_AT\data\deputados.parquet')

    return df


########################################################################################


def get_despesas():
    '''
    Retorna um DataFrame com as despesas dos deputados em agosto de 2024.
    Utiliza o ID de cada deputado para solicitar as despesas associadas.
    '''

    url_base = "https://dadosabertos.camara.leg.br/api/v2"
    df = pd.DataFrame()

    df_deps = pd.read_parquet(r'C:\Users\RodrigoPintoMesquita\Documents\GitHub\DR4_AT\data\deputados.parquet')
    path_despesas = r'C:\Users\RodrigoPintoMesquita\Documents\GitHub\DR4_AT\data\serie_despesas_diárias_deputados.parquet'

    params = {
        'ano': 2024,
        'mes': 8,
    }

    for i, row in df_deps.iterrows():
        id = row['id']
        url = f"{url_base}/deputados/{id}/despesas"
        response = requests.get(url, params)
        dados = response.json()['dados']

        if dados:
            df_iter = pd.DataFrame(dados)
            df_iter['nome'] = row['nome']
            df_iter['data'] = df_iter['dataDocumento'].str[:10]
            df = pd.concat([df, pd.DataFrame(df_iter)])

    df = df.groupby(['nome','data', 'tipoDespesa'])['valorLiquido'].sum().reset_index()
    df.columns = ['name','date', 'expense_type', 'net_value']

    df.to_parquet(path_despesas)

    return df


########################################################################################


def get_proposicoes():
    '''
    Retorna um DataFrame com as proposições tramitando em agosto de 2024, relacionadas aos temas 40, 46 e 62.
    '''

    url_base = "https://dadosabertos.camara.leg.br/api/v2"
    url = f"{url_base}/proposicoes"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    df = pd.DataFrame()

    codTema = [40,46,62]

    #iterar para cada código de tema
    for cod in codTema:

        params = {
            'codTema': cod,
            'dataInicio': '2024-08-01',
            'dataFim': '2024-08-30',
        }
    
        response = requests.get(url, params=params, headers=headers)
        dados = response.json()['dados']


        #iterar para cada proposição na listagem recebida
        for prop in dados:
            url_prop = prop['uri']
            
            response = requests.get(url_prop, headers=headers)
            url_teor = response.json()['dados']['urlInteiroTeor']

            #obter o pdf com o conteúdo da proposição
            response = requests.get(url_teor, headers=headers)

            #obter o conteúdo textual do pdf
            try:
                with BytesIO(response.content) as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    texto = ''
                    for page in reader.pages:
                        texto += page.extract_text() + '\n' 

                #checar se veio algum caracter no texto ou apenas espaços e quebras de linha (ocorre quando o pdf é um docu escaneado/imagem plana)
                if texto.strip():
                    df_iter = pd.DataFrame(
                        {
                            'codTema': cod,
                            'idProp' : prop['id'],
                            'texto': texto
                        },index=[0]
                    )
                #concatenar o df da iteração ao df final
                df = pd.concat([df, df_iter])
                
            except: pass
        
    df.to_parquet(r'C:\Users\RodrigoPintoMesquita\Documents\GitHub\DR4_AT\data\proposicoes_deputados.parquet')

    return df
        

def criar_chunks(text, window, overlap):
    '''
    Recebe uma lista de frases e retorna uma lista de chunks.
    '''
    
    chunks = []
    for i in range(0, len(text), window - overlap):
        chunk = text[i:i + window] 
        chunks.append(" ".join(chunk))
        if i + window >= len(text):
            break
    return chunks


def criar_chunks_por_proposicao(df):
    '''
    Recebe um DataFrame com proposições e retorna uma lista de dicionários, onde cada dicionário contém o ID da proposição e uma lista de chunks de texto.
    '''

    df = df.groupby('codTema').head(10)

    list_chunksPorProposicao = []
    #iterar em cada proposição
    for i, row in df.iterrows():
        texto = row['texto'].replace('\n', ' ')
        #retirar espaços duplos
        texto = ' '.join(row['texto'].split())
        list_frases = texto.split('.')
        #remover posições vazias da lista ou que sejam apenas um espaço em branco
        list_frases = [frase for frase in list_frases if frase != '' and frase != ' ']

        #Devido a estrutura do documento, ficaram muitas linhas com apenas um número ou palavra solta. Neste caso, irei juntar com a linha anterior.
        list_frasesNew = []

        for i in range(0,len(list_frases)-1):
            if i == 0 or len(list_frases[i].split()) > 3:
                list_frasesNew.append(list_frases[i])
            # Juntar com o item anterior se tiver até 3 palavras.
            else:
                list_frasesNew[-1] += ' ' + list_frases[i]

            chunks = criar_chunks(list_frasesNew, 10, 3)
        
        new_chunk = {'idProp': row['idProp'], 'chunks': chunks}
        list_chunksPorProposicao.append(new_chunk)
        
        return list_chunksPorProposicao


def sumarizar_chunks(list_chunksPorProposicao):
    '''
    Recebe uma lista de dicionários com os chunks de texto de cada proposição e retorna um dicionário com os resumos de cada chunk.
    '''

    dict_summaries = {}

    prompt = f"""
    Você é um reporter político.
    Você receberá um trecho de uma proposta legislativa.
    Seu objetivo é resumir o texto em uma única sentença.

    Trecho da proposta:

    """

    genai.configure(api_key=os.getenv('GEMINI_KEY'))
    model = genai.GenerativeModel("gemini-1.5-flash")
    model.temperature = 0.3


    for proposta in list_chunksPorProposicao:
        chunks = proposta['chunks']
        idProp = proposta['idProp']

        if idProp not in dict_summaries:
            dict_summaries[idProp] = []

        for chunk in chunks:
            response = model.generate_content(prompt + chunk)
            dict_summaries[idProp].append(response.text)

            #Há cota de 15 chamadas por minuto, então tive de adicionar um bom tempo entre chamadas para não exceder.
            time.sleep(4.5)

    return dict_summaries

def sumarizacao_final(dict_summaries):
    '''
    Recebe um dicionário com os resumos dos chunks, faz o resumo final de cada proposicao e guarda o resultado em um arquivo JSON.
    '''
    
    df_summaries = pd.DataFrame(columns=['idProp', 'summary'])

    prompt = f"""
    Você é um reporter político.
    Você receberá resumos de trechos de uma proposta legislativas.
    Seu objetivo é condensar de em um único texto, as informações mais relevantes da proposta.

    Resumos dos trechos:

    """

    genai.configure(api_key=os.getenv('GEMINI_KEY'))
    model = genai.GenerativeModel("gemini-1.5-flash")
    model.temperature = 0.3


    for id in dict_summaries:
        chunks = dict_summaries[id]

        response = model.generate_content(prompt + ' '.join(chunks))
        df_iter = pd.DataFrame({'idProp': id, 'summary': response.text}, index=[0])
        df_summaries = pd.concat([df_summaries, pd.DataFrame(df_iter)])
        
        #Há cota de 15 chamadas por minuto, então tive de adicionar um bom tempo entre chamadas para não exceder.
        time.sleep(4.5)

    df_summaries.to_json(r'C:\Users\RodrigoPintoMesquita\Documents\GitHub\DR4_AT\data\sumarizacao_proposicoes.json', orient='records', indent=4, force_ascii=False)


def unificar_datasets():
    '''
    Unifica os datasets de deputados, despesas e proposições em um único arquivo JSON.
    '''

    #Cada Json está em um formato diferente, então está sendo necessário fazer a conversão manualmente deixando em um mesmo formato de lista.

    #Importando arquivo de distribuição de deputados e transformando em lista
    with open(r'C:\Users\RodrigoPintoMesquita\Documents\GitHub\DR4_AT\data\insights_distribuicao_deputados.json', 'r', encoding='utf-8') as file:
        texto = json.load(file)
        texto = texto['text'].replace('*', '')

    lista_temp = [paragrafo.strip() for paragrafo in texto.split('\n\n') if paragrafo.strip()]

    listas = []
    for item in lista_temp:
        listas.append(item)

    #Importando arquivo de distribuição de despesas e transformando em lista
    with open(r'C:\Users\RodrigoPintoMesquita\Documents\GitHub\DR4_AT\data\insights_despesas_deputados.json', 'r', encoding='utf-8') as file:
        texto = json.load(file)
    lista_temp = []
    for item in texto:
        lista_temp.append(list(item.values()))

    lista_temp = [': '.join(sublista) for sublista in lista_temp]
    for item in lista_temp:
        listas.append(item)

    #Importando arquivo de proposições e transformando em lista
    with open(r'C:\Users\RodrigoPintoMesquita\Documents\GitHub\DR4_AT\data\sumarizacao_proposicoes.json', 'r', encoding='utf-8') as file:
        texto = json.load(file)

    lista_temp = []
    for item in texto:
        lista_temp.append(list(item.values()))

    lista_temp = [': '.join(map(str, sublista)) for sublista in lista_temp]
    for item in lista_temp:
        listas.append(item)

    #Exportar para arquivo json
    with open(r'C:\Users\RodrigoPintoMesquita\Documents\GitHub\DR4_AT\data\input_embedding.json', 'w', encoding='utf-8') as file:
        json.dump(listas, file, ensure_ascii=False, indent=4)