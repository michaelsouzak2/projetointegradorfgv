"""
Prepara os arquivos das áreas dos Distritos Navais para uso no mapa.

Os arquivos originais são muito detalhados (13 casas decimais e milhares de
pontos por área), o que deixaria o mapa lento. Este script reduz o detalhe
sem mudar o desenho das áreas na escala em que o mapa é usado.

Execute apenas quando os arquivos originais mudarem:
    python preparar_areas.py
"""

import json
from pathlib import Path

PASTA_ORIGINAIS = Path(__file__).parent / "dados" / "areas_originais"
PASTA_SAIDA = Path(__file__).parent / "dados" / "areas"

# Distância mínima, em graus, entre a linha simplificada e a original.
# 0,005 grau equivale a cerca de 550 metros, detalhe suficiente para um mapa
# que mostra todo o Brasil.
TOLERANCIA = 0.005

# Casas decimais mantidas nas coordenadas. Quatro casas equivalem a cerca de
# 11 metros.
CASAS_DECIMAIS = 4


def distancia_ate_reta(ponto, inicio, fim):
    """Distância de um ponto até a reta que liga os pontos inicio e fim."""
    (x, y), (x1, y1), (x2, y2) = ponto, inicio, fim

    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:  # início e fim são o mesmo ponto
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5

    # Área do paralelogramo dividida pelo comprimento da base.
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / (dx**2 + dy**2) ** 0.5


def simplificar(pontos, tolerancia):
    """
    Reduz a quantidade de pontos de uma linha pelo algoritmo de
    Ramer-Douglas-Peucker: mantém o ponto mais distante da reta que liga as
    duas pontas e repete a verificação nos dois trechos resultantes.
    """
    if len(pontos) <= 2:
        return pontos

    # Ponto mais distante da reta que liga a primeira à última posição.
    distancias = [distancia_ate_reta(p, pontos[0], pontos[-1]) for p in pontos[1:-1]]
    maior_distancia = max(distancias)
    indice = distancias.index(maior_distancia) + 1

    if maior_distancia <= tolerancia:
        return [pontos[0], pontos[-1]]  # o trecho todo vira uma reta

    trecho_inicial = simplificar(pontos[: indice + 1], tolerancia)
    trecho_final = simplificar(pontos[indice:], tolerancia)
    return trecho_inicial[:-1] + trecho_final  # o ponto do meio não se repete


def simplificar_anel(anel, tolerancia):
    """Simplifica um contorno fechado, garantindo que ele continue fechado."""
    anel = simplificar(anel, tolerancia)

    # Um polígono precisa de ao menos 4 posições, com a última igual à primeira.
    if len(anel) < 4:
        return None

    anel[-1] = anel[0]
    return [[round(x, CASAS_DECIMAIS), round(y, CASAS_DECIMAIS)] for x, y in anel]


def simplificar_multipoligono(poligonos, tolerancia):
    """Simplifica todos os contornos de um MultiPolygon."""
    resultado = []
    for poligono in poligonos:
        aneis = [simplificar_anel(anel, tolerancia) for anel in poligono]
        aneis = [anel for anel in aneis if anel]  # descarta os que ficaram pequenos demais
        if aneis:
            resultado.append(aneis)
    return resultado


def contar_pontos(poligonos):
    return sum(len(anel) for poligono in poligonos for anel in poligono)


def main():
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(PASTA_ORIGINAIS.glob("*.json"))

    if not arquivos:
        print(f"Nenhum arquivo encontrado em {PASTA_ORIGINAIS}")
        return

    for arquivo in arquivos:
        geojson = json.loads(arquivo.read_text(encoding="utf-8"))

        for feicao in geojson["features"]:
            geometria = feicao["geometry"]

            # Alguns arquivos vêm como Polygon e outros como MultiPolygon.
            # Aqui todos viram MultiPolygon, para o mapa tratar um formato só.
            if geometria["type"] == "Polygon":
                geometria["type"] = "MultiPolygon"
                geometria["coordinates"] = [geometria["coordinates"]]
            elif geometria["type"] != "MultiPolygon":
                raise ValueError(f"{arquivo.name}: geometria {geometria['type']} não é aceita")

            antes = contar_pontos(geometria["coordinates"])
            geometria["coordinates"] = simplificar_multipoligono(geometria["coordinates"], TOLERANCIA)
            depois = contar_pontos(geometria["coordinates"])

        saida = PASTA_SAIDA / arquivo.name
        saida.write_text(json.dumps(geojson, separators=(",", ":")), encoding="utf-8")

        tamanho_antes = arquivo.stat().st_size / 1024
        tamanho_depois = saida.stat().st_size / 1024
        print(
            f"{arquivo.name}: {antes} -> {depois} pontos | "
            f"{tamanho_antes:.0f} KB -> {tamanho_depois:.0f} KB"
        )


if __name__ == "__main__":
    main()
