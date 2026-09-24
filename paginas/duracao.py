"""
Duração dos eventos e situação final.

Responde à pergunta "como a duração dos eventos se relaciona com a sua
situação final?".
"""

import altair as alt
import pandas as pd
import streamlit as st

from dados_sar import (
    aviso_sem_dados,
    carregar_dados,
    filtros_laterais,
    formatar_numero,
    mostrar_grafico,
    verificar_base,
)

# Faixas de duração, em dias. São ordenadas, e o gráfico mantém esta ordem.
LIMITES = [-1, 0, 1, 2, 5, 10, 10**6]
FAIXAS = ["0", "1", "2", "3 a 5", "6 a 10", "mais de 10"]

# Uma cor para cada situação final. São duas séries, então a cor identifica
# cada uma, e a legenda diz qual é qual.
CORES_SITUACAO = {
    "Encerrado": "#2a78d6",
    "Suspenso": "#d95926",
}


def distribuicao_por_situacao(incidentes):
    """
    Distribui os eventos de cada situação final pelas faixas de duração.

    O valor é a porcentagem dentro da própria situação, e não o total, porque
    há muito mais eventos encerrados do que suspensos: sem isso, a barra dos
    suspensos praticamente sumiria.
    """
    dados = incidentes.copy()
    dados["faixa"] = pd.cut(dados["duracao"], bins=LIMITES, labels=FAIXAS)

    contagem = (
        dados.groupby(["situacao_evento", "faixa"], observed=False)
        .size()
        .rename("eventos")
        .reset_index()
    )
    total = contagem.groupby("situacao_evento")["eventos"].transform("sum")
    contagem["porcentagem"] = 100 * contagem["eventos"] / total.where(total > 0)

    return contagem.dropna(subset=["porcentagem"])


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

st.title("Duração dos eventos")
st.caption(
    "Como a duração se relaciona com a situação final do evento? "
    "A duração é o número de dias entre a abertura e o último acontecimento registrado."
)

verificar_base()
df = carregar_dados()
incidentes = filtros_laterais(df)
aviso_sem_dados(incidentes)

# --- Números gerais -------------------------------------------------------
st.subheader("Situação final dos eventos")

colunas = st.columns(2 * len(CORES_SITUACAO))
for posicao, situacao in enumerate(CORES_SITUACAO):
    do_grupo = incidentes[incidentes["situacao_evento"] == situacao]
    quantidade = len(do_grupo)
    mediana = do_grupo["duracao"].median() if quantidade else 0

    colunas[2 * posicao].metric(
        f"Eventos {situacao.lower()}s",
        formatar_numero(quantidade),
        f"{round(100 * quantidade / len(incidentes))}% do total",
        delta_color="off",
    )
    colunas[2 * posicao + 1].metric(
        f"Duração mediana ({situacao.lower()})",
        f"{mediana:.0f} dia" + ("s" if mediana != 1 else ""),
    )

st.divider()

# --- Distribuição da duração ---------------------------------------------
st.subheader("Duração por situação final")
st.caption(
    "Cada barra mostra a porcentagem dentro da própria situação, porque há muito mais "
    "eventos encerrados do que suspensos."
)

distribuicao = distribuicao_por_situacao(incidentes)

grafico = (
    alt.Chart(distribuicao)
    .mark_bar(cornerRadiusEnd=4, size=30)
    .encode(
        x=alt.X("faixa:N", sort=FAIXAS, title="Duração do evento (dias)", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("porcentagem:Q", title="% dos eventos da situação"),
        # xOffset separa as duas barras lado a lado, com uma folga entre elas.
        xOffset=alt.XOffset("situacao_evento:N", sort=list(CORES_SITUACAO)),
        color=alt.Color(
            "situacao_evento:N",
            sort=list(CORES_SITUACAO),
            scale=alt.Scale(domain=list(CORES_SITUACAO), range=list(CORES_SITUACAO.values())),
            legend=alt.Legend(title="Situação final"),
        ),
        tooltip=[
            alt.Tooltip("situacao_evento:N", title="Situação final"),
            alt.Tooltip("faixa:N", title="Duração (dias)"),
            alt.Tooltip("eventos:Q", title="Eventos"),
            alt.Tooltip("porcentagem:Q", title="% da situação", format=".0f"),
        ],
    )
    .properties(height=320)
)
mostrar_grafico(grafico)

st.info(
    "**A duração reflete a situação final, e não a explica.** Pela doutrina, o evento é "
    "encerrado quando todo o objeto da busca é encontrado, e suspenso quando as buscas se "
    "esgotam sem localizar as vítimas, o que naturalmente exige mais tempo. A diferença entre "
    "as duas distribuições é consequência do desfecho, não sua causa."
)

st.caption(
    "A Folha de Informação SAR-B-001 registra que, em incidentes com fatalidades, duas horas "
    "costumam ser o tempo crítico para o resgate. Medir esse intervalo exigiria registrar, em "
    "grupo data-hora, o momento do acionamento e o da localização das vítimas. A base traz "
    "apenas datas, sem horário, por isso a duração é medida em dias."
)
