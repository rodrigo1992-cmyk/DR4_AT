import requests
import pandas as pd
import PyPDF2
from io import BytesIO

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
        


        




            
