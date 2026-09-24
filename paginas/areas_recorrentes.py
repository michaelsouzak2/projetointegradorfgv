"""
Onde as ocorrências se repetem.

Divide a área de busca em células quadradas e mostra quais delas registram
ocorrências ano após ano, com a organização militar responsável por cada uma.
"""

import folium
import numpy as np
import pandas as pd
import streamlit as st

from dados_sar import (
    aviso_sem_dados,
    carregar_dados,
    filtros_laterais,
    formatar_numero,
    verificar_base,
)

# Lado da célula, em graus. Meio grau equivale a cerca de 55 km.
LADO_CELULA = 0.5

# Faixas de quantidade e a cor de cada uma. É um tom só, do claro ao escuro:
# quanto mais escuro, mais eventos. As cores valem sobre o mapa, que é claro.
FAIXAS = [
    (1, 1, "1 evento", "#86b6ef"),
    (2, 2, "2 eventos", "#5598e7"),
    (3, 5, "3 a 5 eventos", "#2a78d6"),
    (6, 10, "6 a 10 eventos", "#1c5cab"),
    (11, 10**6, "11 ou mais", "#104281"),
]


def cor_da_faixa(eventos):
    """Devolve a cor e o nome da faixa de um número de eventos."""
    for minimo, maximo, nome, cor in FAIXAS:
        if minimo <= eventos <= maximo:
            return cor, nome
    return FAIXAS[-1][3], FAIXAS[-1][2]


@st.cache_data
def montar_celulas(incidentes):
    """
    Agrupa os incidentes em células quadradas e resume cada uma: quantos
    eventos, em quantos anos diferentes, qual a OM responsável, o tipo mais
    frequente e a proporção de eventos com óbito ou desaparecido.
    """
    dados = incidentes.copy()
    dados["celula_x"] = np.floor(dados["longitude"] / LADO_CELULA)
    dados["celula_y"] = np.floor(dados["latitude"] / LADO_CELULA)

    grupos = dados.groupby(["celula_x", "celula_y"])

    def mais_comum(serie):
        return serie.mode().iat[0] if not serie.mode().empty else "—"

    celulas = grupos.agg(
        eventos=("identificador", "size"),
        anos=("ano", "nunique"),
        proporcao_grave=("grave", "mean"),
    ).reset_index()

    celulas["om_responsavel"] = grupos["om_responsavel"].agg(mais_comum).values
    celulas["salvamar"] = grupos["salvamar"].agg(mais_comum).values
    celulas["tipo_frequente"] = grupos["tipo_incidente"].agg(mais_comum).values

    return celulas


def criar_mapa(celulas):
    """Desenha uma área quadrada para cada célula, colorida pela quantidade de eventos."""
    mapa = folium.Map(location=[-15, -45], zoom_start=4, tiles="OpenStreetMap")

    # As células com mais eventos entram por último, para ficarem por cima.
    for _, celula in celulas.sort_values("eventos").iterrows():
        cor, nome_faixa = cor_da_faixa(celula["eventos"])
        sul = celula["celula_y"] * LADO_CELULA
        oeste = celula["celula_x"] * LADO_CELULA

        folium.Rectangle(
            bounds=[[sul, oeste], [sul + LADO_CELULA, oeste + LADO_CELULA]],
            color=cor,
            weight=1,
            fill=True,
            fill_color=cor,
            fill_opacity=0.75,
            tooltip=(
                f"<b>{celula['eventos']} eventos</b> ({nome_faixa})<br>"
                f"Em {celula['anos']} ano(s) diferentes<br>"
                f"{celula['om_responsavel']}<br>"
                f"{celula['salvamar']}<br>"
                f"Tipo mais frequente: {celula['tipo_frequente']}<br>"
                f"Com óbito ou desaparecido: {round(100 * celula['proporcao_grave'])}%"
            ),
        ).add_to(mapa)

    if not celulas.empty:
        sul = celulas["celula_y"].min() * LADO_CELULA
        norte = (celulas["celula_y"].max() + 1) * LADO_CELULA
        oeste = celulas["celula_x"].min() * LADO_CELULA
        leste = (celulas["celula_x"].max() + 1) * LADO_CELULA
        mapa.fit_bounds([[sul, oeste], [norte, leste]], max_zoom=9)

    adicionar_legenda(mapa)
    return mapa


