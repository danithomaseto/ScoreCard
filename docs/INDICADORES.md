# Calculo dos indicadores - estrutura (quebra semanal)

Documento de desenho, antes de escrever codigo. Registra o que a
planilha `Logica_Score_Card.xlsx` faz hoje em Excel, como isso vira
codigo no ScoreCard e quais decisoes ainda estao abertas.

## 1. O que a planilha faz hoje

A entrada e o mesmo relatorio que o app ja extrai (`rptLMUserSummaryRaw`,
o "Summary"), com:

- **Medium Level Group** (coluna A) = a semana (vem como a data de
  inicio da semana: 30/08/2026, 06/09/2026, 13/09/2026...)
- **Detail Level Group** (coluna B) = o User ID

As colunas A ate S sao o export cru. As colunas T, U e o bloco W:Y sao
a logica montada a mao.

### 1.1 Classificacao por pessoa (coluna T, "Dispersao")

```
se Goal = 0  ou  Measured Direct = 0   -> linha ignorada (" ")
senao se Var > 10 ou Var < -10          -> "FORA"
senao                                   -> "DENTRO"
```

`Var` ja vem calculado pelo relatorio (coluna C), em pontos percentuais.
A tolerancia e +/- 10.

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

A soma na semana e feita com `SUMIF` sobre a coluna U, que e
`WEEKNUM(data)`.

### 1.3 Conferencia

Reproduzi as formulas fora do Excel e bate exatamente com os valores
que estao salvos na planilha (semana 36):

| | planilha | recalculado |
|---|---|---|
| tempo meta | 245,99 | 245,99 |
| tempo logado | 255,23 | 255,23 |
| EFETIVIDADE | 96,38% | 96,38% |
| HORA DIRETA | 85,37% | 85,37% |
| DISPERSAO | 81,82% (9 / 11) | 81,82% |

Esses numeros entram como **caso de referencia nos testes**: o app so
esta certo se reproduzir a planilha.

## 2. Estrutura proposta no codigo

Quatro camadas, cada uma com uma responsabilidade. A ideia e que a
parte que calcula nao saiba de arquivo nem de tela, porque e a parte
que precisa ser testada numero por numero.

```
indicators/
  reader.py    le o .xlsx baixado -> lista de linhas (dicts)
  weekly.py    funcoes puras: classifica linha, calcula a semana
indicators_store.py   guarda o resultado por operacao + semana
api.py                calcula depois da extracao e entrega pra tela
ui/ (aba Inicio)      mostra os cards e a tabela
```

**`indicators/reader.py`** — abre o arquivo e devolve as linhas com os
nomes de coluna normalizados (minusculo, sem acento, sem quebra de
linha: `measured direct`, `pd brk`...). O mapeamento e **pelo texto do
cabecalho, nunca pela letra da coluna** — o "Group By 1" e escolhido na
tela, entao o conteudo das colunas de agrupamento muda de uma extracao
pra outra.

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

## 3. Por que guardar o resultado, e nao recalcular do arquivo

A extracao apaga o arquivo anterior da mesma operacao (pedido de
proposito, pra pasta nao acumular lixo). Se o indicador fosse calculado
lendo os arquivos da pasta, o historico de semanas anteriores
desapareceria junto. Calculando na hora da extracao e gravando o
resultado, a pasta continua com um arquivo so e a evolucao semana a
semana fica preservada.

Limite conhecido: o `indicators.json` e por maquina. Se duas pessoas
extraem a mesma operacao, cada uma ve o seu historico. Se isso virar
problema, o passo seguinte e gravar tambem um arquivo acumulado na
pasta da operacao no SharePoint.

## 4. Sobre o mensal

EFETIVIDADE e HORA DIRETA sao razoes de somas, **nao medias das
semanas**. O mes nao pode ser a media dos quatro indicadores semanais —
tem que ser recalculado somando as colunas do periodo inteiro. O mesmo
codigo de `weekly.py` serve, mudando so o conjunto de linhas de
entrada; e por isso que a separacao Week/Month das pastas importa.

## 5. Decisoes abertas

1. **Em que dia comeca a semana?** A planilha usa `WEEKNUM`, que no
   Excel comeca a semana no **domingo** (30/08/2026 e domingo = semana
   36). Os atalhos de data do app hoje usam **segunda a domingo**. As
   duas convencoes nao coincidem — se o Summary fecha a semana no
   domingo, o atalho "Semana passada" esta pegando uma janela
   desalinhada. Proposta: usar como chave a propria data que vem no
   "Medium Level Group" e ajustar o atalho pra domingo-sabado.
2. **Um export real do relatorio.** Precisa pra confirmar tres coisas:
   se o arquivo baixado e `.xlsx` de verdade (define a biblioteca de
   leitura), se existe linha de total/subtotal no final (se existir e
   nao for descartada, tudo dobra) e se ha cabecalho antes da linha das
   colunas.
3. **Pessoa sem medicao.** Quem tem `Goal = 0` fica fora da dispersao,
   mas continua entrando na HORA DIRETA atraves de `Total` e `PD Brk`.
   Na amostra nao muda nada (o `Total` tambem e 0), mas alguem logado
   so em tempo indireto derrubaria o indicador. Confirmar se e isso que
   se espera.
4. **Tolerancia e metas.** O +/- 10 e igual pras 12 operacoes ou muda
   por cliente? E quais sao as metas de EFETIVIDADE, HORA DIRETA e
   DISPERSAO, pra tela poder pintar verde/vermelho?
5. **Indicadores extras.** O relatorio ja traz `Units Per Hour`,
   `Unmeasured Pct` e `Indirect Pct` prontos, que hoje nao sao usados.
   Entram no Score Card ou ficam de fora?
