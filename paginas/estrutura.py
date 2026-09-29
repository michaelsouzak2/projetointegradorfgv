"""
Estrutura x demanda.

Compara a presença institucional do SAR (quantas organizações militares
existem em cada Distrito Naval) com a quantidade de eventos que cada uma
atende. Não é uma medida de efetivo: a base não registra pessoal,
embarcações ou aeronaves fixados por local, só os meios empregados em cada
evento. O número de OMs é o proxy mais próximo disponível na planilha.
"""

import altair as alt
import pandas as pd
import streamlit as st

from dados_sar import (
    ARQUIVO_DADOS,
    aviso_sem_dados,
    carregar_dados,
    filtros_laterais,
    formatar_numero,
    mostrar_grafico,
    verificar_base,
)

ABA_ESTRUTURA = "ESTRUTURA SAR"

# Capitanias, Delegacias e Agências são as organizações que de fato atendem
# eventos na ponta. Os níveis 1 (SALVAMAR BRASIL) e 2 (os 9 Salvamares
# regionais) ficam de fora da contagem: são coordenação, não presença local.
NIVEIS_OM = [3, 4]

# Cor principal da página: um verde-água, diferente do vermelho e do azul já
# usados no resto do painel para óbito e sobrevivente. Esta página mede outra
# coisa (presença institucional), e reaproveitar essas cores confundiria o
# significado.
COR_RAZAO = "#1baf7a"
COR_ESTRUTURA = "#93a1b8"  # cinza-azulado, para a métrica de apoio (nº de OMs)


@st.cache_data
def carregar_estrutura():
    """
    Lê a aba ESTRUTURA SAR e devolve só as organizações de ponta (Capitania,
    Delegacia, Agência), uma linha por OM.
    """
    estrutura = pd.read_excel(ARQUIVO_DADOS, sheet_name=ABA_ESTRUTURA)
    estrutura = estrutura.rename(columns={
        "ORGANIZAÇÃO MILITAR": "organizacao",
        "TIPO": "tipo_om",
        "LOCALIZAÇÃO": "localizacao",
        "DISTRITO NAVAL": "distrito_naval",
        "SALVAMAR": "salvamar",
    })
    estrutura["numero_distrito"] = estrutura["distrito_naval"].astype(str).str.extract(r"(\d+)").astype(float)
    return estrutura[estrutura["NÍVEL"].isin(NIVEIS_OM)].copy()


def eventos_por_om(incidentes):
    """Conta, na base filtrada, quantos eventos cada OM atendeu."""
    return incidentes.groupby("om_responsavel").size().rename("eventos")


def montar_comparativo(incidentes, oms):
    """
    Uma linha por Distrito Naval, com o número de organizações subordinadas
    (estrutura, fixo) e o número de eventos no período filtrado (demanda).
    """
    estrutura_por_distrito = (
        oms.groupby("numero_distrito").agg(organizacoes=("organizacao", "size"), salvamar=("salvamar", "first"))
    )
    eventos_por_distrito = incidentes.groupby("numero_distrito").size().rename("eventos")

    comparativo = estrutura_por_distrito.join(eventos_por_distrito, how="left").reset_index()
    comparativo["eventos"] = comparativo["eventos"].fillna(0).astype(int)
    comparativo["organizacoes"] = comparativo["organizacoes"].fillna(0).astype(int)

    # Eventos por organização: quanto maior, mais eventos cada OM da região
    # precisa atender em média — um indício de estrutura mais sobrecarregada.
    comparativo["eventos_por_om"] = (
        comparativo["eventos"] / comparativo["organizacoes"].where(comparativo["organizacoes"] > 0)
    ).round(1)
    comparativo["rotulo"] = comparativo["salvamar"].str.replace("SALVAMAR ", "", regex=False).str.title()
    return comparativo.sort_values("eventos_por_om", ascending=False)


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

st.title("Estrutura x demanda")
st.caption(
    "A presença institucional do SAR acompanha onde os eventos se concentram? "
    "Compara o número de organizações militares de cada Salvamar com a quantidade de "
    "eventos que ele atende."
)

verificar_base()
df = carregar_dados()
incidentes = filtros_laterais(df)
aviso_sem_dados(incidentes)

st.info(
    "**O que esta página mede, e o que ela não mede.** A base não registra o efetivo "
    "— pessoal, embarcações ou aeronaves fixados em cada local. O que ela tem são os "
    "meios empregados evento a evento, e a lista oficial de organizações que compõem o "
    "sistema SAR (Capitanias, Delegacias e Agências). Aqui, **número de organizações** é "
    "usado como um proxy de presença institucional — não como uma contagem de pessoas ou "
    "de meios. Uma Capitania pode ter uma estrutura bem maior que uma Agência isolada, e "
    "essa diferença de porte não aparece na contagem."
)

oms = carregar_estrutura()
comparativo = montar_comparativo(incidentes, oms)

