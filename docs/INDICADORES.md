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

O atalho "Semana passada" nao calcula mais datas: ele usa o Default
Date Range do proprio relatorio (secao 8.2), entao quem aplica o
fechamento de semana e o Summary. Quando o intervalo e digitado na mao,
vale o domingo-sabado que ja esta no codigo. O domingo normalmente vem
zerado (nao ha operacao), o que nao afeta nenhum indicador.

## 4. Os seis indicadores, metas e cores

Nesta ordem, que e a ordem da tela:

| # | Indicador | Meta | Verde | Vermelho | Azul |
|---|---|---|---|---|---|
| 1 | **CUBO** | 85% | 85% a 100% | abaixo de 85% | acima de 100% |
| 2 | **EFETIVIDADE** | 90% - 110% | 90% a 110% | abaixo de 90% | acima de 110% |
| 3 | **HORA DIRETA** | 85% | 85% ou mais | abaixo de 85% | — |
| 4 | **PRESENTEISMO** | 98% | 98% ou mais | abaixo de 98% | — |
| 5 | **DISPERSAO** | 70% | 70% ou mais | abaixo de 70% | — |
| 6 | **COVERAGE** | 92% | 92% a 110% | abaixo de 92% | acima de 110% |

A coluna **Meta** e o texto que aparece embaixo do nome de cada
indicador na tela, pra quem esta na reuniao nao precisar lembrar de
cabeca. As outras tres sao as faixas de cor. Tudo igual para as 12
operacoes.

### 4.1 O que ja da pra calcular e o que nao da

Das colunas do Summary saem tres: EFETIVIDADE, HORA DIRETA e DISPERSAO
(secao 1.2). **PRESENTEISMO e COVERAGE sao digitados a mao** — nao
saem de calculo nenhum: uma pessoa preenche o valor de cada semana e de
cada mes (secao 13).

Isso nao e so "depois": muda o desenho. Os dois nao chegam pela
extracao, entao precisam de um caminho proprio pra entrar no
`indicators.json`, e a gravacao da extracao nao pode atropelar o que
eles ja tiverem escrito (secao 5).

**CUBO = EFETIVIDADE x HORA DIRETA x PRESENTEISMO.** Como depende do
presenteismo, **ele tambem nao sai enquanto o presenteismo nao existir**
— sao dois indicadores parados, nao um.

Na tela, indicador sem calculo aparece como `—`, com a coluna e a
ordem ja no lugar. Nada de zero: zero e um numero ruim, traco e
"ainda nao temos".

O que da pra adiantar no codigo: a formula do cubo, as seis faixas de
cor e o lugar dos seis na tela e no arquivo guardado. Quando as duas
definicoes chegarem, entra so o calculo — nada mais muda.

### 4.2 O cubo e o primeiro indicador

O CUBO abre a lista e abre a tela: e o numero que resume os outros. A
ordem da secao 4 e a ordem de exibicao, sempre.

A meta de 85% fica como esta. Vale saber que ela e dura por
construcao: um produto de tres percentuais fica abaixo de cada um
deles. Com os numeros da propria amostra, a semana 36 da EFETIVIDADE
96,38% x HORA DIRETA 85,37% = 82,28%, e multiplicando pelo presenteismo
so cai — com 98%, fecha em 80,63%, vermelho, mesmo com os outros dois
dentro da faixa. Ja a semana 37, puxada pela efetividade de 112,9%,
fecha em 106,26% e sai azul.

## 5. O que fica guardado

