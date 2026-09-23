# Indicadores - mapeamento antes do codigo

Documento de desenho. Registra o que a planilha `Logica_Score_Card.xlsx`
faz hoje em Excel, as regras confirmadas e como isso vira codigo no
ScoreCard. Nada aqui esta implementado ainda.

## 1. O que a planilha faz hoje

A entrada e o mesmo relatorio que o app ja extrai
(`rptLMUserSummaryRaw`, o "Summary"), com:

- **Medium Level Group** (coluna A) = a semana, vindo como a data de
  inicio (30/08/2026, 06/09/2026, 13/09/2026...)
- **Detail Level Group** (coluna B) = o User ID

Esse layout e o resultado de **Group By 1 = Week** e **Group By 2 =
User ID** no Summary (secao 8). Os titulos das colunas nao mudam com a
escolha: continuam "Medium Level Group" e "Detail Level Group", so o
conteudo muda. E por isso que o leitor se ancora nesses titulos.

**As colunas A ate S sao o export cru. De T pra frente sao formulas
montadas a mao** — e essa parte que o app passa a fazer.

### 1.1 Classificacao por linha (coluna T, "Dispersao")

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
| Dentro | linhas classificadas "DENTRO" |
| Fora | linhas classificadas "FORA" |
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

## 2. Granularidade: por semana, nunca por pessoa

O resultado guardado e **uma linha por semana**. O detalhe por pessoa
existe so dentro do calculo (pra contar DENTRO e FORA) e e descartado
depois — nao vai pra tela nem pro arquivo de resultados.

**Uma extracao pode conter varias semanas.** A propria planilha de
exemplo tem tres (36, 37 e 38) vindas de um unico export. Entao o
calculo nao e "um resultado por extracao", e "um resultado por semana
presente no arquivo": agrupa as linhas pela data do Medium Level Group
e calcula o conjunto de indicadores pra cada grupo.

## 3. Semana: como identificar

A semana **comeca no domingo** — e a data que vem no Medium Level
Group. O numero da semana serve so de rotulo (Week 36, Week 37...) e
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
relatorio fecha. O domingo normalmente vem zerado (nao ha operacao), o
que nao afeta nenhum indicador.

## 4. Metas e cores

Iguais para as 12 operacoes:

| Indicador | Verde | Vermelho | Azul |
|---|---|---|---|
| EFETIVIDADE | 90% a 110% | abaixo de 90% | acima de 110% |
| HORA DIRETA | 85% ou mais | abaixo de 85% | — |
| DISPERSAO | 70% ou mais | abaixo de 70% | — |

O azul da efetividade acima de 110% aparece na propria amostra: a
semana 37 fecha em 112,9%, puxada por uma pessoa com `Var` de 128.

## 5. O que fica guardado

Calculado na hora da extracao e gravado em
`%APPDATA%\ScoreCard\indicators.json`, indexado por **operacao ->
periodo -> semana**:

```json
{
  "hugo_boss": {
    "week": {
      "2026-08-30": {
        "week_number": 36,
        "linhas": 12,
        "soma_goal": 245.99,
        "soma_measured_direct": 255.23,
        "soma_signon_direct": 36.09,
        "soma_insert_direct": 0.0,
        "soma_total": 347.45,
        "soma_pd_brk": 6.19,
        "dentro": 9,
        "fora": 2,
        "efetividade": 0.9638,
        "hora_direta": 0.8537,
        "dispersao": 0.8182,
        "parcial": false,
        "group_by": "User ID",
        "extraido_em": "2026-09-23T14:05:00"
      }
    }
  }
}
```

**Por que guardar as somas, e nao so os percentuais:** com as somas
gravadas da pra montar qualquer agrupamento depois (ultimas 4 semanas,
um trimestre) somando os componentes e dividindo no final. Somar os
percentuais de varias semanas daria resultado errado, porque
EFETIVIDADE e HORA DIRETA sao razoes de somas, nao medias.

**Regras de gravacao:**

