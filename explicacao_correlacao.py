"""
Como calculamos a correlação entre organizações e eventos
============================================================

A página "Estrutura x demanda" do painel mostra uma correlação de 0,52
entre o número de organizações militares (OMs) de cada Salvamar e o
número de eventos que ele atende. Este script explica, passo a passo, o
que esse número significa e como ele é calculado — sem "caixa-preta".

O script tem quatro partes:
    1. Os dados: 9 pares de números, um por Distrito Naval.
    2. O cálculo manual, com cada etapa mostrada.
    3. A conferência com pandas e com scipy (o mesmo resultado, calculado
       pela biblioteca em vez de na mão).
    4. Um gráfico de dispersão, para ver o que o número representa.

Executar:
    python explicacao_correlacao.py

Precisa de: pandas, matplotlib (para o gráfico) e, se quiser o valor-p,
scipy. Sem scipy o script funciona normalmente, só pula essa parte.
"""

from pathlib import Path

import pandas as pd

ARQUIVO_DADOS = Path(__file__).parent / "dados" / "SAR_2021-2025_consolidado.xlsx"


# =============================================================================
# PARTE 1 — A teoria, em poucas palavras
# =============================================================================
#
# O coeficiente de correlação de Pearson (r) mede o quanto duas variáveis
# numéricas caminham juntas de forma LINEAR: quando uma cresce, a outra
# tende a crescer (ou a diminuir) na mesma proporção?
#
# r varia sempre entre -1 e +1:
#
#   r = +1   correlação positiva perfeita — os pontos formam uma reta subindo
#   r =  0   nenhuma relação linear — os pontos formam uma nuvem sem direção
#   r = -1   correlação negativa perfeita — os pontos formam uma reta descendo
#
# Não existe uma régua oficial para "forte" ou "fraco", mas uma referência
# comum em ciências sociais e aplicadas é:
#
#   |r| até 0,3    fraca
#   |r| de 0,3 a 0,7   moderada
#   |r| acima de 0,7   forte
#
# A FÓRMULA
# ---------
# Para duas listas de números x (organizações) e y (eventos), com médias
# x̄ e ȳ:
#
#            soma[ (xi - x̄) * (yi - ȳ) ]
#   r = -----------------------------------------
#        raiz( soma[(xi-x̄)²] * soma[(yi-ȳ)²] )
#
# Em palavras: para cada Distrito, medimos o quanto ele se afasta da média
# em organizações (xi - x̄) e o quanto se afasta da média em eventos
# (yi - ȳ). Multiplicamos as duas distâncias.
#
#   - Se um Distrito tem MAIS organizações que a média E MAIS eventos que
#     a média, as duas distâncias são positivas, e o produto é positivo.
#   - Se tem MENOS organizações E MENOS eventos, as duas distâncias são
#     negativas, e o produto AINDA é positivo (negativo vezes negativo).
#   - Se um dos dois está acima da média e o outro abaixo, o produto é
#     negativo.
#
# Somando os produtos dos 9 Distritos, descobrimos se eles tendem a variar
# juntos (soma positiva) ou em direções opostas (soma negativa). O
# denominador só reajusta essa soma para caber entre -1 e +1, usando a
# variabilidade de cada variável isoladamente.
#
# LIMITAÇÕES IMPORTANTES
# -----------------------
# 1. Só mede relação LINEAR. Duas variáveis podem ter uma relação forte e
#    r ficar perto de 0, se essa relação não for uma reta (por exemplo, em
#    forma de U).
# 2. É sensível a valores fora da curva. Com só 9 pontos — um por Distrito
#    Naval —, um único Distrito atípico pode mudar bastante o resultado.
# 3. Correlação não é causa. Mesmo um r alto não provaria que mais eventos
#    fazem existir mais organizações, nem o contrário. Pode haver outros
#    fatores por trás dos dois (o tamanho da área, por exemplo).
# 4. Amostra pequena. Com 9 pontos, o valor de r tem pouca precisão
#    estatística — veja a Parte 3, sobre o valor-p.


# =============================================================================
# PARTE 2 — Os dados
# =============================================================================

