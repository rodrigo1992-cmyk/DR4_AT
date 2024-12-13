import streamlit as st
import yaml
from PIL import Image
import json
import pandas as pd
import plotly.express as px

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
    st.title('Insights sobre Despesas dos Deputados')
    try:
        with open('C:/Users/RodrigoPintoMesquita/Documents/GitHub/DR4_AT/data/insights_despesas_deputados.json', 'r', encoding='utf-8') as f:
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
        df_despesas = pd.read_parquet('C:/Users/RodrigoPintoMesquita/Documents/GitHub/DR4_AT/data/serie_despesas_diárias_deputados.parquet')
        
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
    st.title('Resumo das Proposições em Tramitação')
    try:
        with open('C:/Users/RodrigoPintoMesquita/Documents/GitHub/DR4_AT/data/sumarizacao_proposicoes.json', 'r', encoding='utf-8') as file:
            for line in file:
                st.markdown(line.strip())
    except FileNotFoundError:
        st.error("Arquivo sumarizacao_proposicoes não encontrado.")
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")