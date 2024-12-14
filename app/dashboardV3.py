import streamlit as st
import yaml
from PIL import Image
import json
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
import google.generativeai as genai
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np

def search_and_self_ask(user_input):
    with open('data/input_embedding.json', 'r', encoding='utf-8') as file:
        texto = json.load(file)
        
    model_name = 'neuralmind/bert-base-portuguese-cased'
    llm_model_dir = 'data/bertimbau_'

    embedding_model = SentenceTransformer(model_name, cache_folder=llm_model_dir, device='cpu')

    embeddings = embedding_model.encode(texto)
    embeddings = np.array(embeddings).astype("float32")
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d) 
    index.add(embeddings)

    query_embedding = embedding_model.encode([user_input]).astype("float32")
    k = 15

    _, indices = index.search(query_embedding, k)

    list_found = []
    for i in range(k):
        list_found.append(texto[indices[0][i]])

    prompt_inicial = f"""
    Divida a seguinte questão principal em até 3 perguntas menores, caso necessário, que sejam etapas para a resposta da questão principal:
    '{user_input}'

    Responda no formato abaixo:
    1° Pergunta: 'xxx'
    1° Resposta: 'yyy'
    2° Pergunta: 'xxx'
    2° Resposta: 'yyy'

    Instruções:
    -Primeiro crie as perguntas sem analisar os dados, somente os analise após a criação das perguntas.
    -Não adicione comentários extras.
    -As respostas devem ser discursivas porém objetivas.
    -Sempre que citar percentuais, informe também o valor absoluto.
    
    Analise os dados abaixo para responder às perguntas:
    ## DADOS
    {list_found}
    """ 

    load_dotenv()
    genai.configure(api_key=os.getenv('GEMINI_KEY'))
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt_inicial)

    perguntas = response.text

    ## Segundo Prompt
    prompt = f"""
    Responda a questão principal "{user_input}", considerando as respostas já fornecidas às perguntas abaixo.
    Repita as perguntas e respostas anteriores e adicione a resposta à questão principal com base nelas.

    ## RESPOSTAS PRÉVIAS
    {perguntas}
    """

    load_dotenv()
    genai.configure(api_key=os.getenv('GEMINI_KEY'))
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    return response.text


st.set_page_config(page_title="Portal de Governança da Câmara", page_icon=":bar_chart:")

tabs = st.tabs(["Overview", "Despesas", "Proposições"])

with tabs[0]:
    st.title("Portal de Governança da Câmara")
    st.write("Este aplicativo visa facilitar a governança da Câmara de Deputados, permitindo o acompanhamento dos políticos com mandatos vigentes, suas despesas e propostas.")

    st.title("Visão Geral da Câmara dos Deputados")
    try:
        with open('data/config.yaml', 'r', encoding='utf-8') as file:
            yaml_data = yaml.safe_load(file)
            yaml_string = yaml.dump(yaml_data, allow_unicode=True)
            st.text_area("Configurações", yaml_string, height=900)
    except FileNotFoundError:
        st.error("Arquivo config.yaml não encontrado.")
    except yaml.YAMLError as e:
        st.error(f"Erro ao carregar o arquivo YAML: {e}")

    st.title("Distribuição dos Deputados por Partido")
    try:
        image = Image.open('C:/Users/RodrigoPintoMesquita/Documents/GitHub/DR4_AT/docs/distribuicao_deputados.png')
        st.image(image)
    except FileNotFoundError:
        st.error("Arquivo distribuicao_deputados.png não encontrado.")
    except Exception as e:
        st.error(f"Erro ao carregar a imagem: {e}")


    st.title("Análise da Distribuição de Deputados por Partido")
    try:
        with open('data/insights_distribuicao_deputados.json', 'r', encoding='utf-8') as file:
            json_data = json.load(file)
            markdown_text = json_data['text']
            st.markdown(markdown_text)
    except FileNotFoundError:
        st.error("Arquivo insights_distribuicao_deputados.json não encontrado.")
    except json.JSONDecodeError as e:
        st.error(f"Erro ao carregar o arquivo JSON: {e}")
    except KeyError:
        st.error("O arquivo JSON não contém o campo 'text'.")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")

with tabs[1]:
    st.title('Insights sobre Despesas dos Deputados')
    try:
        with open('data/insights_despesas_deputados.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                analysis_title = item['analysis_title'].replace('"', '').replace('\\', '').replace('$', '')
                insight = item['insight'].replace('"', '').replace('\\', '').replace('$', '')
                highest_spending_categories = item.get('highest_spending_categories', '').replace('"', '').replace('\\', '').replace('$', '')
                st.write(f"**Análise:** {analysis_title}")
                st.write(f"**Insight:** {insight}")
                if highest_spending_categories:
                    st.write(f"**Maiores categorias de gastos:** {highest_spending_categories}")
                st.markdown("---")

    except FileNotFoundError:
        st.error("Arquivo insights_despesas_deputados.json não encontrado.")
    except json.JSONDecodeError as e:
        st.error(f"Erro ao carregar o arquivo JSON: {e}")
    except KeyError as e:
        st.error(f"Chave não encontrada no JSON: {e}")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")

    try:
        df_despesas = pd.read_parquet('data/serie_despesas_diárias_deputados.parquet')
        
        #Docstrings
        df_despesas.__doc__ = """DataFrame contendo as despesas diárias dos deputados.

        Columns:
            date (datetime64[ns]): Data da despesa.
            name (object): Nome do deputado.
            net_value (float64): Valor líquido da despesa.
            cnpjcpf (object): CNPJ ou CPF do fornecedor.
            supplier (object): Nome do fornecedor.
            document (object): Número do documento.
            description (object): Descrição da despesa.
        """
        
        deputados = df_despesas['name'].unique()
        selected_deputados = st.selectbox('Consultar histórico de despesas por deputado', deputados, key = 1)
        
        df_filtrado = df_despesas[df_despesas['name'] == selected_deputados]

        fig = px.bar(df_filtrado, x='date', y='net_value', title='Despesas por Tipo de Despesa', 
                     labels={'date':'Data da Despesa', 'net_value':'Valor Total das Despesas'})
        st.plotly_chart(fig)

    except FileNotFoundError:
        st.error("Arquivo serie_despesas_diárias_deputados.parquet não encontrado.")
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo parquet: {e}")


with tabs[2]:
    st.title('Assistente Virtual')
    messages = st.container(height=700)
    
    if "welcome" not in st.session_state:
        st.session_state.welcome = True
            
    if input := st.chat_input("Faça sua pergunta"):
        messages.chat_message("user").write(input)

        resp_llm = search_and_self_ask(input)
        messages.chat_message("assistant").write(resp_llm)

        