# Calculo dos indicadores - estrutura (quebra semanal)

Documento de desenho, antes de escrever o codigo. Registra o que a
planilha `Logica_Score_Card.xlsx` faz hoje em Excel, as regras
confirmadas e como isso vira codigo no ScoreCard.

## 1. O que a planilha faz hoje

A entrada e o mesmo relatorio que o app ja extrai
(`rptLMUserSummaryRaw`, o "Summary"), com:

- **Medium Level Group** (coluna A) = a semana, vindo como a data de
  inicio (30/08/2026, 06/09/2026, 13/09/2026...)
- **Detail Level Group** (coluna B) = o User ID

**As colunas A ate S sao o export cru. De T pra frente sao formulas
montadas a mao** — e essa parte que o app passa a fazer.

### 1.1 Classificacao por pessoa (coluna T, "Dispersao")

```
se Goal = 0  ou  Measured Direct = 0   -> linha ignorada (" ")
senao se Var > 10 ou Var < -10          -> "FORA"
senao                                   -> "DENTRO"
```

`Var` ja vem calculado pelo relatorio (coluna C), em pontos
percentuais. A tolerancia e +/- 10.

Quem cai na primeira regra sai **apenas da dispersao**: continua
entrando normalmente nas somas dos outros indicadores.

### 1.2 Indicadores por semana (bloco W:Y, uma coluna por semana)

| Indicador | Formula (em cima das colunas do relatorio) |
|---|---|
| tempo meta | soma de `Goal` |
| tempo logado | soma de `Measured Direct` |
| **EFETIVIDADE** | tempo meta / tempo logado |
| **HORA DIRETA** | (`Measured Direct` + `Unmeasured Signon Direct` + `Unmeasured Insert Direct`) / (`Total` - `PD Brk`) — todas somadas na semana |
| Dentro | quantidade de pessoas classificadas "DENTRO" |
| Fora | quantidade de pessoas classificadas "FORA" |
| **DISPERSAO** | Dentro / (Dentro + Fora) |

Nenhuma outra coluna do relatorio e usada: `Units Per Hour`,
`Unmeasured Pct` e `Indirect Pct` ficam de fora.

### 1.3 Conferencia

Reproduzi as formulas fora do Excel e bate exatamente com os valores
salvos na planilha (semana 36):

| | planilha | recalculado |
|---|---|---|
| tempo meta | 245,99 | 245,99 |
| tempo logado | 255,23 | 255,23 |
| EFETIVIDADE | 96,38% | 96,38% |
| HORA DIRETA | 85,37% | 85,37% |
| DISPERSAO | 81,82% (9 / 11) | 81,82% |

Esses numeros entram como **caso de referencia nos testes**: o app so
esta certo se reproduzir a planilha.

## 2. Semana: como identificar

A semana **comeca no domingo** — e a data que vem no "Medium Level
Group". O numero da semana serve so de rotulo (Week 36, Week 37...) e
nao entra em nenhum calculo. Para bater com o `WEEKNUM` do Excel
(domingo como primeiro dia):

```
dow_jan1 = dia da semana de 1/jan com domingo = 0
doy      = dia do ano da data
week     = (doy - 1 + dow_jan1) // 7 + 1
```

Conferido: 30/08/2026 -> 36, 06/09/2026 -> 37, 13/09/2026 -> 38, como
na planilha.

O atalho "Semana passada" da tela ja foi ajustado de segunda-domingo
para **domingo-sabado**, pra extrair exatamente a mesma janela que o
relatorio fecha. O domingo normalmente vem zerado (nao ha operacao),
o que nao afeta nenhum indicador.

## 3. Metas e cores

Iguais para as 12 operacoes:

| Indicador | Verde | Vermelho | Azul |
|---|---|---|---|
| EFETIVIDADE | 90% a 110% | abaixo de 90% | acima de 110% |
| HORA DIRETA | 85% ou mais | abaixo de 85% | — |
| DISPERSAO | 70% ou mais | abaixo de 70% | — |

O azul da efetividade acima de 110% e o caso que aparece na propria
amostra: a semana 37 fecha em 112,9%, puxada por uma pessoa com `Var`
de 128.

## 4. Estrutura proposta no codigo

Quatro camadas, cada uma com uma responsabilidade. A parte que calcula
nao sabe de arquivo nem de tela — e a parte que precisa ser testada
valor por valor.

```
indicators/
  reader.py    le o .xlsx baixado -> lista de linhas (dicts)
  weekly.py    funcoes puras: classifica a linha, calcula a semana
  limits.py    tolerancia (+/- 10) e as faixas de cor da secao 3
indicators_store.py   guarda o resultado por operacao + semana
api.py                calcula depois da extracao e entrega pra tela
ui/ (aba Inicio)      mostra os cards e a tabela
```

**`indicators/reader.py`** — abre o `.xlsx` e devolve as linhas com os
nomes de coluna normalizados (minusculo, sem acento, sem quebra de
linha: `measured direct`, `pd brk`...). O mapeamento e **pelo texto do
cabecalho, nunca pela letra da coluna** — o "Group By 1" e escolhido na
tela, entao o conteudo das colunas de agrupamento muda de uma extracao
pra outra. Linha sem data de semana ou com valor nao numerico nas
colunas de calculo e descartada, o que tambem protege de eventual linha
de total no fim do arquivo.

**`indicators/weekly.py`** — nenhum I/O, so calculo:

```
classify_row(linha, tolerancia=10) -> "dentro" | "fora" | None
weekly_indicators(linhas) -> {tempo_meta, tempo_logado, efetividade,
                              hora_direta, dentro, fora, dispersao}
```

**`indicators_store.py`** — mesmo padrao do `history_store.py`, em
`%APPDATA%\ScoreCard\indicators.json`, com o resultado gravado por
operacao + semana. E daqui que sai a comparacao entre semanas.

**`api.py`** — depois de cada extracao bem-sucedida, calcula e grava.
Expoe `get_indicators(operacao, periodo)` pra aba Inicio.

## 5. Por que guardar o resultado, e nao recalcular do arquivo

A extracao apaga o arquivo anterior da mesma operacao (pedido de
proposito, pra pasta nao acumular lixo). Se o indicador fosse calculado
lendo os arquivos da pasta, o historico das semanas anteriores
desapareceria junto. Calculando na hora da extracao e gravando o
resultado, a pasta continua com um arquivo so e a evolucao semana a
semana fica preservada.

Limite conhecido: o `indicators.json` e por maquina. Se duas pessoas
extraem a mesma operacao, cada uma ve o seu historico. Se isso virar
problema, o passo seguinte e gravar tambem um arquivo acumulado na
pasta da operacao no SharePoint.

## 6. Sobre o mensal

EFETIVIDADE e HORA DIRETA sao razoes de somas, **nao medias das
semanas**. O mes nao pode ser a media dos indicadores semanais — tem
que ser recalculado somando as colunas do periodo inteiro. O mesmo
codigo de `weekly.py` serve, mudando so o conjunto de linhas de
entrada; e por isso que a separacao Week/Month das pastas importa.

## 7. Ordem de implementacao

1. `indicators/weekly.py` + `limits.py`, com os testes usando os
   numeros da secao 1.3 como referencia.
2. `indicators/reader.py`, validado contra um export real.
3. `indicators_store.py` e a gravacao dentro do `api.py`.
4. Aba Inicio: cards com as cores da secao 3, tabela de semanas e
   detalhe por pessoa com DENTRO/FORA.
