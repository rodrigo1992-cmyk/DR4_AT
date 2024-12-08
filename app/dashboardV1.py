import streamlit as st
import yaml
from PIL import Image
import json

st.set_page_config(page_title="Portal de Governança da Câmara", page_icon=":bar_chart:")

tabs = st.tabs(["Overview", "Despesas", "Proposições"])

with tabs[0]:
    st.title("Portal de Governança da Câmara")
    st.write("Este aplicativo visa facilitar a governança da Câmara de Deputados, permitindo o acompanhamento dos políticos com mandatos vigentes, suas despesas e propostas.")

    st.title("Visão Geral da Câmara dos Deputados")
    try:
        with open('C:/Users/RodrigoPintoMesquita/Documents/GitHub/DR4_AT/data/config.yaml', 'r', encoding='utf-8') as file:
            yaml_data = yaml.safe_load(file)
            yaml_string = yaml.dump(yaml_data, allow_unicode=True)
            st.text_area("Configurações", yaml_string, height=500)
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
        with open('C:/Users/RodrigoPintoMesquita/Documents/GitHub/DR4_AT/data/insights_distribuicao_deputados.json', 'r', encoding='utf-8') as file:
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
    st.write("Aba Despesas")

with tabs[2]:
    st.write("Aba Proposições")