Calculado na hora da extracao e gravado em
`%APPDATA%\ScoreCard\indicators.json`, indexado por **operacao ->
periodo -> chave do periodo**. A chave da semana e a data que vem no
arquivo (`2026-08-30`); a do mes e o proprio mes (`2026-09`), que vem
dos parametros da extracao, porque no mensal o arquivo nao traz coluna
de data (secao 10):

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
        "cubo": null,
        "efetividade": 0.9638,
        "hora_direta": 0.8537,
        "presenteismo": null,
        "dispersao": 0.8182,
        "coverage": null,
        "parcial": false,
        "group_by": "User ID",
        "origem": "last_week",
        "extraido_em": "2026-09-23T14:05:00"
      }
    }
  }
}
```

Os seis indicadores ficam gravados na ordem da secao 4, com `null`
naqueles que ainda nao tem calculo. Assim o arquivo ja nasce no formato
final e nao precisa de migracao quando o presenteismo e o coverage
chegarem.

**Por que guardar as somas, e nao so os percentuais:** com as somas
gravadas da pra montar qualquer agrupamento depois (ultimas 4 semanas,
um trimestre) somando os componentes e dividindo no final. Somar os
percentuais de varias semanas daria resultado errado, porque
EFETIVIDADE e HORA DIRETA sao razoes de somas, nao medias.

**Regras de gravacao:**

- Extrair de novo um periodo que ja tem resultado **substitui** as
  semanas contidas no novo arquivo. As semanas que nao estao no arquivo
  ficam intactas.
- **A substituicao e parcial, por origem do dado.** A extracao so
  reescreve o que sai do export — as somas, EFETIVIDADE, HORA DIRETA,
  DISPERSAO e os campos de controle. `presenteismo` e `coverage` vem de
  outra fonte (secao 4.1) e **sao preservados** na regravacao; o `cubo`
  e recalculado com o presenteismo que ja estava la. Sem essa regra,
  reextrair uma semana pra corrigir um numero apagaria calado os dois
  indicadores externos e derrubaria o cubo junto.
- `parcial: true` marca a **semana** cujos sete dias nao cabem inteiros
  dentro do intervalo extraido (alguem extraiu de quarta a terca, por
  exemplo). A marca vale so pra semana; no mes, fechar antes do fim do
  mes e o normal (secao 10). O numero fica gravado, mas a tela
  sinaliza que aquela semana esta incompleta — senao entra uma semana
  com menos horas no meio da serie e parece queda de indicador. Uma extracao posterior
  cobrindo a semana inteira substitui e limpa a marca.
- `group_by` guarda com qual agrupamento aquela semana foi calculada,
  porque isso muda o significado da DISPERSAO (secao 7).
- `origem` diz de onde veio o periodo: `last_week` / `last_month`
  (definido pelo relatorio) ou `digitado` (intervalo da tela). Serve
  pra explicar na tela por que um periodo cobre os dias que cobre.

**As pastas ja estao como o desenho previa:** dentro da pasta de cada
operacao no SharePoint existem `Week` e `Month`, e e de la que sai cada
tipo de export. Isso ja esta implementado e conferido no ambiente real.

**Limite conhecido:** o `indicators.json` e por maquina. Se duas
pessoas extraem a mesma operacao, cada uma ve o seu historico. Se isso
virar problema, o passo seguinte e gravar tambem um arquivo acumulado
na pasta da operacao no SharePoint.

**Por que guardar o resultado e nao recalcular do arquivo:** a extracao
apaga o arquivo anterior da mesma operacao (pedido de proposito, pra
pasta nao acumular lixo). Lendo os arquivos da pasta, o historico das
semanas anteriores desapareceria junto.

## 6. Aba Inicio

A tela repete o formato do bloco W:Y da planilha: **indicador nas
linhas, semana nas colunas, mes no final**.

```
                  Week 36   Week 37   Week 38   |   Setembro
                  (30/08)   (06/09)   (13/09)   |  (01 a 19/09)
