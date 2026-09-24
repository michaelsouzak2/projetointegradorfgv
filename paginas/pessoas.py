"""
Sobreviventes, óbitos e desaparecidos.

Responde à pergunta "que tipos de incidente e de embarcação estão mais
associados a óbitos e desaparecidos?", usando as duas medidas propostas
pelo projeto.
"""

import altair as alt
import pandas as pd
import streamlit as st

from dados_sar import (
    COR_GRAVE,
    COR_SALVAS,
    COR_TEXTO_SUAVE,
    aviso_sem_dados,
    carregar_dados,
    filtros_laterais,
    formatar_numero,
    mostrar_grafico,
    verificar_base,
)

# Dimensões que podem ser comparadas, e a coluna correspondente na base.
DIMENSOES = {
    "Tipo de incidente": "tipo_incidente",
    "Classe da embarcação": "classe_embarcacao",
    "Salvamar": "salvamar",
}


def resumir_por(incidentes, coluna):
    """
    Calcula as duas medidas do projeto para cada categoria:

    - eventos com óbito ou desaparecido: quantos eventos tiveram ao menos uma
      vítima. Mostra com que frequência o incidente termina mal.
    - pessoas salvas: sobreviventes divididos pelo total de pessoas envolvidas
      (sobreviventes + óbitos + desaparecidos). Mostra o desfecho das pessoas.

    As duas são necessárias. Na colisão, por exemplo, quase todo evento tem
    vítima, mas a maior parte das pessoas envolvidas é salva.
    """
    resumo = incidentes.groupby(coluna).agg(
        eventos=("identificador", "size"),
        eventos_graves=("grave", "sum"),
        sobreviventes=("sobreviventes", "sum"),
        obitos=("obitos", "sum"),
        desaparecidos=("desaparecidos", "sum"),
    ).reset_index()

    resumo["pct_eventos_graves"] = 100 * resumo["eventos_graves"] / resumo["eventos"]

    pessoas = resumo["sobreviventes"] + resumo["obitos"] + resumo["desaparecidos"]
    # Categorias sem nenhuma pessoa registrada ficam sem a segunda medida.
    resumo["pct_pessoas_salvas"] = 100 * resumo["sobreviventes"] / pessoas.where(pessoas > 0)

    resumo["rotulo"] = resumo[coluna] + " (n=" + resumo["eventos"].astype(str) + ")"
    return resumo.sort_values("eventos", ascending=False)


def grafico_barras(resumo, campo, titulo, cor, ordem, media=None):
    """Barras horizontais de uma medida, com o valor no fim de cada barra."""
    base = alt.Chart(resumo).encode(
        # labelLimit alto para os nomes longos aparecerem inteiros, sem "...".
        y=alt.Y("rotulo:N", sort=ordem, title=None, axis=alt.Axis(labelLimit=400)),
        x=alt.X(f"{campo}:Q", title=titulo, scale=alt.Scale(domain=[0, 100])),
        tooltip=[
            alt.Tooltip("rotulo:N", title="Categoria"),
            alt.Tooltip("eventos:Q", title="Eventos"),
            alt.Tooltip("pct_eventos_graves:Q", title="Eventos com óbito ou desap. (%)", format=".0f"),
            alt.Tooltip("pct_pessoas_salvas:Q", title="Pessoas salvas (%)", format=".0f"),
            alt.Tooltip("obitos:Q", title="Óbitos"),
            alt.Tooltip("desaparecidos:Q", title="Desaparecidos"),
            alt.Tooltip("sobreviventes:Q", title="Sobreviventes"),
        ],
    )

    barras = base.mark_bar(color=cor, cornerRadiusEnd=4, size=18)
    valores = base.mark_text(align="left", dx=6, color="#fafafa", fontSize=12).encode(
        text=alt.Text(f"{campo}:Q", format=".0f")
    )
    camadas = [barras, valores]

    # Linha de referência com a média geral do conjunto filtrado.
    if media is not None:
        regua = (
            alt.Chart(pd.DataFrame({"media": [media]}))
            .mark_rule(color=COR_TEXTO_SUAVE, strokeWidth=2)
            .encode(x=alt.X("media:Q"), tooltip=alt.Tooltip("media:Q", title="Média geral", format=".0f"))
        )
        camadas.insert(0, regua)

    return alt.layer(*camadas).properties(height=max(200, 34 * len(resumo)))


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

