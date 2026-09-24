"""
Leitura da base e filtros compartilhados pelas páginas do painel.

Todas as páginas importam deste arquivo, para que a base seja lida uma vez
só e as medidas sejam calculadas sempre da mesma forma.
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

PASTA_DADOS = Path(__file__).parent / "dados"
ARQUIVO_DADOS = PASTA_DADOS / "SAR_2021-2025_consolidado.xlsx"
ABA_DADOS = "Base de dados"

# Áreas de jurisdição dos Distritos Navais, já simplificadas por
# preparar_areas.py. Cada arquivo tem a área de um Distrito.
PASTA_AREAS = PASTA_DADOS / "areas"

# Colunas da planilha usadas no painel e o nome simplificado de cada uma no código.
COLUNAS = {
    "IDENTIFICADOR SAR": "identificador",
    "ANO": "ano",
    "DATA ABERTURA": "data_abertura",
    "DISTRITO NAVAL": "distrito_naval",
    "SALVAMAR": "salvamar",
    "TIPO INCIDENTE (ANEMAR)": "tipo_incidente",
    "CLASSE DA EMBARCAÇÃO": "classe_embarcacao",
    "RSC (PADRONIZADO)": "om_responsavel",
    "SITUAÇÃO DO EVENTO": "situacao_evento",
    "DURAÇÃO (DIAS)": "duracao",
    "LATITUDE (GD)": "latitude",
    "LONGITUDE (GD)": "longitude",
    "SITUAÇÃO COORDENADA": "situacao_coordenada",
    "VIDAS SALVAS MB": "salvas_mb",
    "VIDAS SALVAS EXTRA-MB": "salvas_extra_mb",
    "SOBREVIVENTES SEM RESGATE": "sobreviventes_sem_resgate",
    "ÓBITOS": "obitos",
    "VIDAS AINDA DESAPARECIDAS": "desaparecidos",
}

# Cor conforme a situação das pessoas envolvidas no incidente. As mesmas cores
# valem em todas as páginas: vermelho é sempre óbito ou desaparecido.
# Vermelho e azul (em vez de vermelho e verde) para que pessoas com
# daltonismo também consigam diferenciar as cores.
CORES = {
    "Com óbito ou desaparecido": "#d03b3b",
    "Somente sobreviventes": "#2a78d6",
    "Sem registro de pessoas": "#8a8984",
}

COR_GRAVE = CORES["Com óbito ou desaparecido"]
COR_SALVAS = CORES["Somente sobreviventes"]

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


# ---------------------------------------------------------------------------
# Leitura da base
# ---------------------------------------------------------------------------

@st.cache_data
def carregar_dados():
    """Lê a planilha e prepara as colunas usadas no painel."""
    df = pd.read_excel(ARQUIVO_DADOS, sheet_name=ABA_DADOS, usecols=list(COLUNAS))
    df = df.rename(columns=COLUNAS)

    # Células vazias nas colunas de pessoas são tratadas como zero.
    colunas_pessoas = ["salvas_mb", "salvas_extra_mb", "sobreviventes_sem_resgate", "obitos", "desaparecidos"]
    df[colunas_pessoas] = df[colunas_pessoas].fillna(0).astype(int)

    # Sobreviventes = salvos pela MB + salvos por meios extra-MB + sobreviventes
    # sem resgate, a mesma soma da aba "SOBREVIVENTES, DESAPAR., ÓBITOS".
    df["sobreviventes"] = df["salvas_mb"] + df["salvas_extra_mb"] + df["sobreviventes_sem_resgate"]

    # Medida central do projeto: o evento teve ao menos um óbito ou desaparecido.
    df["grave"] = (df["obitos"] > 0) | (df["desaparecidos"] > 0)

    df["situacao_pessoas"] = df.apply(classificar_situacao, axis=1)

    df["mes"] = pd.to_datetime(df["data_abertura"]).dt.month
    df["mes_nome"] = df["mes"].map(lambda m: MESES[m - 1])

    # Número do Distrito Naval. Na planilha ele vem como "1ºDN".
    df["numero_distrito"] = df["distrito_naval"].str.extract(r"(\d+)").astype(int)

    return df


def classificar_situacao(incidente):
    """Define o grupo (e, portanto, a cor) de um incidente."""
    if incidente["obitos"] > 0 or incidente["desaparecidos"] > 0:
        return "Com óbito ou desaparecido"
    if incidente["sobreviventes"] > 0:
        return "Somente sobreviventes"
    return "Sem registro de pessoas"


# ---------------------------------------------------------------------------
# Filtros do menu lateral
# ---------------------------------------------------------------------------

# Chaves dos filtros. São as mesmas em todas as páginas, para que a escolha
# do usuário continue valendo ao trocar de página.
CHAVES_FILTROS = [
    "filtro_ano",
    "filtro_salvamar",
    "filtro_tipo",
    "filtro_obitos",
    "filtro_desaparecidos",
    "filtro_sobreviventes",
]


def manter_filtros():
    """
    Mantém os filtros ao trocar de página.

    O Streamlit descarta o valor guardado de um widget que não aparece na
    tela atual. Ao trocar de página, os filtros seriam esquecidos. Regravar
    cada valor sobre ele mesmo, antes de desenhar os widgets, evita esse
    descarte.
    """
    for chave in CHAVES_FILTROS:
        if chave in st.session_state:
            st.session_state[chave] = st.session_state[chave]


def filtros_laterais(df, com_pessoas=True):
    """
    Desenha os filtros no menu lateral e devolve os incidentes filtrados.

    Um filtro vazio não restringe nada.
    """
    manter_filtros()

    with st.sidebar:
        st.header("Filtros")

        anos = st.multiselect(
            "Ano", sorted(df["ano"].unique()), placeholder="Todos os anos", key="filtro_ano"
        )

        # Salvamares na ordem dos Distritos Navais (1º DN, 2º DN, ...).
        lista_salvamares = df.sort_values("numero_distrito")["salvamar"].unique()
        salvamares = st.multiselect(
            "Salvamar", lista_salvamares, placeholder="Todos os Salvamares", key="filtro_salvamar"
        )

        tipos = st.multiselect(
            "Tipo de incidente",
            sorted(df["tipo_incidente"].unique()),
            placeholder="Todos os tipos",
            key="filtro_tipo",
        )

        com_obitos = com_desaparecidos = com_sobreviventes = False
        if com_pessoas:
            st.subheader("Pessoas envolvidas")
            st.caption(
                "Mostra os incidentes que atendem a pelo menos uma opção marcada. "
                "Sem marcação, mostra todos."
            )
            com_obitos = st.checkbox("Com óbitos", key="filtro_obitos")
            com_desaparecidos = st.checkbox(
                "Com desaparecidos",
                help="Pessoas que permanecem desaparecidas.",
                key="filtro_desaparecidos",
            )
            com_sobreviventes = st.checkbox(
                "Com sobreviventes",
                help="Vidas salvas pela MB, vidas salvas por meios extra-MB e sobreviventes sem resgate.",
                key="filtro_sobreviventes",
            )

        st.divider()
        st.caption("Fonte: base consolidada dos eventos SAR do SALVAMAR BRASIL, 2021 a 2025.")

    return filtrar_incidentes(
        df, anos, salvamares, tipos, com_obitos, com_desaparecidos, com_sobreviventes
    )


def filtrar_incidentes(df, anos, salvamares, tipos, com_obitos, com_desaparecidos, com_sobreviventes):
    """Aplica os filtros. Um filtro vazio não restringe nada."""
    if anos:
        df = df[df["ano"].isin(anos)]
    if salvamares:
        df = df[df["salvamar"].isin(salvamares)]
    if tipos:
        df = df[df["tipo_incidente"].isin(tipos)]

    # Pessoas envolvidas: mantém o incidente que atende a pelo menos uma das opções marcadas.
    if com_obitos or com_desaparecidos or com_sobreviventes:
        atende = pd.Series(False, index=df.index)
        if com_obitos:
            atende = atende | (df["obitos"] > 0)
        if com_desaparecidos:
            atende = atende | (df["desaparecidos"] > 0)
        if com_sobreviventes:
            atende = atende | (df["sobreviventes"] > 0)
        df = df[atende]

    return df


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def formatar_numero(numero):
    """Formata um número no padrão brasileiro (ex.: 1.391)."""
    return f"{numero:,}".replace(",", ".")


# Cores do próprio gráfico (texto, eixos e grade), no tom escuro do painel.
COR_TEXTO = "#fafafa"
COR_TEXTO_SUAVE = "#c3c2b7"
COR_GRADE = "#31333f"


def mostrar_grafico(grafico, altura=None):
    """
    Exibe um gráfico Altair já ajustado ao fundo escuro do painel.

    O tema pronto do Streamlit troca as cores das escalas por conta própria,
    o que desfaria as cores escolhidas para o projeto. Por isso ele é
    desligado (theme=None) e o visual é definido aqui: fundo transparente,
    texto claro e grade discreta, para o dado ficar em primeiro plano.
    """
    if altura:
        grafico = grafico.properties(height=altura)

    grafico = grafico.configure_view(
        strokeWidth=0
    ).configure_axis(
        labelColor=COR_TEXTO_SUAVE,
        titleColor=COR_TEXTO_SUAVE,
        gridColor=COR_GRADE,
        domainColor=COR_GRADE,
        tickColor=COR_GRADE,
        labelFontSize=12,
        titleFontSize=12,
        titleFontWeight="normal",
    ).configure_legend(
        labelColor=COR_TEXTO_SUAVE,
        titleColor=COR_TEXTO_SUAVE,
        titleFontWeight="normal",
    ).configure(background="transparent")

    st.altair_chart(grafico, width="stretch", theme=None)


def aviso_sem_dados(incidentes):
    """
    Interrompe a página quando os filtros não deixaram nenhum incidente.
    Evita gráficos vazios e divisões por zero.
    """
    if incidentes.empty:
        st.warning("Nenhum incidente atende aos filtros escolhidos. Ajuste o menu lateral.")
        st.stop()


def verificar_base():
    """Interrompe a página com uma mensagem clara se a planilha não estiver no lugar."""
    if not ARQUIVO_DADOS.exists():
        st.error(f"Arquivo de dados não encontrado. Coloque a planilha em: {ARQUIVO_DADOS}")
        st.stop()
