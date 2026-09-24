"""
Mapa com a posição de cada incidente SAR, colorido pela situação das
pessoas envolvidas, sobre as áreas dos Distritos Navais.
"""

import json

import folium
import streamlit as st
from folium.plugins import TreeLayerControl

from dados_sar import (
    CORES,
    PASTA_AREAS,
    carregar_dados,
    filtros_laterais,
    formatar_numero,
    verificar_base,
)

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


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

st.html(ESTILO)
st.title("Mapa dos incidentes SAR, 2021 a 2025")

verificar_base()
df = carregar_dados()
incidentes = filtros_laterais(df)

# Nome do Salvamar de cada Distrito Naval, para rotular as áreas do mapa.
salvamar_por_distrito = dict(
    df[["numero_distrito", "salvamar"]].drop_duplicates().values
)

mapa = criar_mapa(incidentes, carregar_areas(salvamar_por_distrito))
st.iframe(mapa.get_root().render(), height=600)