- Extrair de novo um periodo que ja tem resultado **substitui** as
  semanas contidas no novo arquivo. As semanas que nao estao no arquivo
  ficam intactas.
- `parcial: true` marca a semana cujos sete dias nao cabem inteiros
  dentro do intervalo extraido (alguem extraiu de quarta a terca, por
  exemplo). O numero fica gravado, mas a tela sinaliza que aquela
  semana esta incompleta — senao entra uma semana com menos horas no
  meio da serie e parece queda de indicador. Uma extracao posterior
  cobrindo a semana inteira substitui e limpa a marca.
- `group_by` guarda com qual agrupamento aquela semana foi calculada,
  porque isso muda o significado da DISPERSAO (secao 7).

**Limite conhecido:** o `indicators.json` e por maquina. Se duas
pessoas extraem a mesma operacao, cada uma ve o seu historico. Se isso
virar problema, o passo seguinte e gravar tambem um arquivo acumulado
na pasta da operacao no SharePoint.

**Por que guardar o resultado e nao recalcular do arquivo:** a extracao
apaga o arquivo anterior da mesma operacao (pedido de proposito, pra
pasta nao acumular lixo). Lendo os arquivos da pasta, o historico das
semanas anteriores desapareceria junto.

## 6. Aba Inicio

1. **Filtro de operacao** no topo (uma operacao por vez, com a ultima
   escolha lembrada).
2. Ao escolher, a tela carrega **todas as semanas guardadas daquela
   operacao**, da mais recente pra mais antiga: uma linha por semana,
   colunas `Semana | Tempo meta | Tempo logado | Efetividade | Hora
   direta | Dentro | Fora | Dispersao`, com os tres indicadores
   pintados pelas faixas da secao 4.
3. Acima da tabela, tres cards com a **semana mais recente** e a
   variacao em relacao a semana anterior.
4. Semana marcada `parcial` aparece com um aviso na linha.
5. Sem nada guardado ainda, a tela explica que os numeros aparecem
   depois da primeira extracao — em vez de mostrar tabela vazia.

Semanas sem extracao simplesmente nao aparecem; nao inventamos linha
zerada pra elas.

## 7. Restricao: DISPERSAO exige Group By 2 = User ID

DENTRO e FORA sao **contagem de linhas**. Com Group By 2 = User ID cada
linha e uma pessoa, que e o que a planilha faz. Se a extracao usar
outro agrupamento no segundo nivel ("Shift", "Work Area"...), a
contagem passa a ser de turnos ou areas e o percentual perde o
significado.

Definicao: EFETIVIDADE e HORA DIRETA sao calculadas sempre (sao somas
de horas, nao dependem do agrupamento); a DISPERSAO so e gravada quando
o segundo nivel foi User ID. Nos outros casos fica vazia, com o motivo
visivel na tela.

## 8. Filtros no Summary: Group By 1 fixo em Week

Hoje o app preenche um unico combobox, "Group By 1", com a opcao
escolhida na tela. **Na opcao Week isso muda:** o primeiro nivel passa
a ser fixo e o campo editavel vira o segundo nivel.

Sequencia no Summary, depois de abrir o relatorio e antes de exportar:

1. `Group By 1` = **Week** — fixo, nao aparece como escolha na tela.
2. Marcar o checkbox do segundo nivel de agrupamento
   (`#groupinglvl2_check-inputEl`). O `Group By 2` fica desabilitado
   enquanto ele nao estiver marcado.
3. `Group By 2` = a opcao escolhida na tela, com as mesmas 29 opcoes
   que existem hoje e `User ID` como padrao das 12 operacoes.

Detalhes que a implementacao precisa respeitar:

- O checkbox tem estado. Se ja estiver marcado de uma execucao
  anterior, um clique cego **desmarca** e o `Group By 2` volta a ficar
  inacessivel. Tem que ler o estado antes (ou usar `check()`, que e
  idempotente).
