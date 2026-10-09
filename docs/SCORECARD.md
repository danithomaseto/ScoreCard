# Score Card — documento completo da ferramenta

**Versão:** V.01.1 · **Criado por:** Daniel Thomaseto · **Atualizado em:** 09/10/2026

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
  e nos dias de pico, para a operação inteira, **por gestor** e **por
  turno**;
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

Dentro da subpasta de cada operação, o arquivo vai para `Week`, `Month`,
`Dias de Pico` ou `Indiretas`, conforme o tipo de extração.

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
- Ao abrir, toca a **animação de abertura** (as faixas da DHL cruzando a
  tela, o logo, as seis barras dos indicadores subindo e o título),
  enquanto o app termina de carregar; ela sobe como uma cortina e o
  login entra.
- A janela abre maximizada.
- **Uma janela só:** clicar no `ScoreCard.exe` com o app já aberto não
  abre outra janela — traz para a frente a que está aberta (inclusive
  se estiver minimizada). Duas janelas gravando nos mesmos dados
  sobrescreveriam uma à outra.

### 4.1.1 Menu, topo e atalhos

- **Menu em grupos:** *Resultados* (Início, Resultado Gestor, Resultado
  Turno, Coverage, Horas Indiretas), *Extração* (Extrair Dados, Extrair
  Múltiplos), *Lançamentos* (Headcount) e *Sistema* (Configurações).
- **Recolher o menu:** o botão à esquerda do logo, na barra amarela (ou
  Ctrl+B), deixa o menu só com os ícones e sobra mais largura para as
  tabelas. Passando o mouse no ícone aparece o nome da aba.
- **Tema claro ou escuro:** o botão de sol/lua na barra amarela (ou
  Ctrl+Shift+L). O claro fica melhor no projetor. O login e a abertura
  continuam escuros (são telas da marca).
- **Atalhos de teclado** (botão do teclado na barra amarela, ou a tecla
  `?`):

  | Atalho | O que faz |
  |---|---|
  | Ctrl+1 … Ctrl+9 | abre as abas do menu, na ordem (1 = Início, 2 = Resultado Gestor…) |
  | Ctrl+E | Extrair Dados, já com a operação da tela aberta |
  | Ctrl+B | recolhe ou abre o menu |
  | Ctrl+Shift+L | tema claro ou escuro |
  | ? | mostra a lista de atalhos |
  | Esc | fecha a lista ou sai do modo apresentação |
  | ← → | trocam a operação no modo apresentação |

