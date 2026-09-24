"""
Mapa dos incidentes SAR (Busca e Salvamento) registrados de 2021 a 2025.

Projeto Integrador I - MBA em IA e Ciência de Dados para Transformação
Digital na Defesa (FGV/EMAP) - Grupo IV.

Para executar:
    streamlit run app.py
"""

import json
import re
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from folium.plugins import TreeLayerControl

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

PASTA_DADOS = Path(__file__).parent / "dados"
ARQUIVO_DADOS = PASTA_DADOS / "SAR_2021-2025_consolidado.xlsx"
ABA_DADOS = "Base de dados"

# Áreas de jurisdição dos Distritos Navais, já simplificadas por
# preparar_areas.py. Cada arquivo tem a área de um Distrito.
PASTA_AREAS = PASTA_DADOS / "areas"

# Colunas da planilha usadas no mapa e o nome simplificado de cada uma no código.
COLUNAS = {
    "IDENTIFICADOR SAR": "identificador",
    "ANO": "ano",
    "DATA ABERTURA": "data_abertura",
    "DISTRITO NAVAL": "distrito_naval",
    "SALVAMAR": "salvamar",
    "TIPO INCIDENTE (ANEMAR)": "tipo_incidente",
    "CLASSE DA EMBARCAÇÃO": "classe_embarcacao",
    "SITUAÇÃO DO EVENTO": "situacao_evento",
    "LATITUDE (GD)": "latitude",
    "LONGITUDE (GD)": "longitude",
    "SITUAÇÃO COORDENADA": "situacao_coordenada",
    "VIDAS SALVAS MB": "salvas_mb",
    "VIDAS SALVAS EXTRA-MB": "salvas_extra_mb",
    "SOBREVIVENTES SEM RESGATE": "sobreviventes_sem_resgate",
    "ÓBITOS": "obitos",
    "VIDAS AINDA DESAPARECIDAS": "desaparecidos",
}

# Cor dos marcadores conforme a situação das pessoas envolvidas no incidente.
# Vermelho e azul (em vez de vermelho e verde) para que pessoas com
# daltonismo também consigam diferenciar as cores.
CORES = {
    "Com óbito ou desaparecido": "#d03b3b",
    "Somente sobreviventes": "#2a78d6",
    "Sem registro de pessoas": "#8a8984",
}

# Cor da área de cada Distrito Naval, pelo número do Distrito.
#
# São quatro cores para nove áreas. Nove tons bem diferentes entre si não
# existem: alguns ficariam parecidos demais, inclusive para quem tem
# daltonismo. Como no mapa o que importa é enxergar onde uma área termina e
# a outra começa, basta que Distritos vizinhos tenham cores diferentes, e é
# assim que as cores abaixo foram distribuídas. Distritos que dividem a mesma
# cor ficam longe um do outro (por exemplo, o 1º no Rio e o 9º em Manaus).
#
# Os tons também evitam o vermelho e o azul dos marcadores, para não
# confundir a área com a situação das pessoas.
# Um Distrito sem cor na lista fica cinza.
CORES_AREAS = {
    1: "#eda100",  # amarelo
    2: "#1baf7a",  # verde-água
    3: "#eda100",
    4: "#4a3aa7",  # violeta
    5: "#eda100",
    6: "#1baf7a",
    7: "#e87ba4",  # rosa
    8: "#4a3aa7",
    9: "#eda100",
}
COR_AREA_PADRAO = "#8a8984"

# CSS para o mapa ocupar toda a tela, abaixo do título.
ESTILO = """
<style>
    .block-container { padding: 3rem 1rem 0 1rem; }
    iframe { height: calc(100vh - 9rem) !important; }
</style>
"""


# ---------------------------------------------------------------------------
# Funções
# ---------------------------------------------------------------------------

@st.cache_data
def carregar_dados():
    """Lê a planilha e prepara as colunas usadas no mapa."""
    df = pd.read_excel(ARQUIVO_DADOS, sheet_name=ABA_DADOS, usecols=list(COLUNAS))
    df = df.rename(columns=COLUNAS)

    # Células vazias nas colunas de pessoas são tratadas como zero.
    colunas_pessoas = ["salvas_mb", "salvas_extra_mb", "sobreviventes_sem_resgate", "obitos", "desaparecidos"]
    df[colunas_pessoas] = df[colunas_pessoas].fillna(0).astype(int)

    # Sobreviventes = salvos pela MB + salvos por meios extra-MB + sobreviventes sem resgate,
    # a mesma soma usada na aba "SOBREVIVENTES, DESAPAR., ÓBITOS" da planilha.
    df["sobreviventes"] = df["salvas_mb"] + df["salvas_extra_mb"] + df["sobreviventes_sem_resgate"]

    df["situacao_pessoas"] = df.apply(classificar_situacao, axis=1)
    return df