- O `Group By 2` e o mesmo tipo de combobox ExtJS do primeiro, entao
  vale a mesma regra que ja esta no `select_combobox`: digitar tecla
  por tecla e clicar na opcao pelo nome exato. Confirmar com setas +
  Enter depende de quantas opcoes o filtro deixou na lista e erra o
  alvo quando a lista muda.
- **Isso vale so para a opcao Week.** Na opcao Month o comportamento
  continua o de hoje (um nivel so, editavel) ate definirmos o mensal
  na secao 10.
- Muda a contagem de etapas do painel "Andamento": entra a etapa de
  marcar o segundo nivel.
- As paginas de mock dos testes precisam ganhar o checkbox e o
  `Group By 2` pra continuarem cobrindo o fluxo real.

## 9. Estrutura no codigo

Quatro camadas. A parte que calcula nao sabe de arquivo nem de tela — e
a parte que precisa ser testada valor por valor.

```
indicators/
  reader.py    le o .xlsx baixado -> lista de linhas (dicts)
  weekly.py    funcoes puras: classifica a linha, agrupa e calcula
  limits.py    tolerancia (+/- 10) e as faixas de cor da secao 4
indicators_store.py   grava por operacao + periodo + semana
api.py                calcula depois da extracao e entrega pra tela
ui/ (aba Inicio)      filtro de operacao, cards e tabela de semanas
```

**`indicators/reader.py`** — abre o `.xlsx` e devolve as linhas com os
nomes de coluna normalizados (minusculo, sem acento, sem quebra de
linha: `measured direct`, `pd brk`...). O mapeamento e **pelo texto do
cabecalho, nunca pela letra da coluna** — o "Group By 1" e escolhido na
tela e muda o conteudo das colunas de agrupamento. Linha sem data de
semana ou com valor nao numerico nas colunas de calculo e descartada,
o que tambem protege de eventual linha de total no fim do arquivo.

**`indicators/weekly.py`** — nenhum I/O, so calculo:

```
classify_row(linha, tolerancia=10) -> "dentro" | "fora" | None
week_totals(linhas)                -> somas + dentro/fora + percentuais
indicators_by_week(linhas)         -> {data_da_semana: week_totals}
```

**`indicators_store.py`** — mesmo padrao do `history_store.py`, com as
regras de substituicao da secao 5.

**`api.py`** — depois de cada extracao bem-sucedida, calcula, grava e
avisa a tela. Expoe `get_indicators(operacao, periodo)` pra aba Inicio.

## 10. Mes (depois da semana)

Mesmo codigo, entrada diferente: o agrupamento passa a ser o mes e o
resultado vai pra `"month"` no mesmo arquivo. Duas coisas a confirmar
quando chegarmos la:

- Se o `Group By 1` tambem vira fixo no mensal (em `Month` ou
  `Fiscal Month`) com o `Group By 2` editavel, igual ao que a secao 8
  define pra semana. E o mais provavel, mas so entra depois de
  confirmado.
- O que o Medium Level Group traz na extracao mensal — mes ou ainda
  semana? Isso define se o mes vem pronto do relatorio ou se e montado
  somando as semanas.
- Mes calendario ou mes fiscal. As semanas nao fecham no dia 1, entao
  os dois nao dao o mesmo numero. O relatorio tem `Fiscal Month` e
  `Month` como opcoes de agrupamento, o que sugere que a distincao
  importa.

Em nenhuma hipotese o mes e a media dos indicadores semanais.

## 11. Ordem de implementacao

1. `indicators/weekly.py` + `limits.py`, com os testes usando os
   numeros da secao 1.3 como referencia e a planilha de exemplo (tres
   semanas num arquivo) como caso de agrupamento.
2. `indicators/reader.py`, validado contra um export real.
3. Os filtros da secao 8: `Group By 1` fixo em Week, checkbox do
   segundo nivel e `Group By 2` editavel, com os mocks dos testes
   acompanhando.
4. `indicators_store.py` e a gravacao dentro do `api.py`.
5. Aba Inicio: filtro de operacao, cards e tabela de semanas.
6. Mes, com as confirmacoes da secao 10.
