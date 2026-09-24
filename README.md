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

## Estrutura

```
.
├── app.py              # painel Streamlit com o mapa dos incidentes
├── requirements.txt    # dependências do projeto
└── dados/
    └── SAR_2021-2025_consolidado.xlsx   # base consolidada dos eventos SAR
```
