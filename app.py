"""
Painel analítico dos eventos SAR (Busca e Salvamento) de 2021 a 2025.

Projeto Integrador I - MBA em IA e Ciência de Dados para Transformação
Digital na Defesa (FGV/EMAP) - Grupo IV.

Este arquivo só monta o menu de navegação. Cada página fica na pasta
"paginas" e responde a uma das perguntas do projeto.

Para executar:
    streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="Painel SAR 2021-2025", page_icon="⚓", layout="wide")

# A ordem abaixo segue a da proposta do projeto: primeiro o mapa geral e
# depois uma página para cada pergunta específica.
paginas = [
    st.Page("paginas/mapa.py", title="Mapa dos incidentes", icon="🗺️", default=True),
    st.Page("paginas/calendario.py", title="Quando acontecem", icon="📅"),
    st.Page("paginas/areas_recorrentes.py", title="Onde se repetem", icon="📍"),
    st.Page("paginas/pessoas.py", title="Pessoas envolvidas", icon="🛟"),
    st.Page("paginas/duracao.py", title="Duração dos eventos", icon="⏱️"),
]

st.navigation(paginas).run()