- **Avisos no canto:** ao copiar uma coluna ou tabela aparece um aviso no
  canto inferior direito dizendo o que foi copiado ("Copiado: 6 valores
  de Week 37"); erros também aparecem ali.
- As preferências (tema, densidade e menu) ficam guardadas na máquina.

### 4.2 Login

- Entre com **o seu** usuário e senha do Summary. Cada pessoa usa a
  própria credencial.
- A senha fica só na memória enquanto o app está aberto (ver
  [Segurança](#8-segurança)).
- Se o Caps Lock estiver ligado, aparece um aviso embaixo da senha —
  senha errada repetida pode bloquear o usuário no Summary.
- **Animação:** o card entra subindo, com um feixe amarelo girando na
  borda; usuário ou senha em branco/errados fazem o card balançar; login
  aceito confirma o card, uma cortina amarela com o logo da DHL cobre a
  tela e sai revelando o app, que entra por partes (barra do topo, menu
  item a item e o conteúdo).
- Com "reduzir movimento" ligado no Windows (Configurações >
  Acessibilidade > Efeitos visuais), nenhuma animação roda.
- Na primeira vez, o app pede a **pasta do SharePoint** (a pasta
  sincronizada pelo OneDrive onde ficam as subpastas das operações).
  Ela fica guardada e pode ser trocada em Configurações.

### 4.3 Início (o painel)

É a tela principal e a que se apresenta.

- **Filtros:** operação e mês (abre no mês atual), e ao lado a última
  extração da operação. O seletor de mês deixa voltar ao mês anterior —
  no começo do mês é ali que está o fechamento. Os filtros têm o mesmo
  desenho em todas as abas.
- **Colunas:** as semanas extraídas que têm dia no mês (Week 36,
  Week 37…, com as datas), depois o **mês** e, colado nele, o **Pico**.
  Semana que não está completa mostra "semana incompleta"; mês ou pico
  extraído só até parte do mês mostra "mês em andamento".
- **Linhas:** os seis indicadores, nesta ordem: CUBO, EFETIVIDADE, HORA
  DIRETA, PRESENTEÍSMO, DISPERSÃO e COVERAGE, cada um com a meta
  escrita embaixo do nome.
- **Cores:** verde (✓) = dentro da meta, vermelho (▼) = abaixo, azul
  (▲) = acima do teto, traço (—) = ainda sem número. O símbolo vai junto
  da cor para funcionar no projetor, no print em preto e branco e para
  quem não distingue verde de vermelho; a cópia leva só o número. Traço nunca é zero: zero seria um
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

1. **Período do indicador**, em dois grupos:
   - **Operação:** Week, Month, Dias de Pico e Horas Indiretas;
   - **Por gestor e por turno:** Gestor · Week, Gestor · Month,
     Turno · Week e Turno · Month.
2. **Operação.**
3. **Período (datas):** digite a data inicial e final, ou use os
   atalhos **Semana passada** / **Mês passado**. Sem datas, o app usa o
   "Last Week" / "Last Month" do próprio relatório. Com Gestor ou Turno
   escolhido, os atalhos trocam só entre o Week e o Month deles.
4. **Agrupamento:** só o **Month** tem campo para escolher (o Group By 1,
   User ID por padrão). Nos outros o agrupamento é **fixo pelo sistema**
   e o campo vira uma nota em amarelo com o agrupamento e a pasta:

   | Tipo | Group By 1 › 2 › 3 | Pasta da operação |
   |---|---|---|
   | Week | Week › Supervisor › User ID | `Week` |
   | Month | escolhido (User ID) | `Month` |
   | Dias de Pico | Report Date | `Dias de Pico` |
   | Horas Indiretas | Week › Job Code | `Indiretas` |
   | Gestor · Week | Week › Supervisor › User ID | `Gestor\Week` |
   | Gestor · Month | Supervisor › User ID | `Gestor\Month` |
   | Turno · Week | Week › Shift › User ID | `Turno\Week` |
   | Turno · Month | Shift › User ID | `Turno\Month` |

   O **Group By 3** usa o mesmo caminho do 2 no Summary: marca o
   checkbox do painel "Grouping Level 3" e preenche o campo "Group By 3".

   A **Week** passou a sair com o Supervisor no meio: é ele que leva o
   gestor de cada usuário para o Coverage. Os números da operação não
   mudam (ver [5.2](#52-efetividade-hora-direta-e-dispersão-vêm-do-summary)).
5. **Iniciar extração.** O painel "Andamento" mostra as 11 etapas
   (abrir o navegador, login, menu Reports, relatório, período, Group
   By 1, 2 e 3, exportar, salvar) e o percentual. Os níveis de
   agrupamento que não entram no tipo escolhido são desmarcados no
   relatório (ele guarda o que ficou marcado da extração anterior).

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
período, agrupamento, tipo, duração, resultado), com filtros por
operação, tipo e resultado (Concluída, Sem indicador, Falha) e a
contagem do que está na tela.

### 4.5 Extrair Múltiplos (fila)

No topo, ao lado do título, escolhe-se o modo:

- **Várias operações:** um tipo de extração (Week, Month, Gestor ·
  Week…) para várias operações marcadas (há "Selecionar todas" e
  "Limpar").
- **Vários filtros:** **uma** operação e **vários tipos** marcados ao
  mesmo tempo (por exemplo Week, Month, Gestor · Week e Turno · Month),
  com as mesmas datas. A fila do painel "Andamento" mostra um item por
  tipo, com a pasta de cada um. Se o Month estiver marcado, o campo
  "Group By 1 do Month" vale para ele; os outros usam o agrupamento fixo.

Nos dois modos as extrações rodam uma depois da outra, num único
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
- **Nome igual ao do Summary:** ao cadastrar ou editar, o campo do nome
  sugere os supervisores que já vieram do Summary para a operação
  (extrações Week e Gestor · Week). Na tabela, cada gestor mostra
  **✓ no Summary** quando o nome bate (o presenteísmo dele vai para o
  Resultado Gestor) ou **sem par no Summary** quando não bate. Sem
  extração com o Supervisor ainda, não aparece nenhum dos dois.
- **Ver no Início:** vai para a aba Início da operação.
- **Como o número foi calculado:** a fórmula e a memória de cálculo
  (horas disponíveis, perdidas, efetivas, resultado e meta).

### 4.7 Coverage

Quanto das horas que cada pessoa deveria trabalhar aparece no LMS.

- **Filtros:** operação (ou "Todas as Operações"), mês, semana,
  **gestor** e Semanal / Resultado do Mês. As semanas são as extraídas
  em Week; o Resultado do Mês é a extração Month.
- **Coverage por gestor:** o filtro **Gestor** mostra só os usuários
  daquele gestor, e os cards e a linha TOTAL viram o coverage do gestor.
  O gestor de cada usuário vem do Supervisor da extração Week (no
  Resultado do Mês, das semanas extraídas do mês, já que o Month não
  traz o Supervisor). Quem trabalhou com dois supervisores fica com o
  que tem mais horas dele. Com um gestor no filtro, a sinergia da
  operação não entra (ela é da operação inteira). Week extraída antes
  dessa mudança não tem gestor: aparece "Sem gestor na extração".
- **Coluna Gestor** na tabela, ao lado da operação.
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

### 4.8 Horas Indiretas

Quanto das horas de cada semana vai para atividades indiretas (não
produtivas) e quais atividades pesam mais. Só existe a visão **por
semana**: o mês escolhe quais semanas aparecem (as que têm algum dia
nele, como na aba Início).

- **Filtros:** operação (ou "Todas as Operações", que soma a mesma
  semana de todas), mês e semana do mês (a dos cards e dos gráficos;
  abre na mais recente).
- **Extração na própria tela:** operação, De e Até, e o botão
  **Extrair**. O agrupamento é fixo pelo sistema (Week + Job Code) e o
  arquivo vai para a pasta `Indiretas`. As datas já vêm sugeridas para o
  mês escolhido. Uma extração nova substitui as semanas que trouxe e
  mantém as outras.
- **Cards:** operação, período, horas totais, horas indiretas e **%
  Indireta** — em vermelho acima de **15,00%**.
- **Visualização** (canto superior direito):
  - **Semanas** (padrão): um quadro por Week, com horas totais, totais
    indiretas e as atividades **da maior para a menor**, cada uma com
    horas, % e uma barrinha (amarela no maior ofensor);
  - **Barras:** as atividades da semana escolhida com horas, % do total
    e % das indiretas, ao lado da tabela atividade × semana;
  - **Pareto:** barras da semana escolhida, da maior para a menor, com a
    linha do % acumulado das indiretas, e a mesma tabela embaixo.
- **Tabela atividade × semana:** cada célula com horas e %; no fim,
  TOTAL INDIRETAS e % INDIRETA de cada semana. Só o corpo rola.
- **Copiar para o PowerPoint:** cada quadro de semana tem um botão
  **Copiar** (copia horas totais, totais indiretas e as atividades, com
  horas e %, como na planilha), e a tabela atividade × semana tem
  **Copiar tabela**. Mesmo formato da cópia da aba Início: cada valor
  numa célula, fonte de 10 pt, sem quebra de linha.

### 4.9 Resultado Gestor

A mesma tabela da aba Início, **uma por gestor**: os seis indicadores
nas linhas, as semanas do mês nas colunas e o mês no fim, com o botão
**Copiar** em cada coluna (igual ao Início).

- **Dados:** extrações **Gestor · Week** (Week › Supervisor › User ID)
  para as semanas e **Gestor · Month** (Supervisor › User ID) para o
  mês. Os arquivos vão para `Gestor\Week` e `Gestor\Month` da operação.
- **Filtros:** operação e mês.
- **Gestores:** no topo, a lista de gestores que vieram no arquivo, com
  caixas de marcar (como a lista de operações do Extrair Múltiplos),
  "Selecionar todos" e "Limpar". Só os marcados ganham tabela. A
  escolha fica guardada por operação; um gestor novo que aparecer no
  Summary já vem marcado.
- **Nome:** o nome é exatamente o da planilha (coluna B, ex.:
  "ANDRE,RICARDO RODRIGUES"). Quem está sem supervisor aparece como
  "Sem supervisor".
- **Ligação com o Headcount:** o **presenteísmo** (e com ele o **cubo**)
  só entra quando existe no Headcount, na mesma operação, um gestor com
  **o mesmo nome** da planilha. A comparação ignora maiúsculas,
  acentos e espaços (inclusive em volta da vírgula); nome diferente não
  puxa nada. O gestor ligado ganha a marca **HC** na lista e "presenteísmo
  do Headcount" no canto da tabela; o não ligado, "sem o mesmo nome no
  Headcount".
- **Visualização:** **Por gestor** (uma tabela por gestor) ou **Resumo**
  (uma tabela só: os gestores nas linhas e os seis indicadores de um
  período nas colunas, com o período escolhido no seletor; cada coluna
  tem Copiar e há "Copiar tabela" com nomes e valores). Clicar no nome no
  Resumo abre a tabela daquele gestor.
- **Barra de nomes:** em Por gestor, uma barra fixa no topo com o nome de
  cada um leva direto à tabela dele, e tem "Abrir todas" / "Recolher
  todas".
- **Recolher:** cada tabela tem uma seta no canto; recolhida, vira uma
  linha com o nome e os seis indicadores da última coluna (o mês, se já
  foi extraído).
- Ver o cálculo em [5.9](#59-indicadores-por-gestor-e-por-turno).

### 4.10 Resultado Turno

Igual ao Resultado Gestor, uma tabela **por turno** (os turnos que
vieram no arquivo, coluna Shift: ex.: ADM, T1, T2; vazio vira "Sem
turno"). Extrações **Turno · Week** (Week › Shift › User ID) e
**Turno · Month** (Shift › User ID), nas pastas `Turno\Week` e
`Turno\Month`. O turno não tem presenteísmo (o Headcount é por
gestor), então **presenteísmo e cubo não se aplicam** — as células ficam
em branco e a cópia guarda a posição delas, para os outros valores não
mudarem de linha.

### 4.11 Configurações

- **Pasta do SharePoint:** mostra a pasta atual e permite trocar.
- **Aparência:** tema (escuro ou claro), densidade (confortável ou
  compacta — a compacta mostra mais linhas numa tela de notebook) e menu
  lateral (aberto ou recolhido). Só muda a tela, nunca um número.
- **Atalhos de teclado:** a mesma lista da tecla `?`.
- **Gerar diagnóstico:** cria um zip para mandar ao suporte (ver
  [Suporte](#10-suporte-e-diagnóstico)).

### 4.12 Rodapé do menu

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

**Week com o Supervisor no meio.** Quem trabalhou com dois supervisores
na mesma semana vem em duas linhas, cada uma com uma parte das horas.
Para as somas tanto faz; para a dispersão, a pessoa contaria duas vezes.
Por isso, para o resultado da **operação**, as linhas da mesma pessoa
na mesma semana são somadas e o Var é refeito com as horas somadas
(`(Goal ÷ Measured Direct − 1) × 100`, arredondado, a mesma conta do
relatório). Quem tem uma linha só fica exatamente como veio. Conferido
com os exports reais da SWA: Week › Supervisor › User ID e Week › Shift ›
User ID dão exatamente os mesmos números da operação, semana a semana.

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

### 5.8 Horas indiretas

Extração **Week + Job Code** (uma linha por atividade em cada semana).
Mesma lógica da planilha de referência (aba HD), cujas colunas têm as
mesmas letras do export:

| Coluna | Campo do export | Na planilha |
|---|---|---|
| H | `Unmeasured Signon Indirect` | HORAS LOGADAS |
| K | `PD Brk` | BRIEFING |
| L | `Total` | TOTAL |
| M | `UnPd Brk` | REFEIÇÃO |

- **Atividade indireta:** H, K ou M diferente de zero (as outras são
  diretas e não entram).
- **Horas da atividade:** H + K + M.
- **Horas totais da semana:** soma de **L + M** de todas as atividades.
  A refeição (M) não vem no `Total` do relatório; sem somá-la, as horas
  de LUNCH ficariam fora do total.
- **% da atividade** = horas ÷ horas totais; **% Indireta** = soma das
  indiretas ÷ horas totais. Acima de **15,00%** é ruim (vermelho).
- Sempre da maior representatividade para a menor.

Conferido com a planilha, semana de 06/09/2026: **715,26 h** totais,
**135,88 h** indiretas, **19,00%** (LUNCH 9,37%, ISTART 3,66%, MEET
3,14%).

### 5.9 Indicadores por gestor e por turno

As mesmas contas da operação, feitas só com as linhas de cada gestor
(ou turno), uma coluna à direita por causa do nível a mais no export:

| Indicador | Por gestor / turno |
|---|---|
| **EFETIVIDADE, HORA DIRETA, DISPERSÃO** | as fórmulas de [5.2](#52-efetividade-hora-direta-e-dispersão-vêm-do-summary) com as linhas do grupo |
| **PRESENTEÍSMO** | gestor: o do Headcount quando o nome bate (semana do Summary e ciclo da folha do mês, como no Início); turno: não se aplica |
| **CUBO** | EFETIVIDADE × HORA DIRETA × PRESENTEÍSMO (turno: não se aplica) |
| **COVERAGE** | horas LMS dos usuários do grupo ÷ dias × horas de cada um (os digitados na aba Coverage, ou o calendário), sem a sinergia, que é da operação |

Quem trabalhou com dois gestores (ou turnos) no período conta nos dois
para efetividade, hora direta e dispersão (cada linha é o trabalho dele
com aquele gestor). Para o coverage ele fica num só — o que tem mais
horas dele —, senão as horas que ele deveria trabalhar contariam duas
vezes.

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
| `settings.json` | o caminho da pasta do SharePoint, os gestores/turnos escondidos nas abas de resultado e as preferências de tela (tema, densidade, menu) |
| `history.json` | histórico das extrações (últimas 200) |
| `indicators.json` | indicadores calculados, por operação e período |
| `headcount.json` | gestores e o quadro de cada período (HC, dias, horas, faltas) |
| `coverage.json` | horas por usuário das extrações e o que foi digitado no Coverage |
| `indiretas.json` | horas indiretas por operação e semana (da extração Horas Indiretas) |
| `grupos.json` | resultados por gestor e por turno, por operação e período (extrações Gestor e Turno) |
| `logs\scorecard.log` | registro do que o app fez (até 1 MB, com 3 cópias antigas) |

- Os arquivos são gravados de forma **segura**: primeiro num arquivo
  temporário e só depois trocados de uma vez. Se o PC desligar no
  meio, fica o arquivo antigo inteiro — nunca um pedaço.
- Os relatórios baixados ficam na pasta do SharePoint, em
  `<pasta>\<operação>\Week|Month|Dias de Pico|Indiretas\` e
  `<pasta>\<operação>\Gestor|Turno\Week|Month\`.
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
| `indicators/indiretas.py` | horas indiretas por semana (regra da planilha) |
| `indicators/grupos.py` | indicadores por gestor e por turno |
| `grupos_tela.py` / `grupos_store.py` | telas e dados do Resultado Gestor e Resultado Turno |
| `indiretas_tela.py` / `indiretas_store.py` | tela e dados das Horas Indiretas |
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

São cerca de 240 testes automáticos (`tests/`). Eles rodam a extração
contra páginas que imitam o BlueYonder, conferem cada cálculo contra as
planilhas de referência (Efetividade 96,38%, Hora Direta 85,37%,
Dispersão 81,82%, Pico 96,57%/96,82%, Coverage) e cobrem presenteísmo,
calendário, gravação, lançador, log e segurança. As planilhas de teste
com Supervisor e Shift (`summary_gestor_*.xlsx`, `summary_turno_*.xlsx`)
têm nomes fictícios.

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
| 05/10/2026 | Gráfico de distribuição da dispersão do mês na aba Início; aba **Horas Indiretas** (extração Week + Job Code, pasta Indiretas, quadros por semana, Barras e Pareto) |
| 05/10/2026 | **V.01.1:** correção do erro ao digitar dias úteis no Resultado do Mês; o ciclo da folha passa a ir para o mês em que fecha (e para o Pico); ciclo em aberto conta até ontem; cópia para o PowerPoint numa linha só por célula |
| 09/10/2026 | Menu em grupos e recolhível; Resumo, barra de nomes e tabelas recolhíveis no Resultado Gestor/Turno; nomes do Summary sugeridos no Headcount; **tema claro**; símbolos junto das cores; filtros iguais em todas as abas; avisos de "copiado"; atalhos de teclado; densidade compacta; filtro no histórico |
| 08/10/2026 | Abas **Resultado Gestor** e **Resultado Turno** (extrações Gestor e Turno, Week e Month, com Group By 3); Week com o Supervisor no meio e **Coverage por gestor**; **Vários filtros** no Extrair Múltiplos; cópia das Horas Indiretas para o PowerPoint; animações de abertura, login, entrada no app e transições |

---

*Score Card · DHL — Excellence. Simply delivered. · Criado por Daniel Thomaseto*