def carregar_dados():
    """
    Devolve, para cada um dos 9 Distritos Navais: o número de organizações
    subordinadas (Capitanias, Delegacias e Agências) e o número de eventos
    SAR que o Distrito atendeu de 2021 a 2025. É a mesma conta feita na
    página "Estrutura x demanda" do painel, sem filtro nenhum.
    """
    estrutura = pd.read_excel(ARQUIVO_DADOS, sheet_name="ESTRUTURA SAR")
    estrutura["numero_distrito"] = estrutura["DISTRITO NAVAL"].astype(str).str.extract(r"(\d+)").astype(float)
    oms = estrutura[estrutura["NÍVEL"].isin([3, 4])]  # só Capitania, Delegacia, Agência
    organizacoes = oms.groupby("numero_distrito").size()

    base = pd.read_excel(ARQUIVO_DADOS, sheet_name="Base de dados")
    base["numero_distrito"] = base["DISTRITO NAVAL"].astype(str).str.extract(r"(\d+)").astype(float)
    eventos = base.groupby("numero_distrito").size()
    salvamar = base.groupby("numero_distrito")["SALVAMAR"].first()

    dados = pd.DataFrame({"salvamar": salvamar, "organizacoes": organizacoes, "eventos": eventos})
    dados["salvamar"] = dados["salvamar"].str.replace("SALVAMAR ", "", regex=False).str.title()
    return dados.sort_index().reset_index(drop=True)


# =============================================================================
# PARTE 3 — O cálculo, passo a passo
# =============================================================================

def calcular_pearson_manual(x, y):
    """
    Calcula r "na mão", pela fórmula, devolvendo também as contas
    intermediárias — para conseguirmos mostrar cada etapa.
    """
    n = len(x)
    media_x = sum(x) / n
    media_y = sum(y) / n

    desvios_x = [xi - media_x for xi in x]
    desvios_y = [yi - media_y for yi in y]
    produtos = [dx * dy for dx, dy in zip(desvios_x, desvios_y)]

    soma_produtos = sum(produtos)
    soma_quadrados_x = sum(dx ** 2 for dx in desvios_x)
    soma_quadrados_y = sum(dy ** 2 for dy in desvios_y)

    r = soma_produtos / (soma_quadrados_x * soma_quadrados_y) ** 0.5

    return {
        "n": n, "media_x": media_x, "media_y": media_y,
        "desvios_x": desvios_x, "desvios_y": desvios_y, "produtos": produtos,
        "soma_produtos": soma_produtos,
        "soma_quadrados_x": soma_quadrados_x, "soma_quadrados_y": soma_quadrados_y,
        "r": r,
    }


def mostrar_tabela_do_calculo(dados, resultado):
    """Imprime, linha a linha, a conta que cada Distrito contribui para o r final."""
    print(
        f"{'Salvamar':<14}{'OMs (x)':>9}{'Eventos (y)':>13}"
        f"{'x - x̄':>10}{'y - ȳ':>10}{'produto':>12}"
    )
    print("-" * 68)
    linhas = zip(dados["salvamar"], dados["organizacoes"], dados["eventos"],
                 resultado["desvios_x"], resultado["desvios_y"], resultado["produtos"])
    for salvamar, x, y, dx, dy, produto in linhas:
        print(f"{salvamar:<14}{x:>9}{y:>13}{dx:>10.1f}{dy:>10.1f}{produto:>12.1f}")
    print("-" * 68)
    print(
        f"{'Soma':<14}{'':>9}{'':>13}{'':>10}{'':>10}{resultado['soma_produtos']:>12.1f}"
        "   ← numerador da fórmula"
    )


def interpretar(r):
    """Classifica a força da correlação pela referência usada no texto acima."""
    forca = "forte" if abs(r) > 0.7 else "moderada" if abs(r) > 0.3 else "fraca"
    direcao = "positiva" if r > 0 else "negativa" if r < 0 else "nula"
    return f"{forca} e {direcao}" if r != 0 else "nula"


# =============================================================================
# Programa principal
# =============================================================================

