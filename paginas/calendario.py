"""
Quando as ocorrências acontecem.

Responde à pergunta "as ocorrências se repetem no mesmo período do ano em
cada Salvamar?", com o total por mês e o índice sazonal de cada Salvamar.
"""

import altair as alt
import pandas as pd
import streamlit as st

from dados_sar import (
    COR_SALVAS,
    MESES,
    aviso_sem_dados,
    carregar_dados,
    filtros_laterais,
    formatar_numero,
    mostrar_grafico,
    verificar_base,
)

# Escala divergente do mapa de calor. O meio é cinza, porque "na média" deve
# parecer "nada"; azul puxa para baixo da média e vermelho para cima. Todos os
# tons são escuros o bastante para o número branco dentro da célula ser lido.
#
# Os tons intermediários são declarados, e não calculados: deixando o programa
# misturar azul e cinza sozinho, ele passa por um verde que não quer dizer nada
# aqui. interpolate="rgb" mantém a mistura no caminho mais direto.
ESCALA_SAZONAL = alt.Scale(
    domain=[0.4, 0.7, 1.0, 1.3, 1.6],
    range=["#1c5cab", "#26456b", "#383835", "#6b3130", "#b03232"],
    interpolate="rgb",
    clamp=True,
)


def eventos_por_mes(incidentes):
    """Conta os incidentes de cada mês, incluindo meses sem nenhum."""
    contagem = incidentes["mes"].value_counts().reindex(range(1, 13), fill_value=0)
    return pd.DataFrame({
        "mes": contagem.index,
        "mes_nome": [MESES[m - 1] for m in contagem.index],
        "eventos": contagem.values,
    })


def indice_sazonal(incidentes):
    """
    Calcula, para cada Salvamar e mês, duas medidas:

    - índice sazonal: eventos do mês divididos pela média mensal do próprio
      Salvamar. 1 é a média; 1,5 significa 50% acima dela.
    - anos acima da média: em quantos anos aquele mês ficou acima da média
      mensal daquele Salvamar naquele ano. Mostra se o pico se repete ou se
      veio de um ano isolado.
    """
    salvamares = incidentes.sort_values("numero_distrito")["salvamar"].unique()
    anos = sorted(incidentes["ano"].unique())

    # Grade completa de Salvamar x ano x mês, para que meses sem evento
    # contem como zero em vez de sumirem da conta.
    grade = pd.MultiIndex.from_product(
        [salvamares, anos, range(1, 13)], names=["salvamar", "ano", "mes"]
    ).to_frame(index=False)

    por_ano = incidentes.groupby(["salvamar", "ano", "mes"]).size().rename("eventos")
    por_ano = grade.merge(por_ano, on=["salvamar", "ano", "mes"], how="left").fillna({"eventos": 0})

    media_do_ano = por_ano.groupby(["salvamar", "ano"])["eventos"].transform("mean")
    por_ano["acima"] = por_ano["eventos"] > media_do_ano

    tabela = por_ano.groupby(["salvamar", "mes"]).agg(
        eventos=("eventos", "sum"), anos_acima=("acima", "sum")
    ).reset_index()

    media_mensal = tabela.groupby("salvamar")["eventos"].transform("mean")
    tabela["indice"] = tabela["eventos"] / media_mensal.where(media_mensal > 0)
    tabela["mes_nome"] = tabela["mes"].map(lambda m: MESES[m - 1])

    # Total de cada Salvamar, para o rótulo do eixo mostrar o tamanho da amostra.
    totais = incidentes["salvamar"].value_counts()
    ordem = list(salvamares)
    tabela["rotulo"] = tabela["salvamar"].map(lambda s: f"{s.replace('SALVAMAR ', '').title()} (n={totais.get(s, 0)})")
    ordem_rotulos = [f"{s.replace('SALVAMAR ', '').title()} (n={totais.get(s, 0)})" for s in ordem]

    return tabela.dropna(subset=["indice"]), ordem_rotulos, len(anos)


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

st.title("Quando as ocorrências acontecem")
st.caption(
    "As ocorrências se repetem no mesmo período do ano em cada Salvamar? "
    "O total nacional varia pouco entre os meses, mas cada Salvamar tem seus próprios picos."
)

verificar_base()
df = carregar_dados()
incidentes = filtros_laterais(df)
aviso_sem_dados(incidentes)

# --- Total por mês, no conjunto filtrado ---------------------------------
por_mes = eventos_por_mes(incidentes)
mes_menor = por_mes.loc[por_mes["eventos"].idxmin()]
mes_maior = por_mes.loc[por_mes["eventos"].idxmax()]

st.subheader("Total de eventos por mês")

col1, col2, col3 = st.columns(3)
col1.metric("Eventos no período", formatar_numero(len(incidentes)))
col2.metric("Mês com menos eventos", f"{mes_menor['mes_nome']} ({mes_menor['eventos']})")
col3.metric("Mês com mais eventos", f"{mes_maior['mes_nome']} ({mes_maior['eventos']})")

grafico_mes = (
    alt.Chart(por_mes)
    .mark_bar(color=COR_SALVAS, cornerRadiusEnd=4, size=28)
    .encode(
        x=alt.X("mes_nome:N", sort=MESES, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("eventos:Q", title="Eventos"),
        tooltip=[
            alt.Tooltip("mes_nome:N", title="Mês"),
            alt.Tooltip("eventos:Q", title="Eventos"),
        ],
    )
    .properties(height=260)
)
mostrar_grafico(grafico_mes)

st.divider()

# --- Índice sazonal por Salvamar -----------------------------------------
st.subheader("Índice sazonal por Salvamar")
st.caption(
    "Cada célula compara o mês com a média mensal do próprio Salvamar: 1 é a média e "
    "1,5 significa 50% acima dela. Assim, Salvamares com muitos e com poucos eventos "
    "podem ser lidos na mesma escala. Passe o mouse para ver em quantos anos aquele "
    "mês ficou acima da média."
)

sazonal, ordem_salvamares, total_anos = indice_sazonal(incidentes)

base = alt.Chart(sazonal).encode(
    x=alt.X("mes_nome:N", sort=MESES, title=None, axis=alt.Axis(labelAngle=0)),
    y=alt.Y("rotulo:N", sort=ordem_salvamares, title=None),
    tooltip=[
        alt.Tooltip("salvamar:N", title="Salvamar"),
        alt.Tooltip("mes_nome:N", title="Mês"),
        alt.Tooltip("eventos:Q", title="Eventos no mês"),
        alt.Tooltip("indice:Q", title="Índice sazonal", format=".2f"),
        alt.Tooltip("anos_acima:Q", title=f"Acima da média em (de {total_anos} anos)"),
    ],
)

celulas = base.mark_rect(stroke="#0e1117", strokeWidth=2).encode(
    color=alt.Color(
        "indice:Q",
        scale=ESCALA_SAZONAL,
        legend=alt.Legend(title="Índice sazonal", format=".1f"),
    )
)

# O valor dentro da célula deixa o mapa de calor servir também como tabela.
numeros = base.mark_text(fontSize=11, color="#fafafa").encode(
    text=alt.Text("indice:Q", format=".1f")
)

mostrar_grafico(celulas + numeros, altura=340)

st.caption(
    "O índice mostra o tamanho do pico, e os anos acima da média mostram se ele se repete. "
    "Um índice alto vindo de um único ano é um episódio isolado, não um padrão sazonal."
)
