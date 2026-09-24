# Padrões de ocorrências SAR e situação das pessoas envolvidas

Projeto Integrador I do MBA em IA e Ciência de Dados para Transformação Digital na Defesa (FGV/EMAP), Grupo IV.

Painel analítico sobre os eventos de Busca e Salvamento (SAR) registrados pelo SALVAMAR BRASIL de 2021 a 2025. O painel busca responder onde, quando e em que tipos de ocorrência se concentram os eventos com óbitos e desaparecidos.

## Mapa dos incidentes

O arquivo `app.py` mostra, sobre o OpenStreetMap, a posição de cada um dos 1.391 incidentes SAR. O menu lateral filtra os incidentes por:

- **Ano**
- **Salvamar** (em ordem de Distrito Naval)
- **Tipo de incidente** (as 9 categorias do ANEMAR)
- **Pessoas envolvidas**: com óbitos, com desaparecidos e com sobreviventes. Quando mais de uma opção é marcada, o mapa mostra os incidentes que atendem a pelo menos uma delas.

Um filtro vazio não restringe nada. A cor de cada círculo indica a situação das pessoas envolvidas:

| Cor | Significado |
|---|---|
| Vermelho | ao menos um óbito ou desaparecido |
| Azul | somente sobreviventes |
| Cinza | sem registro de pessoas (nenhum sobrevivente, óbito ou desaparecido registrado) |

Passe o mouse sobre um círculo para ver o identificador e o tipo do incidente. Clique para ver os detalhes.

## Áreas dos Distritos Navais

No canto superior direito do mapa há um menu com as áreas de jurisdição dos Distritos Navais, que correspondem às áreas dos Salvamares regionais. Cada área pode ser ligada e desligada sozinha, e a caixa **"Áreas dos Distritos Navais"**, no topo do menu, liga e desliga todas de uma vez.

São nove áreas, do 1º ao 9º Distrito Naval, cobrindo toda a região de busca e salvamento sob responsabilidade brasileira. O rótulo de cada uma junta o número do Distrito ao nome do Salvamar, e passando o mouse sobre a área esse nome aparece.

As áreas usam **quatro cores para as nove áreas**. Nove tons bem diferentes entre si não existem: alguns ficariam parecidos demais, inclusive para quem tem daltonismo. Como no mapa o que importa é enxergar onde uma área termina e a outra começa, basta que Distritos vizinhos tenham cores diferentes, e as cores foram distribuídas assim. Distritos que dividem a mesma cor ficam longe um do outro, como o 1º, no Rio de Janeiro, e o 9º, em Manaus.

Os tons também evitam o vermelho e o azul dos incidentes, para que a área não seja confundida com a situação das pessoas, e o preenchimento é bem claro, de modo que os incidentes continuem em primeiro plano.

## Aparência

O arquivo `.streamlit/config.toml` deixa o painel **sempre no modo escuro**, sem seguir a preferência do navegador de quem abre a página, e esconde o menu do canto superior direito. Sem esse menu, some também a opção de trocar o tema, e o modo escuro fica travado.

O mapa em si continua claro, porque usa os blocos do OpenStreetMap.

## Como executar

1. Instale o Python 3.10 ou superior.
2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Inicie o painel:

   ```bash
   streamlit run app.py
   ```

O mapa precisa de acesso à internet para carregar os blocos do OpenStreetMap e a biblioteca Leaflet.

## Dados

O painel lê a aba **Base de dados** da planilha `dados/SAR_2021-2025_consolidado.xlsx`, com um evento SAR por linha. As medidas de pessoas seguem a aba "SOBREVIVENTES, DESAPAR., ÓBITOS" da própria planilha:

| Medida | Colunas da planilha |
|---|---|
| Sobreviventes | `VIDAS SALVAS MB` + `VIDAS SALVAS EXTRA-MB` + `SOBREVIVENTES SEM RESGATE` |
| Óbitos | `ÓBITOS` |
| Desaparecidos | `VIDAS AINDA DESAPARECIDAS` |

Observações:

- A coluna `SOBREVIVENTES` da base só está preenchida em 2024 e 2025, por isso ela não é usada. A soma acima reproduz os totais da aba de resumo (3.202 sobreviventes de 2021 a 2025).
- Células vazias nas colunas de pessoas são tratadas como zero. A coluna `SOBREVIVENTES SEM RESGATE` só é registrada desde 2023, então fica vazia em 2021 e 2022. Nas demais colunas de pessoas, há células vazias em 4 eventos.
- A posição vem das colunas `LATITUDE (GD)` e `LONGITUDE (GD)`. Os 3 eventos com posição aproximada trazem essa informação no detalhe do incidente.
- O tipo de incidente usa a coluna padronizada `TIPO INCIDENTE (ANEMAR)`.

### Áreas dos Distritos Navais

As áreas vêm em arquivos GeoJSON, um por Distrito Naval, em SIRGAS 2000 (EPSG:4674). Para acrescentar ou atualizar uma área, basta colocar o arquivo em `dados/areas_originais/` e rodar o script de preparação: o mapa passa a mostrar a área sozinho, sem mexer no código. O número do Distrito é lido do campo `id_dn`, porque a sigla varia de arquivo para arquivo (`1° DN`, `6º DN`, `9º`). Arquivos no formato `Polygon` ou `MultiPolygon` são aceitos.

Os arquivos originais são muito detalhados para um mapa de todo o Brasil: são 13 casas decimais e até 91 mil pontos por área, somando 15 MB. O script `preparar_areas.py` reduz esse detalhe e grava o resultado em `dados/areas/`:

```bash
python preparar_areas.py
```

A simplificação usa o algoritmo de Ramer-Douglas-Peucker, com tolerância de 0,005 grau (cerca de 550 metros), e arredonda as coordenadas para 4 casas decimais (cerca de 11 metros). O conjunto cai de 15 MB para 296 KB, sem mudança visível na escala em que o mapa é usado. O app lê apenas a pasta `dados/areas/`, então não é preciso rodar o script de novo para usar o painel.

O nome do Salvamar que aparece no rótulo vem da própria planilha. Assim o mapa usa as mesmas palavras do filtro lateral.

## Estrutura

```
.
├── app.py                  # painel Streamlit com o mapa dos incidentes
├── preparar_areas.py       # simplifica os arquivos das áreas dos Distritos Navais
├── requirements.txt        # dependências do projeto
├── .streamlit/
│   └── config.toml         # modo escuro e menu do canto superior direito
└── dados/
    ├── SAR_2021-2025_consolidado.xlsx   # base consolidada dos eventos SAR
    ├── areas_originais/                 # áreas dos Distritos como recebidas
    └── areas/                           # áreas simplificadas, usadas pelo mapa
```