@st.cache_data
def carregar_areas(salvamar_por_distrito):
    """
    Lê as áreas dos Distritos Navais da pasta dados/areas.

    Devolve uma lista com o número, o rótulo e o desenho (GeoJSON) de cada
    área, na ordem do número do Distrito.
    """
    areas = []
    for arquivo in sorted(PASTA_AREAS.glob("*.json")):
        geojson = json.loads(arquivo.read_text(encoding="utf-8"))
        propriedades = geojson["features"][0]["properties"]

        # O número do Distrito. A sigla varia de arquivo para arquivo
        # ("1° DN", "6º DN", "9º"), por isso usamos o campo id_dn.
        numero = int(propriedades["id_dn"])

        # O nome do Salvamar vem da planilha, para usar as mesmas palavras do
        # filtro lateral. Um Distrito ausente da planilha fica sem esse trecho.
        salvamar = salvamar_por_distrito.get(numero)
        rotulo = f"{numero}º DN" + (f" — {salvamar}" if salvamar else "")

        areas.append({"numero": numero, "rotulo": rotulo, "geojson": geojson})

    return sorted(areas, key=lambda area: area["numero"])


def classificar_situacao(incidente):
    """Define o grupo (e, portanto, a cor) de um incidente."""
    if incidente["obitos"] > 0 or incidente["desaparecidos"] > 0:
        return "Com óbito ou desaparecido"
    if incidente["sobreviventes"] > 0:
        return "Somente sobreviventes"
    return "Sem registro de pessoas"


def filtrar_incidentes(df, anos, salvamares, tipos, com_obitos, com_desaparecidos, com_sobreviventes):
    """Aplica os filtros do menu lateral. Um filtro vazio não restringe nada."""
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


def texto_popup(incidente):
    """Monta o texto (HTML) que aparece ao clicar em um incidente."""
    texto = (
        f"<b>{incidente['identificador']}</b><br>"
        f"Abertura: {incidente['data_abertura']:%d/%m/%Y}<br>"
        f"{incidente['salvamar']}<br>"
        f"Tipo: {incidente['tipo_incidente']}<br>"
        f"Embarcação: {incidente['classe_embarcacao']}<br>"
        f"Situação do evento: {incidente['situacao_evento']}<br>"
        f"<hr style='margin:4px 0'>"
        f"Sobreviventes: {incidente['sobreviventes']}<br>"
        f"Óbitos: {incidente['obitos']}<br>"
        f"Desaparecidos: {incidente['desaparecidos']}"
    )
    if incidente["situacao_coordenada"] != "OK":
        texto += f"<br><i>Posição {incidente['situacao_coordenada']}</i>"
    return texto


def criar_mapa(incidentes, areas):
    """Cria o mapa do OpenStreetMap com as áreas dos Distritos e os incidentes."""
    mapa = folium.Map(location=[-15, -45], zoom_start=4, tiles="OpenStreetMap")

    # As áreas entram primeiro, para ficarem embaixo dos incidentes.
    adicionar_areas(mapa, areas)

    # Desenha os grupos na ordem inversa da legenda, para que os incidentes
    # com óbito ou desaparecido fiquem por cima dos demais.
    for situacao in reversed(list(CORES)):
        grupo = incidentes[incidentes["situacao_pessoas"] == situacao]
        for _, incidente in grupo.iterrows():
            folium.CircleMarker(
                location=[incidente["latitude"], incidente["longitude"]],
                radius=6,
                color="white",  # borda branca destaca o círculo do fundo
                weight=1,
                fill=True,
                fill_color=CORES[situacao],
                fill_opacity=0.9,
                tooltip=f"{incidente['identificador']} | {incidente['tipo_incidente']}",
                popup=folium.Popup(texto_popup(incidente), max_width=300),
            ).add_to(mapa)

    # Aproxima o mapa da área onde estão os incidentes filtrados.
    if not incidentes.empty:
        canto_sudoeste = [incidentes["latitude"].min(), incidentes["longitude"].min()]
        canto_nordeste = [incidentes["latitude"].max(), incidentes["longitude"].max()]
        mapa.fit_bounds([canto_sudoeste, canto_nordeste], max_zoom=9)

    adicionar_legenda(mapa, incidentes)
    return mapa