st.title("Sobreviventes, óbitos e desaparecidos")
st.caption(
    "Que tipos de incidente e de embarcação estão mais associados a óbitos e desaparecidos? "
    "A leitura usa duas medidas ao mesmo tempo, porque cada uma responde a uma pergunta diferente."
)

verificar_base()
df = carregar_dados()
incidentes = filtros_laterais(df)
aviso_sem_dados(incidentes)

# --- Números gerais -------------------------------------------------------
total_sobreviventes = int(incidentes["sobreviventes"].sum())
total_obitos = int(incidentes["obitos"].sum())
total_desaparecidos = int(incidentes["desaparecidos"].sum())
pct_graves = 100 * incidentes["grave"].mean()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Eventos", formatar_numero(len(incidentes)))
col2.metric("Com óbito ou desaparecido", f"{pct_graves:.0f}%")
col3.metric("Sobreviventes", formatar_numero(total_sobreviventes))
col4.metric("Óbitos", formatar_numero(total_obitos))
col5.metric("Desaparecidos", formatar_numero(total_desaparecidos))

st.divider()

# --- Comparação por dimensão ---------------------------------------------
coluna_escolhida = st.selectbox("Comparar por", list(DIMENSOES))
minimo = st.slider(
    "Mostrar apenas categorias com pelo menos N eventos",
    min_value=1, max_value=50, value=10,
    help="Categorias com poucos eventos produzem percentuais instáveis.",
)

resumo = resumir_por(incidentes, DIMENSOES[coluna_escolhida])
resumo = resumo[resumo["eventos"] >= minimo]

if resumo.empty:
    st.warning("Nenhuma categoria tem eventos suficientes. Diminua o mínimo.")
    st.stop()

ordem = list(resumo.sort_values("pct_eventos_graves", ascending=False)["rotulo"])

# Os dois gráficos ficam um sobre o outro, e não lado a lado, para que os
# nomes das categorias apareçam inteiros. Os dois usam a mesma ordem de
# categorias, então dá para comparar linha a linha.
st.subheader("Eventos com óbito ou desaparecido")
st.caption("De cada 100 eventos da categoria, quantos tiveram ao menos uma vítima.")
mostrar_grafico(
    grafico_barras(resumo, "pct_eventos_graves", "% dos eventos", COR_GRAVE, ordem, media=pct_graves)
)
st.caption("A linha cinza marca a média geral do conjunto filtrado.")

st.subheader("Pessoas salvas")
st.caption(
    "De cada 100 pessoas envolvidas na categoria, quantas foram salvas. "
    "As categorias seguem a mesma ordem do gráfico acima."
)
mostrar_grafico(grafico_barras(resumo, "pct_pessoas_salvas", "% das pessoas", COR_SALVAS, ordem))
st.caption("Sobreviventes divididos por sobreviventes mais óbitos mais desaparecidos.")

st.info(
    "**Por que duas medidas?** As duas contam histórias diferentes. Na colisão, quase todo "
    "evento tem vítima, mas a maior parte das pessoas envolvidas é salva. No homem ao mar, "
    "acontece o contrário. Parte dessa diferença vem da natureza do incidente: o homem ao mar "
    "já começa com uma pessoa na água, enquanto a avaria começa, em geral, com todos a bordo."
)

# --- Tabela com as duas medidas ------------------------------------------
with st.expander("Ver os números em tabela"):
    tabela = resumo.assign(
        **{
            coluna_escolhida: resumo[DIMENSOES[coluna_escolhida]],
            "Eventos": resumo["eventos"],
            "Com óbito ou desap. (%)": resumo["pct_eventos_graves"].round().astype(int),
            "Pessoas salvas (%)": resumo["pct_pessoas_salvas"].round(),
            "Sobreviventes": resumo["sobreviventes"],
            "Óbitos": resumo["obitos"],
            "Desaparecidos": resumo["desaparecidos"],
        }
    )
    st.dataframe(
        tabela[[
            coluna_escolhida, "Eventos", "Com óbito ou desap. (%)", "Pessoas salvas (%)",
            "Sobreviventes", "Óbitos", "Desaparecidos",
        ]],
        hide_index=True,
        width="stretch",
    )

st.caption(
    "O projeto identifica padrões e associações, sem afirmar causas: a base descreve as "
    "ocorrências atendidas, mas não a exposição ao risco, como quantas embarcações navegavam "
    "em cada área."
)