def main():
    dados = carregar_dados()
    x = dados["organizacoes"].tolist()
    y = dados["eventos"].tolist()

    print("=" * 68)
    print("OS DADOS: organizações e eventos, um par por Distrito Naval")
    print("=" * 68)
    print(dados.rename(columns={
        "salvamar": "Salvamar", "organizacoes": "Organizações", "eventos": "Eventos",
    }).to_string(index=False))

    print()
    print("=" * 68)
    print("O CÁLCULO, PASSO A PASSO")
    print("=" * 68)
    resultado = calcular_pearson_manual(x, y)
    print(f"Média de organizações (x̄): {resultado['media_x']:.2f}")
    print(f"Média de eventos (ȳ): {resultado['media_y']:.2f}")
    print()
    mostrar_tabela_do_calculo(dados, resultado)
    print()
    print(f"Soma dos quadrados dos desvios de x: {resultado['soma_quadrados_x']:.1f}  ← denominador, parte 1")
    print(f"Soma dos quadrados dos desvios de y: {resultado['soma_quadrados_y']:.1f}  ← denominador, parte 2")
    print()
    r_manual = resultado["r"]
    print(f"r = {resultado['soma_produtos']:.1f} / raiz({resultado['soma_quadrados_x']:.1f} × {resultado['soma_quadrados_y']:.1f})")
    print(f"r = {r_manual:.4f}")

    print()
    print("=" * 68)
    print("CONFERINDO COM AS BIBLIOTECAS")
    print("=" * 68)
    r_pandas = pd.Series(x).corr(pd.Series(y))  # method="pearson" é o padrão
    print(f"pandas  Series.corr()         → r = {r_pandas:.4f}")

    try:
        from scipy import stats
        r_scipy, p_valor = stats.pearsonr(x, y)
        print(f"scipy   stats.pearsonr()      → r = {r_scipy:.4f}, valor-p = {p_valor:.3f}")
        print()
        print(
            f"O valor-p ({p_valor:.3f}) é a chance de observar uma correlação tão forte "
            "quanto essa, ou mais, se na realidade não houvesse relação nenhuma entre "
            "as duas variáveis. Abaixo de 0,05 é a referência mais comum para dizer que "
            "o resultado 'provavelmente não é acaso' — mas, com só 9 Distritos, esse "
            "teste tem pouca força: é fácil não cruzar esse limite mesmo quando existe "
            "uma relação real. O valor-p aqui é só um complemento, não a palavra final."
        )
    except ImportError:
        print("(scipy não está instalado — pulando o valor-p. pip install scipy para vê-lo.)")

    print()
    print("=" * 68)
    print("O QUE O NÚMERO DIZ")
    print("=" * 68)
    print(
        f"r = {r_manual:.2f}: correlação {interpretar(r_manual)}. As duas variáveis "
        "tendem a crescer juntas, mas a relação está longe de ser exata — dá para ver "
        "isso no gráfico: os pontos sobem em geral, mas espalhados, não alinhados numa reta."
    )

    gerar_grafico(dados, resultado)


def gerar_grafico(dados, resultado):
    """
    Desenha o gráfico de dispersão: cada ponto é um Distrito Naval, o eixo x
    é o número de organizações e o eixo y é o número de eventos. A reta é o
    ajuste linear simples, construído com as mesmas somas já calculadas na
    Parte 3 — correlação e reta de tendência vêm da mesma conta.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib não está instalado — pulando o gráfico. pip install matplotlib.)")
        return

    inclinacao = resultado["soma_produtos"] / resultado["soma_quadrados_x"]
    intercepto = resultado["media_y"] - inclinacao * resultado["media_x"]

    fig, eixo = plt.subplots(figsize=(7, 5))
    eixo.scatter(dados["organizacoes"], dados["eventos"], color="#1baf7a", s=80, zorder=3)

    for _, linha in dados.iterrows():
        eixo.annotate(
            linha["salvamar"], (linha["organizacoes"], linha["eventos"]),
            textcoords="offset points", xytext=(6, 6), fontsize=9,
        )

    x_reta = [min(dados["organizacoes"]) - 0.5, max(dados["organizacoes"]) + 0.5]
    y_reta = [inclinacao * xi + intercepto for xi in x_reta]
    eixo.plot(x_reta, y_reta, color="#93a1b8", linestyle="--", zorder=2, label="reta de tendência")

    eixo.set_xlabel("Organizações militares (Capitanias, Delegacias, Agências)")
    eixo.set_ylabel("Eventos atendidos (2021–2025)")
    eixo.set_title(f"Organizações x eventos, por Salvamar  (r = {resultado['r']:.2f})")
    eixo.legend()
    fig.tight_layout()

    caminho = Path(__file__).parent / "correlacao_estrutura_demanda.png"
    fig.savefig(caminho, dpi=150)
    print(f"\nGráfico salvo em: {caminho}")


if __name__ == "__main__":
    main()