def adicionar_areas(mapa, areas):
    """
    Desenha a área de cada Distrito Naval e cria, no canto superior direito,
    o menu que liga e desliga cada área e todas de uma vez.
    """
    if not areas:
        return

    itens_do_menu = []
    for area in areas:
        cor = CORES_AREAS.get(area["numero"], COR_AREA_PADRAO)

        # Cada área fica em seu próprio grupo, para poder ser ligada e
        # desligada sozinha pelo menu.
        grupo = folium.FeatureGroup(name=area["rotulo"], show=True)
        folium.GeoJson(
            area["geojson"],
            # O preenchimento é bem claro, para não esconder o mapa nem
            # competir com as cores dos incidentes.
            style_function=lambda _, cor=cor: {
                "color": cor,
                "weight": 2.5,
                "fillColor": cor,
                "fillOpacity": 0.08,
            },
            tooltip=area["rotulo"],
        ).add_to(grupo)
        grupo.add_to(mapa)

        itens_do_menu.append({"label": area["rotulo"], "layer": grupo})

    TreeLayerControl(
        overlay_tree={
            "label": "Áreas dos Distritos Navais",
            "selectAllCheckbox": "Ligar ou desligar todas as áreas",
            "children": itens_do_menu,
        },
        position="topright",
        collapsed=False,
    ).add_to(mapa)


def adicionar_legenda(mapa, incidentes):
    """Adiciona ao mapa um quadro com o total de incidentes e o significado de cada cor."""
    contagem = incidentes["situacao_pessoas"].value_counts()

    linhas = [f"<b>{formatar_numero(len(incidentes))} incidentes no mapa</b>"]
    for situacao, cor in CORES.items():
        quantidade = formatar_numero(int(contagem.get(situacao, 0)))
        linhas.append(f"<span style='color:{cor}; font-size:16px'>●</span> {situacao}: {quantidade}")
    conteudo = "<br>".join(linhas)

    legenda = f"""
    <div style="position: fixed; bottom: 25px; left: 10px; z-index: 1000;
                background: white; padding: 8px 12px; border-radius: 6px;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
                font: 13px sans-serif; line-height: 1.6;">
        {conteudo}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legenda))


def formatar_numero(numero):
    """Formata um número no padrão brasileiro (ex.: 1.391)."""
    return f"{numero:,}".replace(",", ".")


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Incidentes SAR 2021-2025", page_icon="⚓", layout="wide")
st.html(ESTILO)
st.title("Mapa dos incidentes SAR, 2021 a 2025")

if not ARQUIVO_DADOS.exists():
    st.error(f"Arquivo de dados não encontrado. Coloque a planilha em: {ARQUIVO_DADOS}")
    st.stop()

df = carregar_dados()

# Menu lateral com os filtros.
with st.sidebar:
    st.header("Filtros")

    anos = st.multiselect("Ano", sorted(df["ano"].unique()), placeholder="Todos os anos")

    # Salvamares na ordem dos Distritos Navais (1º DN, 2º DN, ...).
    lista_salvamares = df.sort_values("distrito_naval")["salvamar"].unique()
    salvamares = st.multiselect("Salvamar", lista_salvamares, placeholder="Todos os Salvamares")

    tipos = st.multiselect(
        "Tipo de incidente", sorted(df["tipo_incidente"].unique()), placeholder="Todos os tipos"
    )

    st.subheader("Pessoas envolvidas")
    st.caption("Mostra os incidentes que atendem a pelo menos uma opção marcada. Sem marcação, mostra todos.")
    com_obitos = st.checkbox("Com óbitos")
    com_desaparecidos = st.checkbox(
        "Com desaparecidos", help="Pessoas que permanecem desaparecidas."
    )
    com_sobreviventes = st.checkbox(
        "Com sobreviventes", help="Vidas salvas pela MB, vidas salvas por meios extra-MB e sobreviventes sem resgate."
    )

    st.divider()
    st.caption("Fonte: base consolidada dos eventos SAR do SALVAMAR BRASIL, 2021 a 2025.")

incidentes = filtrar_incidentes(
    df, anos, salvamares, tipos, com_obitos, com_desaparecidos, com_sobreviventes
)

# Nome do Salvamar de cada Distrito Naval, para rotular as áreas do mapa.
# Na planilha o Distrito vem como "1ºDN"; aqui guardamos apenas o número.
salvamar_por_distrito = {
    int(re.search(r"\d+", distrito).group()): salvamar
    for distrito, salvamar in df[["distrito_naval", "salvamar"]].drop_duplicates().values
}

# Mapa ocupando o restante da tela.
mapa = criar_mapa(incidentes, carregar_areas(salvamar_por_distrito))
st.iframe(mapa.get_root().render(), height=600)