def adicionar_legenda(mapa):
    """Quadro com o significado das cores, no canto inferior esquerdo do mapa."""
    linhas = ["<b>Eventos por área</b>"]
    for _, _, nome, cor in FAIXAS:
        linhas.append(
            f"<span style='display:inline-block; width:12px; height:12px;"
            f" background:{cor}; margin-right:6px'></span>{nome}"
        )

    legenda = f"""
    <div style="position: fixed; bottom: 25px; left: 10px; z-index: 1000;
                background: white; padding: 8px 12px; border-radius: 6px;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
                font: 13px sans-serif; line-height: 1.6;">
        {"<br>".join(linhas)}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legenda))


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

st.title("Onde as ocorrências se repetem")
st.caption(
    f"A área de busca é dividida em células de {LADO_CELULA} grau de lado, cerca de 55 km. "
    "Áreas que registram ocorrências ano após ano são candidatas naturais a ações de prevenção, "
    "porque a demanda ali não é eventual."
)

verificar_base()
df = carregar_dados()
incidentes = filtros_laterais(df)
aviso_sem_dados(incidentes)

celulas = montar_celulas(incidentes)
anos_no_periodo = incidentes["ano"].nunique()
recorrentes = celulas[celulas["anos"] == anos_no_periodo]
eventos_recorrentes = int(recorrentes["eventos"].sum())

col1, col2, col3 = st.columns(3)
col1.metric("Áreas com ocorrência", formatar_numero(len(celulas)))
col2.metric(
    f"Áreas com eventos nos {anos_no_periodo} anos",
    formatar_numero(len(recorrentes)),
    help="Células que registraram ao menos um evento em cada um dos anos selecionados.",
)
col3.metric(
    "Eventos nessas áreas",
    f"{formatar_numero(eventos_recorrentes)} ({round(100 * eventos_recorrentes / len(incidentes))}%)",
    help="Parcela do total de incidentes que caiu nas áreas recorrentes.",
)

somente_recorrentes = st.toggle(
    "Mostrar somente as áreas com ocorrências em todos os anos",
    help="Ajuda a enxergar onde a demanda se repete, em vez de onde ela apenas apareceu uma vez.",
)

mostradas = recorrentes if somente_recorrentes else celulas
if mostradas.empty:
    st.warning("Nenhuma área atende ao critério escolhido.")
    st.stop()

st.iframe(criar_mapa(mostradas).get_root().render(), height=520)

st.divider()

# --- Tabela das áreas recorrentes, uma linha por OM ----------------------
st.subheader("Organizações militares com áreas recorrentes")
st.caption(
    "Para cada OM, a maior de suas áreas recorrentes. O percentual indica quantos "
    "eventos daquela área envolveram ao menos um óbito ou desaparecido."
)

if recorrentes.empty:
    st.info("Nenhuma área registrou ocorrências em todos os anos selecionados.")
else:
    tabela = (
        recorrentes.sort_values("eventos", ascending=False)
        .drop_duplicates("om_responsavel")
        .head(15)
        .assign(com_grave=lambda d: (100 * d["proporcao_grave"]).round().astype(int))
        .rename(columns={
            "om_responsavel": "OM responsável pela área",
            "salvamar": "Salvamar",
            "eventos": "Eventos",
            "tipo_frequente": "Tipo mais frequente",
            "com_grave": "Com óbito ou desap. (%)",
        })
    )
    st.dataframe(
        tabela[[
            "OM responsável pela área", "Salvamar", "Eventos",
            "Tipo mais frequente", "Com óbito ou desap. (%)",
        ]],
        hide_index=True,
        width="stretch",
    )

st.caption(
    "As áreas recorrentes do litoral concentram avarias e embarcações à deriva, com uma "
    "parcela menor de eventos graves. Nas áreas recorrentes do Norte predominam naufrágios "
    "e homem ao mar, e a proporção de eventos com óbito ou desaparecido é bem maior."
)