correlacao = comparativo["organizacoes"].corr(comparativo["eventos"])
maior = comparativo.iloc[0]
menor = comparativo.iloc[-1]

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Organizações militares",
    formatar_numero(len(oms)),
    help="Capitanias, Delegacias e Agências — as organizações de ponta do sistema SAR.",
)
col2.metric("Correlação nº de OMs x eventos", f"{correlacao:.2f}".replace(".", ","))
col3.metric(f"Mais eventos por OM — {maior['rotulo']}", f"{maior['eventos_por_om']:.1f}".replace(".", ","))
col4.metric(f"Menos eventos por OM — {menor['rotulo']}", f"{menor['eventos_por_om']:.1f}".replace(".", ","))

st.divider()

# --- Gráfico principal: eventos por organização ---------------------------
st.subheader("Eventos por organização, em cada Salvamar")
st.caption(
    "Sobreviventes, óbitos e desaparecidos à parte: aqui a pergunta é quantos eventos, em "
    "média, cada organização daquele Salvamar precisa atender. Quanto maior a barra, menos "
    "organizações existem para a quantidade de eventos da região."
)

ordem = list(comparativo["rotulo"])

grafico_razao = (
    alt.Chart(comparativo)
    .mark_bar(color=COR_RAZAO, cornerRadiusEnd=4, size=28)
    .encode(
        x=alt.X("rotulo:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("eventos_por_om:Q", title="Eventos por organização"),
        tooltip=[
            alt.Tooltip("rotulo:N", title="Salvamar"),
            alt.Tooltip("eventos:Q", title="Eventos no período"),
            alt.Tooltip("organizacoes:Q", title="Organizações subordinadas"),
            alt.Tooltip("eventos_por_om:Q", title="Eventos por organização", format=".1f"),
        ],
    )
    .properties(height=280)
)
mostrar_grafico(grafico_razao)

# --- Os dois ingredientes, lado a lado ------------------------------------
st.subheader("Os dois números por trás da razão")
st.caption(
    "À esquerda, quantas organizações militares existem em cada Salvamar — isso não muda "
    "com os filtros, porque é uma característica fixa da estrutura. À direita, quantos "
    "eventos cada Salvamar atendeu no recorte escolhido."
)

esquerda, direita = st.columns(2)
with esquerda:
    grafico_oms = (
        alt.Chart(comparativo)
        .mark_bar(color=COR_ESTRUTURA, cornerRadiusEnd=4, size=22)
        .encode(
            x=alt.X("rotulo:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=-40)),
            y=alt.Y("organizacoes:Q", title="Organizações"),
            tooltip=[alt.Tooltip("rotulo:N", title="Salvamar"), alt.Tooltip("organizacoes:Q", title="Organizações")],
        )
        .properties(height=260, title="Organizações subordinadas")
    )
    mostrar_grafico(grafico_oms)

with direita:
    grafico_eventos = (
        alt.Chart(comparativo)
        .mark_bar(color=COR_ESTRUTURA, cornerRadiusEnd=4, size=22)
        .encode(
            x=alt.X("rotulo:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=-40)),
            y=alt.Y("eventos:Q", title="Eventos"),
            tooltip=[alt.Tooltip("rotulo:N", title="Salvamar"), alt.Tooltip("eventos:Q", title="Eventos")],
        )
        .properties(height=260, title="Eventos no período filtrado")
    )
    mostrar_grafico(grafico_eventos)

st.divider()

# --- Detalhe por organização -----------------------------------------------
st.subheader("Organizações de cada Salvamar")

salvamar_escolhido = st.selectbox(
    "Ver as organizações de", ["Todos os Salvamares"] + ordem
)

contagem_eventos = eventos_por_om(incidentes)
tabela_oms = oms.copy()
tabela_oms["rotulo"] = tabela_oms["salvamar"].str.replace("SALVAMAR ", "", regex=False).str.title()
tabela_oms["eventos"] = tabela_oms["organizacao"].map(contagem_eventos).fillna(0).astype(int)

if salvamar_escolhido != "Todos os Salvamares":
    tabela_oms = tabela_oms[tabela_oms["rotulo"] == salvamar_escolhido]

tabela_oms = tabela_oms.sort_values("eventos", ascending=False).rename(columns={
    "organizacao": "Organização",
    "tipo_om": "Tipo",
    "rotulo": "Salvamar",
    "localizacao": "Localização",
    "eventos": "Eventos no período filtrado",
})
st.dataframe(
    tabela_oms[["Organização", "Tipo", "Salvamar", "Localização", "Eventos no período filtrado"]],
    hide_index=True,
    width="stretch",
)

st.caption(
    f"{formatar_numero(len(oms))} organizações ao todo: "
    f"{formatar_numero(int((oms['tipo_om'] == 'Capitania').sum()))} Capitanias, "
    f"{formatar_numero(int((oms['tipo_om'] == 'Delegacia').sum()))} Delegacias e "
    f"{formatar_numero(int((oms['tipo_om'] == 'Agência').sum()))} Agências."
)

st.info(
    "**Para observar.** A correlação entre número de organizações e número de eventos é "
    "moderada, não forte — a estrutura acompanha a demanda só em parte. O Norte tem a maior "
    "razão de eventos por organização: relativamente poucas OMs para o volume de eventos "
    "da região. O Oeste tem a menor razão: mais organizações, proporcionalmente, para "
    "menos eventos. Isso não significa que uma região está mal atendida e a outra bem — só "
    "que a divisão de organizações não segue de perto onde os eventos se concentram, "
    "medida por essa contagem."
)
