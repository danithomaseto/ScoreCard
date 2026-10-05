# Score Card — documento completo da ferramenta

**Versão:** V.01.1 · **Criado por:** Daniel Thomaseto · **Atualizado em:** 05/10/2026

Este documento explica o Score Card de ponta a ponta: para que serve,
como se usa, como cada indicador é calculado, onde ficam os dados, como
se gera uma versão nova e como a ferramenta foi construída. Os detalhes
de desenho de cada regra, com as datas das decisões, estão em
[`INDICADORES.md`](INDICADORES.md). O passo a passo técnico de build está
no [`README.md`](../README.md).

---

## Sumário

1. [Resumo](#1-resumo)
2. [Problema e solução](#2-problema-e-solução)
3. [Operações atendidas](#3-operações-atendidas)
4. [Como usar, tela por tela](#4-como-usar-tela-por-tela)
5. [Os indicadores e como são calculados](#5-os-indicadores-e-como-são-calculados)
6. [Regras de calendário](#6-regras-de-calendário)
7. [Onde ficam os dados](#7-onde-ficam-os-dados)
8. [Segurança](#8-segurança)
9. [Distribuição, versão e build](#9-distribuição-versão-e-build)
10. [Suporte e diagnóstico](#10-suporte-e-diagnóstico)
11. [Arquitetura técnica](#11-arquitetura-técnica)
12. [Testes](#12-testes)
13. [Limites conhecidos e próximos passos](#13-limites-conhecidos-e-próximos-passos)
14. [Histórico do projeto](#14-histórico-do-projeto)

---

## 1. Resumo

O **Score Card** é um aplicativo para Windows, distribuído num único
arquivo (`ScoreCard.exe`), que:

- **extrai** automaticamente o relatório Summary (`rptLMUserSummaryRaw`)
  do BlueYonder, para uma operação ou para várias em fila, e salva o
  arquivo na pasta da operação no SharePoint;
- **calcula** os seis indicadores do Score Card — Cubo, Efetividade,
  Hora Direta, Presenteísmo, Dispersão e Coverage — por semana, por mês
  e nos dias de pico;
- **mostra** tudo num painel único (aba Início), com cores por meta,
  botão para copiar cada coluna para a apresentação e um modo
  apresentação em tela cheia;
- **organiza** os lançamentos manuais (HC, dias úteis, horas/dia,
  faltas, sinergia) em telas próprias, com a fórmula sempre visível.

Não precisa instalar nada: basta abrir o `ScoreCard.exe`.

---

## 2. Problema e solução

**Problema / Oportunidade.** O Score Card das 12 operações era montado
quase todo à mão. Para cada operação era preciso entrar no BlueYonder,
aplicar os filtros e exportar o relatório, repetindo isso para a
semana, o mês e os dias de pico. Os indicadores eram calculados numa
planilha de macros, o que abria espaço para erro de cópia, fórmula
quebrada e critérios diferentes entre quem calculava. Algumas regras
eram difíceis de aplicar à mão, como a escala espanhola, o ciclo da
folha do dia 13 ao 12, a semana incompleta e os dias de pico. Além
disso, informações como HC, faltas, horas e sinergia ficavam
espalhadas. No fim, a maior parte do tempo ia para preparar os dados,
e não para analisá-los.

**Solução / Melhoria.** O Score Card é um aplicativo distribuído num
único arquivo, sem instalação. Ele extrai automaticamente os relatórios
de uma ou de várias operações em fila e salva tudo direto no
SharePoint. Também calcula os seis indicadores por semana, mês e pico,
com as regras de cada operação já embutidas. Os resultados aparecem num
painel único, com cores por meta, cópia direta para a apresentação e
modo tela cheia. Headcount e Coverage ganharam telas próprias, com a
fórmula sempre visível. O app é seguro: a senha nunca é gravada, ele
confere a VPN antes de extrair e gera um diagnóstico para suporte. O
resultado é menos tempo preparando dados e mais tempo agindo sobre os
indicadores.

---

## 3. Operações atendidas

Todas usam o mesmo relatório (`rptLMUserSummaryRaw`) e a mesma
automação. O agrupamento padrão de todas é **User ID**.

| Operação | Subpasta no SharePoint | Escala espanhola |
|---|---|---|
| Hugo Boss | `Hugo Boss` | — |
| Hughes | `Hughes` | — |
| Swa | `SWA` | — |
| Nike/Fisia | `Nike` | **sim** |
| Sumup | `SumUp` | — |
| Rede | `Rede` | **sim** |
| JCB | `JCB` | **sim** |
| Lego | `Lego` | — |
| SpaceX | `SpaceX` | — |
| HPE | `HPE` | **sim** |
| Armani | `Armani` | — |
| ABB | `ABB` | — |

Dentro da subpasta de cada operação, o arquivo vai para `Week`, `Month`
ou `Dias de Pico`, conforme o tipo de extração.

**Adicionar uma operação nova** é uma entrada a mais em
`config/operations.py` (nome, endereço de login, subpasta e, se for o
caso, `"escala_espanhola": True`). Nenhuma outra parte do código muda.

---

## 4. Como usar, tela por tela

### 4.1 Abrir o app

- Dê dois cliques no `ScoreCard.exe`. Na **primeira abertura de cada
  versão** ele leva alguns segundos a mais, porque prepara os arquivos
  internos (a tela de abertura mostra o andamento). Das próximas vezes
  abre direto.
- A janela abre maximizada.
- **Uma janela só:** clicar no `ScoreCard.exe` com o app já aberto não
  abre outra janela — traz para a frente a que está aberta (inclusive
  se estiver minimizada). Duas janelas gravando nos mesmos dados
  sobrescreveriam uma à outra.

### 4.2 Login

- Entre com **o seu** usuário e senha do Summary. Cada pessoa usa a
  própria credencial.
- A senha fica só na memória enquanto o app está aberto (ver
  [Segurança](#8-segurança)).
- Se o Caps Lock estiver ligado, aparece um aviso embaixo da senha —
  senha errada repetida pode bloquear o usuário no Summary.
- Na primeira vez, o app pede a **pasta do SharePoint** (a pasta
  sincronizada pelo OneDrive onde ficam as subpastas das operações).
  Ela fica guardada e pode ser trocada em Configurações.

### 4.3 Início (o painel)

É a tela principal e a que se apresenta.

- **Filtros:** operação e mês (abre no mês atual). O seletor de mês
  deixa voltar ao mês anterior — no começo do mês é ali que está o
  fechamento.
- **Colunas:** as semanas extraídas que têm dia no mês (Week 36,
  Week 37…, com as datas), depois o **mês** e, colado nele, o **Pico**.
  Semana que não está completa mostra "semana incompleta"; mês ou pico
  extraído só até parte do mês mostra "mês em andamento".
- **Linhas:** os seis indicadores, nesta ordem: CUBO, EFETIVIDADE, HORA
  DIRETA, PRESENTEÍSMO, DISPERSÃO e COVERAGE, cada um com a meta
  escrita embaixo do nome.
- **Cores:** verde = dentro da meta, vermelho = abaixo, azul = acima do
  teto, traço (—) = ainda sem número. Traço nunca é zero: zero seria um
  resultado ruim; traço é "ainda não temos".
- **Percentuais** sempre com duas casas decimais (96,38%, 100,00%).
- **Copiar:** cada coluna tem um botão que copia os seis valores, na
  ordem da tela, para colar direto na apresentação (Excel ou
  PowerPoint). Indicador sem número vira célula vazia, para nenhum
  valor mudar de lugar. Cada valor vai centralizado, em fonte de 10 pt
  e sem quebra de linha, para caber numa linha só da célula.
- **Última extração:** mostra quando a operação escolhida foi extraída
  pela última vez.
- **Sem extração no mês:** aparece "Nenhuma extração de <operação> em
  <mês> ainda" com o botão **Extrair agora**, que abre a tela de
  extração com a operação já escolhida.

**Distribuição da dispersão** (quadro embaixo da tabela, só fora do modo
apresentação): gráfico de barras com quantas pessoas caíram em cada
faixa de Var no mês, da extração Month — ver [5.7](#57-distribuição-da-dispersão).

**Modo apresentação** (botão ao lado do título "Início"):

- tela cheia, sem menu, só a tabela, com letra maior;
- **setas ← →** trocam a operação;
- **Esc** sai (a janela volta maximizada).

### 4.4 Extrair Dados (uma operação)

1. **Período do indicador:** Week, Month ou Dias de Pico.
2. **Operação.**
3. **Período (datas):** digite a data inicial e final, ou use os
   atalhos **Semana passada** / **Mês passado**. Sem datas, o app usa o
   "Last Week" / "Last Month" do próprio relatório.
4. **Agrupamento:** o rótulo do campo diz para onde ele vai:
   - **Week:** Group By 1 fica fixo em Week e o campo escolhido (User ID)
     vai no Group By 2;
   - **Month:** o campo escolhido vai no Group By 1;
   - **Dias de Pico:** Group By 1 fixo em Report Date (campo travado).
5. **Iniciar extração.** O painel "Andamento" mostra as 10 etapas
   (abrir o navegador, login, menu Reports, relatório, período, Group
   By 1 e 2, exportar, salvar) e o percentual.

Antes de abrir o navegador, o app confere se o servidor da operação
responde (VPN). Sem VPN, ele avisa na hora, em vez de esperar o login
falhar por tempo esgotado.

Ao terminar: botão para **abrir a pasta** do arquivo e, se algo falhou,
para **ver o print da tela do erro**. Os indicadores são calculados
automaticamente e já aparecem na aba Início.

**Fechar a janela durante uma extração** pede confirmação ("Há uma
extração em andamento…"), porque fechar no meio deixa o download pela
metade. Fora de extração, fecha direto.

O **histórico** embaixo da tela lista as últimas extrações (operação,
período, agrupamento, tipo, duração, resultado).

### 4.5 Extrair Múltiplos (fila)

Mesmos parâmetros, mas com várias operações marcadas (há "Selecionar
todas" e "Limpar"). As operações rodam uma depois da outra, num único
navegador:

- uma falha não interrompe a fila — as outras continuam;
- servidor fora do ar (sem VPN) é checado uma vez só por servidor;
- **Parar fila:** a operação em andamento termina e a fila para antes
  da próxima;
- no fim, um resumo: "X de Y extrações concluídas, N com falha…".

### 4.6 Headcount (Cálculo de Presenteísmo)

Onde se lança o quadro de cada gestor para o presenteísmo.

- **Filtros:** operação (ou "Todas as Operações"), mês vigente, semana
  do mês e a visualização **Semanal** ou **Resultado do Mês**.
- **Semanal:** as semanas do mês vigente (S1, S2…), de segunda a
  domingo, cortadas na virada do mês, com o nome da semana do Summary
  (ex.: "Week 39 · 21/09 a 27/09"). Abre na última semana já encerrada.
- **Resultado do Mês:** o ciclo da folha ponto, do dia 13 ao dia 12.
- **Cards:** operação, período (com os dias úteis), HC total, faltas
  (com as horas perdidas) e o presenteísmo, com "dentro da meta" ou
  "abaixo da meta".
- **Tabela por gestor:** HC, dias úteis, horas/dia e faltas (em dias
  inteiros) são digitados por semana ou por ciclo. O que não foi
  digitado aparece esmaecido e é herdado (ver
  [5.4](#54-presenteísmo)). A linha **TOTAL CONSOLIDADO** soma tudo.
- **Gestores:** "+ Adicionar Gestor" (nome e operação). Cada gestor tem
  os ícones de **editar** (mudar nome e/ou operação) e **excluir**.
- **Ver no Início:** vai para a aba Início da operação.
- **Como o número foi calculado:** a fórmula e a memória de cálculo
  (horas disponíveis, perdidas, efetivas, resultado e meta).

### 4.7 Coverage

Quanto das horas que cada pessoa deveria trabalhar aparece no LMS.

- **Filtros:** operação (ou "Todas as Operações"), mês, semana e
  Semanal / Resultado do Mês. As semanas são as extraídas em Week (com
  User ID); o Resultado do Mês é a extração Month.
- **Cards:** operação, período, Horas LMS (com o número de usuários),
  Horas Metrics e o Coverage do total.
- **Tabela por usuário:** User ID, operação, Horas LMS, Diretas sem
  meta, **Dias** e **Horas** (digitáveis), Horas Metrics e o Coverage.
  Com muitos usuários, só a lista rola; filtros, cards, cabeçalho e
  total ficam parados.
- **Para todos:** aplica Dias ou Horas em todos os usuários da tela de
  uma vez (útil em semana com feriado).
- **Linha TOTAL:** soma das colunas e o Coverage do total. A
  **Sinergia cedida** e a **Sinergia recebida** da operação são
  digitadas aqui, em horas (a visibilidade da sinergia é por operação,
  não por pessoa).
- O que é digitado fica guardado à parte e **sobrevive a uma nova
  extração** do mesmo período.

### 4.8 Configurações

- **Pasta do SharePoint:** mostra a pasta atual e permite trocar.
- **Gerar diagnóstico:** cria um zip para mandar ao suporte (ver
  [Suporte](#10-suporte-e-diagnóstico)).

### 4.9 Rodapé do menu

Status do sistema, "DHL — Excellence. Simply delivered.", **Criado por
Daniel Thomaseto** e a versão (passando o mouse, a data do build).

---

## 5. Os indicadores e como são calculados

### 5.1 Metas e cores

Iguais para as 12 operações:

| Indicador | Meta | Verde | Vermelho | Azul |
|---|---|---|---|---|
| **CUBO** | 85,00% | 85% a 100% | abaixo de 85% | acima de 100% |
| **EFETIVIDADE** | 90,00% a 110,00% | 90% a 110% | abaixo de 90% | acima de 110% |
| **HORA DIRETA** | 85,00% | 85% ou mais | abaixo de 85% | — |
| **PRESENTEÍSMO** | 98,00% | 98% ou mais | abaixo de 98% | — |
| **DISPERSÃO** | 70,00% | 70% ou mais | abaixo de 70% | — |
| **COVERAGE** | 92,00% | 92% a 110% | abaixo de 92% | acima de 110% |

As metas e faixas ficam num só lugar (`indicators/limits.py`): mudar
uma meta não exige mexer em cálculo nem em tela.

### 5.2 Efetividade, Hora Direta e Dispersão (vêm do Summary)

Calculados a partir das colunas do export, somadas no período. As
colunas são achadas **pelo título**, não pela letra (a posição muda
entre o export semanal e o mensal).

| Indicador | Fórmula |
|---|---|
| **EFETIVIDADE** | soma de `Goal` ÷ soma de `Measured Direct` |
| **HORA DIRETA** | (`Measured Direct` + `Unmeasured Signon Direct` + `Unmeasured Insert Direct`) ÷ (`Total` − `PD Brk`) |
| **DISPERSÃO** | linhas DENTRO ÷ (DENTRO + FORA) |

Classificação de cada linha (pessoa) para a dispersão:

```
se Goal = 0 ou Measured Direct = 0  -> ignorada (sai só da dispersão)
senão, se Var > 10 ou Var < -10     -> FORA
senão                               -> DENTRO
```

`Var` já vem calculado pelo relatório. A dispersão depende do detalhe
por **User ID**; com outro agrupamento ela perde o sentido.

Conferido contra a planilha de referência (semana 36): Efetividade
96,38%, Hora Direta 85,37%, Dispersão 81,82% (9 de 11) — iguais.

O **mês** vem de uma extração própria (Month), não da soma das semanas.

### 5.3 Cubo

```
CUBO = EFETIVIDADE × HORA DIRETA × PRESENTEÍSMO
```

Só aparece quando os três existem. É o primeiro indicador da tela: é o
número que resume os outros. Por ser um produto de três percentuais,
fica abaixo de cada um deles.

### 5.4 Presenteísmo

Calculado a partir do quadro digitado na aba Headcount:

```
Presenteísmo = 1 − (Faltas × Horas/Dia) ÷ (HC × Dias Úteis × Horas/Dia)
```

O total da operação soma as horas de todos os gestores (não é a média
dos percentuais).

**Cada período tem os seus números.** HC, dias úteis, horas/dia e
faltas são guardados por gestor em cada semana do mês e em cada ciclo
da folha. O que não foi digitado no período vem de:

| Campo | Sem valor digitado no período |
|---|---|
| HC | último HC digitado numa semana (ou ciclo) anterior; senão, o do cadastro |
| Horas/dia | idem |
| Dias úteis | o calendário do período (com os sábados da escala espanhola) |
| Faltas | zero |

Mudar o HC numa semana vale dali para a frente, nas semanas sem valor
próprio; as anteriores não mudam. Apagar o campo volta a herdar.

**Como chega na aba Início** (calculado na hora, toda vez que a tela
abre — não há botão de "gravar"):

- **Semana do Summary:** cada dia útil da semana do Summary cai numa
  semana do Headcount, e é dela que vêm os números. Na virada do mês a
  semana tem dois pedaços e eles somam (ex.: 31/08 a 06/09 = última
  semana de agosto + S1 de setembro). Funciona tanto para operações
  cuja semana do Summary começa no domingo (ABB) quanto na segunda.
- **Mês:** o ciclo da folha que **fecha no dia 12 daquele mês**
  (Outubro = 13/09 → 12/10; Setembro = 13/08 → 12/09). O mesmo valor vai
  para a coluna **Pico** do mês e entra no Cubo das duas, mesmo que o
  mês tenha só alguns dias extraídos. Ciclo sem HC próprio usa o último
  valor digitado nas semanas até o fim do ciclo.
- **Ciclo em aberto:** conta os dias úteis do dia 13 **até ontem** — o
  dia de hoje ainda não fechou e não entra. Ex.: em 05/10 conta de 13/09
  a 02/10 (15 dias úteis); na semana seguinte, até 09/10; e assim até
  fechar no dia 12.
- Semana ou ciclo **sem falta lançada conta como zero falta (100%)**.
  Semana que ainda não começou, ou operação sem gestor com HC, fica sem
  número.

### 5.5 Coverage

```
Coverage = (Horas LMS − Diretas sem meta) ÷ (Horas Metrics + Sinergia recebida − Sinergia cedida)
```

| Campo | De onde vem |
|---|---|
| User ID | 2º nível da extração Week; 1º nível da Month |
| Horas LMS | coluna `Total` do export |
| Diretas sem meta | coluna `Unmeasured Signon Direct` |
| Dias | dias úteis do período extraído (com os sábados da escala espanhola); digitável |
| Horas | 8,75 por dia; digitável |
| Horas Metrics | Dias × Horas |
| Sinergia cedida / recebida | da operação, digitadas em horas na linha TOTAL |

O **total** aplica a fórmula sobre as **somas** das colunas (nunca a
média dos percentuais). A linha COVERAGE da aba Início recebe o total
da operação em cada semana e no mês.

### 5.6 Hora Direta de Pico (coluna "Pico")

Extração **Dias de Pico**: o mesmo Summary com Group By 1 = Report Date
(uma linha por dia) do mês do calendário.

1. Calcula a hora direta de **cada dia** (mesma fórmula da 5.2).
2. Pega os **5 dias de maior hora direta** entre os dias válidos.
3. A hora direta de pico é **agregada**: soma das horas dos 5 dias
   dividida uma vez só (não é a média das porcentagens).

**Dias válidos:** segunda a sexta; nas operações de escala espanhola,
também os dois últimos sábados do mês. Domingo e sábado fora da escala
nunca entram (é hora extra, e hora extra não entra).

Na aba Início, a coluna **Pico** fica à direita do mês:

- **Hora Direta** = a do pico;
- **Efetividade, Dispersão e Presenteísmo** = os do mês;
- **Cubo do pico** = EF do mês × HD do pico × PRES do mês;
- **Coverage** não se aplica (fica em branco).

Passando o mouse no título da coluna aparecem os 5 dias usados.

### 5.7 Distribuição da dispersão

Gráfico do mês na aba Início, feito com a **extração Month** (com User
ID) e com **a mesma regra do indicador Dispersão**: só entram as pessoas
com `Goal` e `Measured Direct` diferentes de zero, e a faixa verde é
exatamente o DENTRO (verde ÷ total = a Dispersão do mês).

| Faixa de Var | Cor | Meta |
|---|---|---|
| `<-15` | vermelho | 0 |
| `>=-15 <-10` | amarelo | total × 0,15 |
| `>=-10 <=10` | verde | total × 0,7 |
| `>10 <=15` | amarelo | total × 0,15 |
| `>15` | vermelho | 0 |

O **total** é a soma das pessoas das cinco faixas (como o `$R$17` da
planilha). A meta é em pessoas inteiras: na **verde**, o mínimo para
chegar a 70%, arredondado **para cima** (2 pessoas: 1,4 → 2; 9 pessoas:
6,3 → 7); nas **amarelas**, o máximo aceito, arredondado **para baixo**
(9 pessoas: 1,35 → 1). A curva laranja é a meta, com o número
da faixa verde no topo. Embaixo do gráfico, a tabela Pessoas × Meta.

Mês extraído antes deste gráfico existir não tem a contagem por faixa:
o quadro pede para extrair o mês de novo. Não aparece no modo
apresentação.

---

## 6. Regras de calendário

| Regra | Como funciona |
|---|---|
| **Semana do Summary** | a data que vem no export (algumas operações começam no domingo, outras na segunda). O número (Week 36, 37…) é só rótulo, igual ao `WEEKNUM` do Excel |
| **Semana do Headcount** | segunda a domingo, cortada na virada do mês (S1, S2…) |
| **Ciclo da folha** | do dia 13 de um mês ao dia 12 do seguinte; pertence ao mês em que fecha (13/09 → 12/10 = Outubro). Em aberto, conta até ontem |
| **Dia útil** | segunda a sexta |
| **Escala espanhola** | Nike/Fisia, Rede, JCB e HPE: os **dois últimos sábados de cada mês** também são dia útil (no presenteísmo, no coverage e nos dias de pico). Cada ciclo 13→12 ganha 2 dias (ex.: 13/09 → 12/10/2026 tem 21 dias úteis na escala normal e 23 na espanhola) |
| **Domingo** | nunca é dia útil |

---

## 7. Onde ficam os dados

Tudo fica **no próprio computador**, em `%APPDATA%\ScoreCard\`:

| Arquivo | O que guarda |
|---|---|
| `settings.json` | só o caminho da pasta do SharePoint |
| `history.json` | histórico das extrações (últimas 200) |
| `indicators.json` | indicadores calculados, por operação e período |
| `headcount.json` | gestores e o quadro de cada período (HC, dias, horas, faltas) |
| `coverage.json` | horas por usuário das extrações e o que foi digitado no Coverage |
| `logs\scorecard.log` | registro do que o app fez (até 1 MB, com 3 cópias antigas) |

- Os arquivos são gravados de forma **segura**: primeiro num arquivo
  temporário e só depois trocados de uma vez. Se o PC desligar no
  meio, fica o arquivo antigo inteiro — nunca um pedaço.
- Os relatórios baixados ficam na pasta do SharePoint, em
  `<pasta>\<operação>\Week|Month|Dias de Pico\`.
- O app descompactado fica em `%LOCALAPPDATA%\ScoreCard\app-<versão>`
  (a versão anterior é apagada ao abrir uma nova).
- Os dados são **por computador**: cada pessoa que usa o app tem os
  seus lançamentos de Headcount e Coverage.

---

## 8. Segurança

- **Usuário e senha nunca são gravados:** não ficam no código, em
  arquivo de configuração, em log nem em cache. Ficam só na memória
  enquanto o app está aberto e somem ao fechar ou ao clicar em Sair.
- O **log** passa todo texto por um filtro que troca usuário e senha
  por `***`, caso apareçam numa mensagem de erro do navegador.
- O **diagnóstico** não leva credenciais nem dados de pessoas (nomes de
  gestores, matrículas, faltas): dos arquivos de dados vão só tamanhos
  e contagens.
- O mesmo `.exe` serve para todo mundo: cada pessoa digita a própria
  credencial.

---

## 9. Distribuição, versão e build

### 9.1 O que se distribui

Um arquivo só: **`ScoreCard.exe`**. Quem usa não precisa de Python nem
de internet (o navegador da automação vai embutido). Precisa apenas de:

- Windows 10/11 com o **Microsoft Edge WebView2 Runtime** (já vem no
  Windows atualizado);
- **VPN da DHL** conectada na hora de extrair;
- a **pasta do SharePoint** sincronizada no computador.

Em Propriedades > Detalhes do `ScoreCard.exe` aparecem o nome, a versão
e o autor.

### 9.2 Número da versão

Formato **V.01.0**, guardado no arquivo `VERSAO`. A cada atualização
sobe o último dígito (V.01.1 … V.01.9) e depois vira a dezena (V.02.0).
A versão aparece no rodapé do app.

### 9.3 Gerar uma versão nova (numa máquina Windows)

```bat
git pull origin claude/scorecard-hugo-boss-automation-0hme3g
python tools/subir_versao.py      :: só quando for uma versão nova
build.bat
```

O `build.bat` cria o ambiente Python, instala as dependências, baixa o
Chromium, empacota com o PyInstaller e junta tudo em
`dist\ScoreCard.exe`.

**Como o arquivo único abre rápido:** o `ScoreCard.exe` é um lançador
pequeno com o app inteiro guardado dentro. Na primeira abertura de cada
versão ele descompacta o app em `%LOCALAPPDATA%\ScoreCard\app-<versão>`;
nas seguintes, só abre. Se a descompactação for interrompida, a próxima
abertura refaz.

---

## 10. Suporte e diagnóstico

- **Gerar diagnóstico** (Configurações): cria um zip na pasta Downloads
  com o log, a versão, o ambiente (Windows, pastas, Chromium) e as
  últimas extrações — sem credenciais nem dados de pessoas. É esse
  arquivo que se manda para quem dá suporte.
- **Erro na tela:** aparece um aviso no canto e o erro vai para o log.
- **Extração com falha:** o botão "ver print" mostra a tela do
  BlueYonder no momento do erro.
- **Sem VPN:** a extração para antes de abrir o navegador, com a
  mensagem "Sem conexão com o servidor da operação… confira a VPN".

---

## 11. Arquitetura técnica

**Tecnologias:** Python, **pywebview** (janela com interface
HTML/CSS/JavaScript, via WebView2), **Playwright** com Chromium
embutido (automação do BlueYonder), **xlrd/openpyxl** (leitura do
export .xls/.xlsx) e **PyInstaller** (empacotamento).

```
ScoreCard.exe (lancador.py)
  └─ descompacta uma vez e abre o app
       main.py ─ cria a janela (pywebview) ─ ui/ (index.html, app.js, style.css)
          │
          api.py ─ tudo o que a tela chama
             ├─ automation/   extração no BlueYonder (Playwright)
             ├─ indicators/   leitura do export e cálculos
             └─ *_store.py    gravação dos dados em %APPDATA%
```

| Arquivo / pasta | Papel |
|---|---|
| `lancador.py` | o `ScoreCard.exe`: descompacta o app uma vez e abre |
| `instancia_unica.py` | uma janela só: a segunda abertura traz a primeira |
| `main.py` | cria a janela, confere o Chromium, aviso ao fechar |
| `api.py` | métodos chamados pela tela (login, extração, telas, lançamentos) |
| `automation/base.py` | login, menu Reports, filtros, exportação |
| `automation/generic.py` | orquestra o fluxo de uma operação |
| `indicators/reader.py` | lê o export pelo título das colunas |
| `indicators/weekly.py` | Efetividade, Hora Direta e Dispersão |
| `indicators/limits.py` | metas, faixas de cor e formato dos percentuais |
| `indicators/presenteismo.py` | calendário, escala espanhola e a fórmula |
| `indicators/pico.py` | hora direta dos 5 dias de pico |
| `indicators/coverage.py` | coverage por usuário e total |
| `indicators/periodos.py` | semanas, meses e rótulos |
| `headcount.py` / `headcount_store.py` | tela e dados do Headcount |
| `coverage_tela.py` / `coverage_store.py` | tela e dados do Coverage |
| `indicators_store.py` / `history_store.py` / `settings_store.py` | indicadores, histórico e configurações |
| `arquivo_seguro.py` | gravação dos JSON sem corromper |
| `registro.py` | log com filtro de credenciais |
| `conexao.py` | checagem da VPN antes de extrair |
| `diagnostico.py` | zip de diagnóstico |
| `versao.py` / `VERSAO` | número da versão e detalhes do .exe |
| `config/operations.py` | cadastro das 12 operações |
| `build.spec` / `build.bat` / `tools/` | build, empacotamento e subir versão |

---

## 12. Testes

São cerca de 200 testes automáticos (`tests/`). Eles rodam a extração
contra páginas que imitam o BlueYonder, conferem cada cálculo contra as
planilhas de referência (Efetividade 96,38%, Hora Direta 85,37%,
Dispersão 81,82%, Pico 96,57%/96,82%, Coverage) e cobrem presenteísmo,
calendário, gravação, lançador, log e segurança.

```bat
pip install -r requirements-dev.txt
python -m pytest -q tests
```

---

## 13. Limites conhecidos e próximos passos

**Limites atuais**

- **Planilha de ausências desligada:** as faltas são digitadas. O
  código de importar a planilha continua no projeto, desligado
  (`FALTAS_DA_PLANILHA = False` em `headcount.py`), para uma versão
  futura.
- **Dados por computador:** cada pessoa tem os seus lançamentos de
  Headcount e Coverage; não há base compartilhada.
- **Coverage precisa de extração nova:** extrações feitas antes da aba
  Coverage não guardavam as horas por usuário.
- **Validado em ambiente de teste:** a checagem final (janela única,
  aviso ao fechar, tela cheia, detalhes do .exe) é feita no Windows
  após o build.

**Ideias para próximas versões**

- Aba própria para a **hora direta de pico por hora** (já levantada
  como próximo passo).
- Religar a importação da planilha de ausências.
- Cópia diária automática dos dados, atalhos de teclado entre abas e
  explicação das fórmulas ao passar o mouse nos indicadores.

---

## 14. Histórico do projeto

| Data | Marco |
|---|---|
| 28/07/2026 | Início: automação do login e da extração do Summary (Hugo Boss) |
| 04/08/2026 | Versão em Python com as operações cadastradas e login por pessoa |
| 05/08/2026 | Vira aplicativo desktop (.exe), sem nuvem, com o Chromium embutido |
| 21/08/2026 | Empacotamento em arquivo único |
| 15 a 17/09/2026 | Período específico, Group By na tela, menu lateral, visual DHL, tela de login |
| 20 e 21/09/2026 | Week/Month em subpastas, aba Extrair Múltiplos, abrir pasta, print do erro, atalhos de data, parar fila |
| 23 e 24/09/2026 | Regras dos indicadores fechadas; cálculo de Efetividade, Hora Direta e Dispersão; aba Início |
| 25/09/2026 | Cópia por coluna para o PowerPoint; Headcount e Presenteísmo; Dias de Pico; escala espanhola |
| 26/09/2026 | Versão no rodapé, diagnóstico, checagem de VPN, revisão de design; editar/excluir gestor |
| 28/09/2026 | Faltas digitadas por semana/ciclo; versão V.01.0; Início de um mês por vez |
| 29/09/2026 | Aba Coverage; percentuais com duas casas; janela única, aviso ao fechar, modo apresentação, telas vazias com "Extrair agora"; pente fino de layout |
| 30/09/2026 | **V.01.0 fechada para apresentação** e este documento |
| 05/10/2026 | Gráfico de distribuição da dispersão do mês na aba Início |
| 05/10/2026 | **V.01.1:** correção do erro ao digitar dias úteis no Resultado do Mês; o ciclo da folha passa a ir para o mês em que fecha (e para o Pico); ciclo em aberto conta até ontem; cópia para o PowerPoint numa linha só por célula |

---

*Score Card · DHL — Excellence. Simply delivered. · Criado por Daniel Thomaseto*