CUBO                 —         —         —      |      —
EFETIVIDADE       96,4%    112,9%     ...       |     ...
HORA DIRETA       85,4%     96,1%     ...       |     ...
PRESENTEISMO         —         —         —      |      —
DISPERSAO         81,8%     66,7%     ...       |     ...
COVERAGE             —         —         —      |      —
```

1. **Um filtro so: a operacao**, com a ultima escolha lembrada. O nome
   da operacao escolhida aparece no canto da tabela, na celula vazia
   acima dos nomes dos indicadores, e troca junto com o filtro. Assim a
   tabela diz de quem ela e, inclusive num print levado pra reuniao,
   onde o filtro nao aparece.
2. Escolhida a operacao, a tela mostra **todas as semanas guardadas
   dela**, da mais antiga pra mais recente, e depois de um separador os
   **meses**, tambem em ordem. Sem filtro de periodo: o que esta
   guardado aparece.
3. Conforme as semanas se acumulam, a tabela rola na horizontal. Os
   nomes dos indicadores ficam fixos na primeira coluna, senao rolar
   pro lado perde a referencia de qual linha e qual.
4. Cada celula pintada pelas faixas da secao 4. Indicador sem calculo
   aparece como `—` na linha inteira, mantendo a ordem dos seis.
5. Semana marcada `parcial` ganha um aviso no cabecalho da coluna; o
   mes mostra o intervalo real embaixo do nome.
6. Sem nada guardado ainda, a tela explica que os numeros aparecem
   depois da primeira extracao — em vez de mostrar tabela vazia.

Na tela ficam **so os seis indicadores**. Os numeros que alimentam as
contas (tempo meta, tempo logado, dentro, fora) continuam gravados no
`indicators.json`, mas nao aparecem: a aba principal e pra levar pra
reuniao, nao pra conferir conta.

Semanas sem extracao simplesmente nao aparecem; nao inventamos coluna
zerada pra elas.

### 6.1 Copiar os numeros

A tabela tem que sair da tela pra apresentacao sem redigitacao. Um
botao **Copiar** em cada cabecalho de coluna, e so: copia os seis
numeros daquela semana (ou do mes), de cima pra baixo, na ordem da
secao 4. Nao ha copiar a tabela inteira — o que se leva pra reuniao e
uma coluna por vez.

**So as porcentagens, sem rotulo nenhum.** Nem nome de indicador, nem
nome de semana: quem cola ja tem esses textos na apresentacao, e o
rotulo junto so atrapalha.

**Formato: um valor por linha**, seis linhas. Colando no Excel, cada
valor cai numa celula, descendo a coluna na ordem dos indicadores:

```
(cubo, vazio)
96,4%
85,4%
(presenteismo, vazio)
81,8%
(coverage, vazio)
```

**Indicador sem numero vira linha vazia**, nao `—` nem `0`. Assim as
seis posicoes ficam preservadas e nada sobe de lugar; um traco viraria
celula de texto no meio dos numeros.

**Valor igual ao da tela** (`96,4%`, com virgula e sinal de porcento):
o que e apresentado e o que foi conferido. Se um dia precisar do numero
puro pra fazer conta, e mudar uma linha.

**Como copiar, no ambiente do app:** `navigator.clipboard.writeText`
quando disponivel, com o truque do `<textarea>` escondido +
`document.execCommand('copy')` como reserva. O WebView2 do Windows
aceita o primeiro em contexto seguro, mas o segundo cobre o caso de
nao aceitar. Nenhuma dependencia nova, nada passa pelo Python.

**O botao confirma**: vira "Copiado" por dois segundos. Copia e uma
acao sem retorno visivel — sem confirmacao, a pessoa clica de novo sem
saber se funcionou.

**O mes nao e a soma das semanas da tela, e isso e proposital.** Sao
duas extracoes diferentes, com intervalos que nao coincidem: o mes
comeca no dia 1, que quase sempre cai no meio de uma semana. Em
setembro de 2026 o mes vai de 01 a 19/09, enquanto a semana 36 comeca
em 30/08 — os quatro primeiros dias dela sao de agosto e nao entram no
mes. Por isso os numeros das colunas nao fecham com o da ultima, e a
tela nao deve sugerir que fechariam.

A semana que atravessa a virada do mes aparece **no mes da sua data de
inicio**: a semana de 30/08 fica em agosto, inteira, e nao e partida
nem repetida em setembro. Isso nao afeta o numero do mes, que vem de
uma extracao propria comecando no dia 1 e nao le as semanas.

## 7. Restricao: DISPERSAO exige o detalhe em User ID

DENTRO e FORA sao **contagem de linhas**. Com User ID no nivel de
detalhe cada linha e uma pessoa, que e o que a planilha faz. Com outro
agrupamento ("Shift", "Work Area"...) a contagem passa a ser de turnos
ou areas e o percentual perde o significado.

O nivel de detalhe muda conforme o periodo: na semana e o `Group By 2`
(porque o `Group By 1` fica fixo em Week), no mes e o `Group By 1`
(porque ele e o unico nivel). A regra e a mesma nos dois casos.

Definicao: EFETIVIDADE e HORA DIRETA sao calculadas sempre (sao somas
de horas, nao dependem do agrupamento); a DISPERSAO so e gravada quando
o nivel de detalhe foi User ID. Nos outros casos fica vazia, com o
motivo visivel na tela.

## 8. Filtros no Summary: diferentes na semana e no mes

Hoje o app preenche um unico combobox, "Group By 1", com a opcao
escolhida na tela. **Na opcao Week isso muda:** o primeiro nivel passa
a ser fixo em Week e o campo editavel vira o segundo nivel. **Na opcao
Month continua exatamente como hoje**, um nivel so.

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
- **Isso vale so para a opcao Week.** Na opcao Month e `Group By 1` =
  a opcao da tela (`User ID` nas 12 operacoes), sem segundo nivel e sem
  Week — o relatorio ja vem com o mes consolidado (secao 10).
- Muda a contagem de etapas do painel "Andamento": entra a etapa de
  marcar o segundo nivel.
- As paginas de mock dos testes precisam ganhar o checkbox e o
  `Group By 2` pra continuarem cobrindo o fluxo real.

### 8.1 Mes passado usa o Date Range do proprio relatorio

Pro mes fechado, **nao se preenche data nenhuma**: usa-se o bloco
"DATE RANGE CRITERIA" do relatorio.

1. Marcar o radio **Default Date Range** (o fluxo de datas digitadas
   marca "Custom Date Range", entao voltar pro padrao e um passo
   explicito, nao um estado que sobra da execucao anterior).
2. `Date Range` = **Last Month**.

Hoje o codigo ja tem esse caminho, mas ele digita so `"Las"` no
combobox e confirma com Enter, sem dizer qual opcao quer. Isso pega a
primeira que o filtro deixar na lista — pode ser "Last Week", "Last
Month" ou "Last Year", conforme o que o relatorio oferecer. Tem que
passar o nome completo e clicar na opcao pelo nome exato, como ja e
feito no Group By.

**Efeito no que fica guardado:** com o Last Month quem define o
intervalo e o relatorio, nao a tela. A chave do mes passa a ser o mes
anterior a data da extracao (extraindo em 23/09/2026, a chave e
`2026-08`) e o intervalo gravado e o mes calendario correspondente,
anotado como vindo do Last Month e nao digitado. Continua valendo a
regra da secao 5: reextrair o mesmo mes substitui a entrada.

O "Last Month" do relatorio e o mes calendario inteiro, do dia 1 ao
ultimo dia. Os dois caminhos do mensal convivem sem conflito: o Last
Month fecha o mes anterior e o intervalo digitado acompanha o mes
corrente ate o ultimo sabado.

### 8.2 Semana passada segue o mesmo caminho

O atalho "Semana passada" usa o mesmo mecanismo: **Default Date Range**
com `Date Range` = **Last Week**. Com isso o fechamento de semana e o
do proprio Summary, e nao uma conta feita na tela torcendo pra bater —
que era o risco discutido na secao 3.

O `date_range_type_text` das 12 operacoes hoje guarda `"Las"`, um
pedaco de texto que nao diz qual opcao e. Passa a guardar o nome
completo por periodo: `Last Week` na semana, `Last Month` no mes.

O "Last Week" do relatorio e domingo-sabado, o mesmo fechamento da
secao 3. **Rede de protecao mesmo assim:** se algum dia nao for, o
arquivo vem com duas semanas parciais em vez de uma inteira — e a marca
`parcial` da secao 5 acusa isso na tela em vez de deixar passar um
numero errado.

### 8.3 Dois caminhos de data, sem voltar com o seletor

Os dois atalhos passam a ser, na pratica, uma troca de modo:

- Clicar em "Semana passada" ou "Mes passado" -> **modo padrao do
  relatorio**: os campos de data ficam vazios e desabilitados, com um
  aviso do que vai ser usado ("periodo definido pelo relatorio: Last
  Week").
- Digitar qualquer data -> **modo intervalo**, exatamente como hoje.

Assim nao volta o seletor "Ultima semana / Periodo especifico" que foi
tirado da tela: os botoes que ja existem e que a pessoa ja usa e que
definem o modo. A validacao de "datas obrigatorias" precisa afrouxar —
hoje ela barra a extracao sem data, e no modo padrao isso passa a ser
valido.

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
regras de substituicao da secao 5. Duas portas de entrada separadas:
uma pra extracao (grava o que veio do export) e outra pra entrada
manual (grava presenteismo e coverage numa semana ou mes, criando a
entrada se ela ainda nao existir, e recalcula o cubo). Nenhuma das duas
sobrescreve o territorio da outra.

**`api.py`** — depois de cada extracao bem-sucedida, calcula, grava e
avisa a tela. Expoe `get_indicators(operacao, periodo)` pra aba Inicio.

## 10. Mes: relatorio consolidado, sem quebra de semana

No mensal o `Group By 1` e **User ID** e nao existe segundo nivel nem
agrupamento por Week. O relatorio vem com o **mes consolidado**: uma
linha por pessoa com os totais do periodo inteiro.

Confirmado pela planilha `Logica_Score_Card_-_Mes.xlsx`: a coluna A e
`Detail Level Group` com o User ID direto, e nao existe nenhuma coluna
de data.

### 10.1 As colunas mudam de lugar entre os dois

Sem o `Medium Level Group`, **tudo anda uma posicao pra esquerda**:

| Coluna | Semana | Mes |
|---|---|---|
| Medium Level Group (semana) | A | nao existe |
| Detail Level Group (User ID) | B | A |
| Var | C | B |
| Goal | D | C |
| Measured Direct | E | D |
| Unmeasured Signon Direct | G | F |
| Unmeasured Insert Direct | I | H |
| PD Brk | K | J |
| Total | L | K |

E a prova de que o leitor tem que se ancorar no **titulo** da coluna e
nunca na letra: o mesmo relatorio, com um agrupamento a menos, ja
entrega o layout deslocado. Lendo por letra, o mensal calcularia
efetividade com a coluna errada e entregaria um numero plausivel e
falso — o pior tipo de erro.

**Como o leitor sabe qual e qual:** existe coluna `Medium Level Group`
-> export semanal, agrupa por ela; nao existe -> export mensal, um
grupo so.

### 10.2 As formulas sao as mesmas

A planilha do mes usa `SUM(C:C)` onde a da semana usa
`SUMIF($U:$U, semana, $D:$D)`. Fora isso, tudo igual: mesma
classificacao DENTRO/FORA com tolerancia +/- 10, mesmas somas, mesmos
tres indicadores. Somar a coluna inteira e o mesmo que somar um grupo
so.

**Conferencia** (recalculado fora do Excel, bate com a planilha):

| | planilha | recalculado |
|---|---|---|
| tempo meta | 1.407,65 | 1.407,65 |
| tempo logado | 1.402,52 | 1.402,52 |
| EFETIVIDADE | 100,37% | 100,37% |
| HORA DIRETA | 92,99% | 92,99% |
| DISPERSAO | 60,00% (9 / 15) | 60,00% |

Segundo caso de referencia dos testes, ao lado do semanal da secao 1.3:
um cobre o agrupamento por semana, o outro o consolidado sem data.

### 10.3 Consequencias

- **A chave do mes vem dos parametros da extracao** (o intervalo de
  datas digitado na tela, ou o mes anterior quando se usa o Last
  Month), nao do conteudo do arquivo — ao contrario da semana, onde a
  data vem pronta.
- **O intervalo e escolhido a cada extracao, na tela.** Nao ha regra
  automatica de fechamento: quem extrai digita o periodo. A convencao
  usada na pratica e **do dia 1 ate o ultimo sabado**, porque a semana
  fecha no sabado — em setembro de 2026, extraindo no dia 23, o mes vai
  de 01/09 a 19/09. O mes nao termina no ultimo dia do mes, e isso e o
  comportamento normal, nao uma falha.
- **Por isso o mes nao usa a marca `parcial`.** Fechar antes do fim do
  mes e a regra, nao a excecao; marcar aviso em todo mes seria ruido. O
  que a entrada guarda e o **intervalo real extraido** (`de` e `ate`),
  e a tela mostra o mes com esse intervalo ao lado: "setembro (01 a
  19/09)". Assim da pra ver de imediato ate onde o numero vai.
- **Reextrair o mesmo mes com um intervalo maior substitui a entrada**,
  pela regra da secao 5. E o fluxo esperado: durante o mes a mesma
  chave (`2026-09`) vai sendo atualizada a cada semana fechada, sempre
  cobrindo mais dias.
- **Uma chave por mes, um mes por extracao.** Como nao existe coluna de
  data, um intervalo cobrindo dois meses viraria um bloco consolidado
  so, impossivel de separar depois. A chave gravada e o mes da data
  inicial. Na pratica o mensal sempre comeca no dia 1, entao isso nao
  aparece; se um dia aparecer, a tela **avisa e grava assim mesmo** —
  ver secao 10.4.
- **O atalho "Mes passado" deixa de preencher datas.** Ele passa a
  marcar o Default Date Range com `Last Month`, pela secao 8.1: os
  campos de data ficam vazios e desabilitados, e quem define o periodo
  e o relatorio. O intervalo digitado na tela continua sendo o caminho
  pro mes corrente, ate o ultimo sabado fechado.

### 10.4 Nenhuma validacao de data bloqueia a extracao

Regra geral: os avisos de periodo sao **avisos**, nunca travas. Quem
esta extraindo e quem sabe o que quer puxar.

O caso concreto: **uma semana completa que atravessa a virada do mes**
— do dia 29 de um mes ao dia 4 do outro — e um periodo legitimo e
comum, e tem que passar sem nenhum atrito. O mesmo vale pra qualquer
intervalo digitado na aba de extracao.

A razao de fundo: **o numero da semana vai pra reuniao**, entao ele
precisa ser o da semana inteira. Um limite de calendario que obrigasse
a cortar no dia 31 entregaria uma semana pela metade — exatamente o
numero errado pra apresentar. E tambem por isso que a marca `parcial`
existe: ela nao e burocracia, e o aviso de que aquele numero ainda nao
esta pronto pra levar pra reuniao.

Isso nao conflita com o mensal comecar no dia 1: sao coisas separadas.
O mes e extraido a parte, filtrando do dia 1, e nunca e montado a
partir das semanas — entao uma semana que pega dias de dois meses nao
contamina numero nenhum. Ela e guardada pela data de inicio dela e
pronto.

Onde ainda cabe um aviso (sem travar nada): semana parcial (secao 5) e
intervalo mensal atravessando a virada (secao 10.3). Nos dois casos o
numero e gravado normalmente e a tela so conta o que aconteceu.

## 11. Ordem de implementacao

1. `indicators/weekly.py` + `limits.py`, com os seis indicadores na
   ordem da secao 4 (dois sem calculo, o cubo esperando o
   presenteismo), as seis faixas de cor e os testes usando os numeros
   da secao 1.3 como referencia e a planilha de exemplo (tres semanas
   num arquivo) como caso de agrupamento.
2. `indicators/reader.py`, validado contra um export real.
3. Os filtros da secao 8: `Group By 1` fixo em Week, checkbox do
   segundo nivel, `Group By 2` editavel e os dois atalhos de data
   usando o Default Date Range com o nome completo da opcao, com os
   mocks dos testes acompanhando.
4. `indicators_store.py` e a gravacao dentro do `api.py`.
5. Aba Inicio: filtro de operacao, tabela com os seis indicadores nas
   linhas, semanas nas colunas, os meses no fim e os botoes de copiar
   (secao 6.1).
6. Mes: um grupo unico com a chave vinda dos parametros, reusando o
   mesmo calculo.

## 12. Resumo para a implementacao

O que muda em cada arquivo, pra proxima sessao comecar sem reabrir a
discussao.

**Arquivos novos**

| Arquivo | O que faz |
|---|---|
| `indicators/reader.py` | le o `.xlsx`, normaliza os titulos das colunas, distingue o export semanal do mensal pela presenca do `Medium Level Group` (secao 10.1), descarta linha invalida |
| `indicators/weekly.py` | `classify_row`, somas do grupo e `indicators_by_period` — funcoes puras, sem I/O |
| `indicators/limits.py` | tolerancia +/- 10, ordem dos seis e as faixas de cor da secao 4 |
| `indicators_store.py` | `indicators.json` em `%APPDATA%\ScoreCard\`, com as regras da secao 5 |
| `tests/test_indicators.py` | os numeros da secao 1.3 como referencia, mais o caso de tres semanas num arquivo |
| `tests/fixtures/summary_3semanas.xlsx` | export de exemplo com as tres semanas |
| `tests/fixtures/summary_mes.xlsx` | export mensal de exemplo, sem coluna de data |

**Arquivos alterados**

| Arquivo | Mudanca |
|---|---|
| `config/operations.py` | `date_range_type_text` passa a guardar o nome completo por periodo (`Last Week` / `Last Month`) em vez de `"Las"` |
| `automation/base.py` | Date Range escolhido pelo nome exato; marcar o radio `Default Date Range`; helper idempotente pro checkbox do segundo nivel |
| `automation/generic.py` | fluxo por periodo — semana: `Group By 1` = Week + checkbox + `Group By 2`; mes: `Group By 1` = opcao da tela. Modo de data padrao vs digitado. Etapa nova no progresso |
| `api.py` | calcula e grava depois da extracao; `get_indicators(operacao, mes)`; entrega as faixas de cor pra tela |
| `ui/index.html` | aba Inicio com o filtro de operacao e a tabela dos seis; campos de data desabilitados no modo padrao |
| `ui/app.js` | troca de modo dos atalhos, render da tabela e das cores; copiar em TSV (secao 6.1); `lastWeekRange`/`lastMonthRange` deixam de preencher datas |
| `ui/style.css` | verde, vermelho e azul das faixas; celula `—`; cards Week/Month e Fonte de dados (secao 15) |
| `tests/fixtures/*.html` | mocks ganham o checkbox do segundo nivel e o `Group By 2` |
| `requirements.txt` | entra `openpyxl` |
| `build.spec` | conferir se o `openpyxl` entra no `--onefile` (hidden imports) e que o `.exe` continua sendo um arquivo so |
| `README.md` | secao dos indicadores |

**Ordem:** a da secao 11.

**Aberto, sem travar o inicio:** nada. Ver a secao 13.

**Depois, quando as definicoes chegarem:** o calculo do PRESENTEISMO e
do COVERAGE, que destrava o CUBO junto.

## 13. Presenteismo e coverage: entrada manual

Os dois nao sao calculados: **uma pessoa digita o numero** de cada
semana e de cada mes, por operacao. Com o presenteismo preenchido, o
CUBO sai sozinho — e por isso que os tres andam juntos.

**Onde se digita.** Na propria aba Inicio, clicando na celula da linha
do presenteismo ou do coverage, na coluna da semana. E onde a pessoa ja
esta olhando o numero faltando; mandar ela pra outra tela pra voltar
depois so cria passo. Ao salvar, a linha do CUBO se completa na hora.

**Regras:**

- Valor em percentual, aceitando virgula ou ponto. Fora de 0 a 200% a
  tela pergunta antes de gravar — nao bloqueia, so confere, porque
  digito trocado e o erro mais comum de campo manual.
- Da pra digitar **antes da extracao**. Se a semana ainda nao existe no
  arquivo, ela e criada so com os campos manuais e os calculados ficam
  como `—` ate a extracao chegar. Os dois caminhos funcionam em
  qualquer ordem.
- Reextrair **nao apaga** o que foi digitado (secao 5).
- Cada valor guarda quando foi preenchido. Numero digitado a mao sem
  data de quando vira duvida em reuniao tres semanas depois.

### 13.1 Onde o arquivo mora: isso precisa ser decidido

Ate aqui o `indicators.json` ficava em `%APPDATA%\ScoreCard\`, **por
maquina** — decisao registrada na secao 5 quando tudo vinha da
extracao. Com preenchimento manual feito por mais de uma pessoa, isso
deixa de funcionar:

> voce extrai a semana na sua maquina; outra pessoa digita o
> presenteismo na dela. Nenhuma das duas tem a tabela inteira, e o CUBO
> nao fecha em lugar nenhum.

Duas saidas:

1. **Guardar na pasta do SharePoint** (recomendado). A pasta ja esta
   configurada e ja sincroniza pelo OneDrive, entao todo mundo le e
   escreve o mesmo arquivo. Risco: duas pessoas salvando ao mesmo tempo
   geram copia de conflito do OneDrive. Da pra reduzir com um arquivo
   por operacao — a escrita e rara e curta, dificilmente duas caem no
   mesmo instante.
2. **Manter local** e aceitar que cada maquina tem a sua parte. So
   funciona se uma pessoa so fizer tudo, extracao e digitacao.

A escolha muda pouco codigo (e o caminho do arquivo), mas muda muito o
uso. **Fica pra depois, junto com a entrada manual.** Ate la o arquivo
segue em `%APPDATA%`, como esta na secao 5: enquanto tudo vem da
extracao, cada maquina se vira sozinha. Trocar depois e mudar o caminho
e reextrair o que ja estava guardado — nao trava nada agora.

## 14. Em aberto

**O escopo de agora:** semana e mes com **EFETIVIDADE, HORA DIRETA e
DISPERSAO**, que e tudo o que sai do export atual. Os seis ja tem lugar
na tela e no arquivo; os tres que faltam aparecem como `—`.

**Depois, tudo junto:**

1. A tela de **entrada manual** do presenteismo e do coverage (secao
   13), que destrava o **CUBO** por dependencia.
2. **Onde o `indicators.json` mora** (secao 13.1) — so vira problema
   quando mais de uma pessoa preencher.
3. A aba **Headcount**, ainda sem conteudo definido.

A ordem esta decidida: primeiro a semana e o mes com os tres
indicadores que saem do export atual; os outros tres entram depois, por
uma porta separada no store (secao 9), sem refazer nada do que ja
estiver pronto.

**Tecnico, resolve durante a implementacao:**

4. `openpyxl` embarcado no `--onefile`, mantendo o `.exe` como um
   arquivo so.

**Decidido, sem pendencia:**

- Meta de 85% do cubo mantida, e o cubo e o primeiro indicador (secao
  4.2).
- `Last Month` = mes calendario inteiro (secao 8.1).
- `Last Week` = domingo-sabado (secao 8.2).
- Aba Inicio com filtro so de operacao e so os seis indicadores, sem
  filtro de mes e sem bloco de numeros de apoio (secao 6).
- DISPERSAO vazia quando o detalhe nao e User ID (secao 7).
- Marca `parcial` na semana incompleta (secao 5).
- Presenteismo e coverage digitados na propria aba Inicio (secao 13).

## 15. Ajuste de tela: os cards Week/Month estao apertados

Nao e sobre indicadores, mas entra na mesma leva de mudancas, porque
mexe nos mesmos arquivos.

**O que acontece.** Os cards "Week" e "Month" do "Periodo do indicador"
ficam estreitos demais: a legenda quebra em duas linhas e o texto fica
espremido contra o titulo.

**Medido na tela real**, renderizando `ui/index.html`:

| Viewport | Card de parametros | Cada botao | Altura da legenda |
|---|---|---|---|
| 1280px | 553px | 125px | **24px (duas linhas)** |
| 1440px | 644px | 138px | **24px (duas linhas)** |
| 1920px | 915px | 422px de grupo, 206px cada | 12px (uma linha) |

**Causa.** Tres divisoes em cima da mesma largura: o card de parametros
divide a linha com o painel de andamento, dentro dele os campos
dividem a linha em dois, e dentro dessa metade os dois botoes dividem
de novo. Sobra `125px` por botao a 1280. Desses, o icone come uns 38px
com o espacamento, e a legenda "Indicadores semanais" precisa de
`107px` em 11px pra caber numa linha — entao quebra. So passa de
1500px de janela e o problema some, o que explica ele nao aparecer
sempre.

**O ajuste:**

1. **Tirar as legendas** "Indicadores semanais" e "Indicadores
   mensais". O rotulo do campo ja diz "Periodo do indicador" e o botao
   ja diz "Week"; a legenda repete e e ela que causa o aperto.
2. **Subir o titulo** de 13px pra 15px, o mesmo tamanho dos outros
   campos do formulario. Com a legenda fora, sobra altura pra isso sem
   o botao crescer.
3. **Empilhar em vez de espremer**: abaixo de uma largura minima, os
   dois botoes passam um embaixo do outro. Espremer ate quebrar a
   palavra e o que acontece hoje.
4. **Mesmo tratamento no card "Fonte de dados"**, que tem a mesma forma
   (titulo + legenda) e fica na mesma linha — se so um dos dois mudar,
   os dois ficam desalinhados.

**De quebra, trocar os emoji por SVG.** Os icones desses cards sao
emoji no HTML (`🖧`, `📆`, `🗓️`). A barra lateral ja usa SVG de traco,
e o `🖧` em particular nao existe em varias fontes do Windows — aparece
como quadrado ou em preto e branco no meio de uma interface que e toda
monocromatica de traco. Como o ajuste ja mexe nesses cards, e o momento
de igualar.

## 16. Onde paramos (24/09/2026)

### Feito e no branch

Tudo das secoes 1 a 15 esta implementado, com 61 testes passando. A
primeira extracao real aconteceu e apontou uma coisa que nenhuma das
planilhas mostrava: **o Summary entrega o relatorio em `.xls` antigo**
(BIFF, gerado pelo JasperReports), nao em `.xlsx`.

O leitor passou a descobrir o formato pelos **primeiros bytes** do
arquivo, nao pela extensao do nome, e le os dois. O `.xls` que veio da
extracao real virou fixture (`tests/fixtures/summary_real.xls`, com os
identificadores das pessoas trocados por codigos).

O que esse arquivo confirmou, e nao precisa mais ser verificado:

- Os titulos das colunas sao exatamente os que o leitor espera.
- Cabecalho na primeira linha, sem bloco de titulo antes.
- Sem linha de total no fim.
- As semanas vem separadas certinho (15, 15 e 16 linhas).

### Proximo passo: a falha do calculo precisa aparecer na tela

**E por onde retomar.** Hoje, quando o calculo nao roda, `api.py`
guarda o motivo em `result["indicators_message"]` e **ninguem mostra
esse campo**. A extracao segue como "Concluida", porque o arquivo
realmente foi salvo — e foi exatamente isso que escondeu o problema do
`.xls` ate a primeira extracao real.

O que fazer:

1. A tela de extracao mostra o aviso quando ele existe, em vez de so
   "Concluida".
2. O historico distingue os tres casos: concluida, concluida sem
   indicador, e falha.
3. Um teste cobrindo o caminho: arquivo salvo, calculo recusado, aviso
   visivel.

### Decidido e fechado

O dia em que a semana comeca **nao importa**. O arquivo real vem com
semanas de segunda a domingo (31/08, 07/09, 14/09), diferente das
planilhas de exemplo, que eram de domingo. Nada no calculo depende
disso — ele agrupa pela data que vem no arquivo — e os rotulos saem
iguais (Week 36, 37, 38 nos dois casos). O atalho de datas digitadas
fica como esta.

### Continua em aberto, sem pressa

- Presenteismo e coverage: entrada manual (secao 13), que destrava o
  cubo.
- Onde o `indicators.json` mora quando mais de uma pessoa preencher
  (secao 13.1).
- Aba Headcount.
- Tempo de abertura do `.exe`: o teto e a descompactacao dos ~700 MB de
  Chromium e Node a cada abertura, que vem da regra de um arquivo so.
  Sair do teto exige o modo pasta ou desempacotar uma vez em
  `%LOCALAPPDATA%`.
