# Score Card - Aplicativo Desktop

[![Testes](https://github.com/danithomaseto/ScoreCard/actions/workflows/testes.yml/badge.svg)](https://github.com/danithomaseto/ScoreCard/actions/workflows/testes.yml)

> **Documento completo da ferramenta** (uso, indicadores, regras, dados,
> segurança, build e histórico): [`docs/SCORECARD.md`](docs/SCORECARD.md).

Versao 100% local do Score Card: sem Vercel, sem Supabase, sem servidor
nenhum. Distribuido como **um unico arquivo `ScoreCard.exe`** — quem
recebe so precisa desse arquivo, nada de Python, pip, Node.js, nem
pastas do projeto. Roda como um programa desktop de verdade (janela
nativa, sem barra de navegador), usando
[pywebview](https://pywebview.flowrl.com/) pra mostrar a interface
(HTML/CSS/JS) com um backend em Python.

## Como funciona

1. Tela de login: cada pessoa entra com o **seu proprio** usuario/senha
   do Summary (nada fixo no codigo, nunca gravado em disco — so fica na
   memoria enquanto o programa esta aberto).
2. Na primeira vez, pede pra selecionar a pasta do SharePoint/OneDrive
   onde os relatorios vao ser salvos — fica guardado localmente
   (`%APPDATA%\ScoreCard\settings.json`, so o caminho da pasta, nunca
   credenciais), nao precisa selecionar de novo nas proximas vezes. Da
   pra trocar depois em Configuracoes.
3. Escolhe a operacao, clica em Executar — a automacao roda com as
   credenciais informadas, e salva o relatorio na subpasta daquela
   operacao dentro da pasta configurada.

Detalhes de uso:

- **Uma janela so.** Abrir o `ScoreCard.exe` de novo com o app ja aberto
  nao abre outra janela: traz a que esta aberta para a frente. Duas
  janelas gravando nos mesmos dados sobrescreveriam uma a outra.
- **Fechar durante uma extracao pede confirmacao**, porque fechar no
  meio deixa o download pela metade. Fora de extracao, fecha direto.
- **Modo apresentacao** (aba Inicio): tela cheia so com a tabela, em
  letra maior. As setas trocam a operacao e Esc sai.
- **Tela sem extracao** (Inicio e Coverage) mostra o botao "Extrair
  agora", que abre Extrair Dados com a operacao ja escolhida.
- **Resultado Gestor e Resultado Turno:** a tabela da aba Inicio, uma por
  gestor (ou turno), das extracoes Gestor/Turno · Week e · Month (pastas
  `Gestor\Week`, `Gestor\Month`, `Turno\Week`, `Turno\Month`). A Week
  sai Week > Supervisor > User ID e leva o gestor para o Coverage.
- **Extrair Multiplos > Varios filtros:** uma operacao e varios tipos de
  extracao (Week, Month, Gestor...) em sequencia.
- **Aparencia:** tema claro ou escuro (botao na barra amarela ou
  Ctrl+Shift+L), densidade compacta e menu recolhido (Ctrl+B ou a alca
  no meio da borda do menu), em Configuracoes. A tecla `?` mostra os
  atalhos de teclado.
- **Pasta compartilhada:** o que qualquer pessoa extrai vai para a pasta
  do SharePoint e aparece para todo mundo; o Headcount e o Coverage
  digitados tambem (um arquivo por operacao em `<operacao>\Lancamentos`).
- **Apresentacao automatica:** no modo apresentacao, o botao Automatico
  (ou a barra de espaco) troca a operacao sozinho, com uma capa entre
  uma e outra, passando so pelas operacoes com dados no mes escolhido
  (com uma so, avisa e fica nela). A tabela se ajusta a altura da tela:
  enche a TV em 1920x1080 e cabe sem rolar num notebook 1366x768, mesmo
  com o Windows em 125%.
- **Procurar (Ctrl+K):** "hughes setembro" abre a Inicio da Hughes em
  setembro; "swa coverage", o Coverage da Swa; "tema", a troca de tema.
- **Imagem:** o botao ao lado do Modo apresentacao copia a tabela da
  Inicio como figura (fundo branco) para colar no PowerPoint; com Shift,
  salva o PNG em Downloads.
- **Dica com a conta:** parando o mouse (ou o foco do teclado) num numero
  da tabela aparece a formula e a conta daquele periodo ("302,0 h ÷
  267,6 h = 112,88%").
- **O que ha de novo e tour:** na primeira vez, um tour de cinco passos
  pela Inicio; a cada versao nova, a janela com as novidades. Os dois
  reabrem em Configuracoes > Ajuda.
- **Mais leve:** a tela le a pasta quando o Windows avisa que ela mudou
  (a leitura a cada 5 min fica de reserva), as telas montadas ficam
  guardadas ate os dados mudarem, o Coverage desenha so as linhas
  visiveis e, com a janela minimizada, animacoes e leituras param.
  **Modo leve** (Configuracoes > Aparencia > Animacoes: Leves) desliga o
  que so enfeita, para notebook fraco, Citrix e projetor.
- **Configuracoes > Saude do sistema:** VPN por servidor, a pasta, os
  relatorios que nao foram lidos (e por que), "Ler a pasta do zero", as
  versoes, os lancamentos compartilhados e o backup.
- **Backup diario** dos dados em `%APPDATA%\ScoreCard\backups` (7 dias),
  com restauracao em Configuracoes.
- **Versao nova:** quem publica uma versao com `tools/publicar_versao.py`
  faz aparecer um aviso no app de todo mundo.

Toda a logica de automacao (login no Summary, navegacao pelo iframe de
relatorios, filtros, exportacao) e a mesma ja validada — o empacotamento
em `.exe` nao mudou nada dessa parte, so a forma como e distribuida.

## Rodando em modo desenvolvimento (sem gerar o .exe)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python main.py
```

## Testes

Os testes rodam a automacao de verdade (Playwright + Chromium) contra
paginas de mock em `tests/fixtures`, que imitam o Summary: login, menu
Reports, iframe de relatorios, filtros e exportacao. Ou seja, da pra
validar uma mudanca sem VPN e sem tocar no sistema real.

```bash
pip install -r requirements-dev.txt
playwright install chromium
pytest
```

Se o seu Chromium estiver em outro lugar, aponte
`PLAYWRIGHT_CHROMIUM_EXECUTABLE` para o executavel antes de rodar.

No GitHub, os testes rodam sozinhos a cada push e pull request
(`.github/workflows/testes.yml`), junto com uma checagem de erros de
codigo no Python (flake8) e no JavaScript da tela (eslint). O selo no
topo deste arquivo mostra se a ultima rodada passou.

## Indicadores

Depois de cada extracao o app le o arquivo que acabou de baixar,
calcula os indicadores e guarda o resultado em
`%APPDATA%\ScoreCard\indicators.json`, por operacao, periodo e semana
(ou mes). A aba **Inicio** mostra esses numeros: os seis indicadores nas
linhas, as semanas nas colunas e o mes no final.

O calculo tem que rodar na hora da extracao porque o proximo download
apaga o arquivo anterior da mesma operacao — quem nao calcular naquele
momento nao calcula mais.

Tres dos seis saem do relatorio: **EFETIVIDADE**, **HORA DIRETA** e
**DISPERSAO**. **PRESENTEISMO** e **COVERAGE** serao digitados a mao, e
o **CUBO** (o produto dos tres primeiros) depende do presenteismo —
entao os tres aparecem como `—` por enquanto, nunca como zero.

**PRESENTEISMO** vem da aba **Headcount**: o quadro (HC, dias uteis e
horas/dia) e as **faltas, em dias**, sao digitados ali, por gestor — na
semana do mes (visao Semanal) ou no ciclo da folha ponto, do dia 13 ao
dia 12 (Resultado do Mes). A leitura da planilha de ausencias esta
desligada por enquanto e volta numa versao futura
(`headcount.FALTAS_DA_PLANILHA`).

Nada precisa ser "aplicado": a aba Inicio **calcula o presenteismo na
hora**, do quadro e das faltas, sempre que abre. Por isso qualquer
mudanca — planilha nova, HC corrigido, gestor ou funcao a mais — ja
aparece la, e o **CUBO** sai sozinho nas semanas que tem efetividade e
hora direta. Cada semana (segunda a domingo, a mesma do Summary) recebe
o valor dela, e o mes e o ciclo da folha que fecha no dia 12 dele
(outubro = 13/09 a 12/10; em aberto, conta ate ontem). So
aparecem as semanas e os meses que vieram do Summary; os outros ciclos
da folha ficam so na aba Headcount.

A planilha so tem linha em dia com falta, entao o periodo que ela cobre
e deduzido — do dia 13 do ciclo da primeira data ate o dia da
importacao — e aparece no card do arquivo. Semana com dia util fora
dessa cobertura fica sem numero: melhor um traco do que um 100%
inventado.

As formulas, as metas e as decisoes de desenho estao em
[docs/INDICADORES.md](docs/INDICADORES.md).

## Gerando o .exe

**Precisa ser feito numa maquina Windows** (o PyInstaller gera o
executavel pro sistema operacional em que ele roda — nao da pra gerar
um .exe a partir de Linux/Mac).

Na pasta do projeto, de duplo-clique em `build.bat` (ou rode pelo
terminal, de qualquer pasta). Ele:
1. Acha o Python (pelo lancador `py`, preferindo o 3.12; sem ele, o
   `python` do PATH).
2. Cria o ambiente virtual `venv` — e refaz, se estiver quebrado ou for
   de uma versao do Python fora da faixa testada.
3. Chama `tools/build.py`, que instala as dependencias e empacota tudo
   com o PyInstaller num **arquivo unico**. Antes de trocar o `dist`, ele
   abre o app gerado com `--autoteste` (confere que nenhum modulo ou
   arquivo da tela ficou de fora do pacote); se falhar, o build para.
   `SCORECARD_BUILD_SEM_AUTOTESTE=1` pula essa conferencia.

**Se der erro:** o build para no passo que falhou e mostra a causa
provavel e o que fazer (Python sem Tcl/Tk, pythonnet que nao instala na
versao do Python, Chromium que nao baixou, proxy/SSL, arquivo preso pelo
ScoreCard.exe aberto, OneDrive ou antivirus, disco cheio). Tudo o que
aparece na tela fica em **`build.log`**, na pasta do projeto — e esse o
arquivo para mandar ao suporte. Um build que falha **nao apaga** o
`dist\ScoreCard.exe` anterior.

**O `dist` fica com um arquivo so:** o PyInstaller trabalha numa pasta
temporaria fora do projeto (`%TEMP%\ScoreCard_build`, ou a de
`SCORECARD_BUILD_TEMP`) — assim o OneDrive nao sincroniza os milhares de
arquivos intermediarios nem prende algum deles. Dali so o `ScoreCard.exe`
vai para o `dist`, e qualquer outra coisa que estiver la (como a pasta
`ScoreCardApp` com o `_internal` de um build antigo) e apagada. Para
mandar a alguem, basta o `dist\ScoreCard.exe` (ou a pasta `dist`
inteira, que so tem ele).

Comando equivalente, se preferir rodar direto (com o venv ativado):
```powershell
python tools\build.py                 # instala as dependencias e gera
python tools\build.py --sem-instalar  # so gera
```

Ao final, o executavel fica em **`dist\ScoreCard.exe`** — um arquivo
so, sem mais nada junto. E esse arquivo que voce distribui. Em
Propriedades > Detalhes dele aparecem o nome, a versao (a do arquivo
`VERSAO`) e o autor.

> **Como o arquivo unico abre rapido:** o `ScoreCard.exe` e um lancador
> pequeno com o app inteiro (Python e interface, e o Chromium na versao completa) guardado
> dentro. Na **primeira abertura de cada versao** ele descompacta o app
> em `%LOCALAPPDATA%\ScoreCard\app-<versao>` — a tela de abertura
> mostra o andamento no rodape — e nas seguintes so abre, sem
> descompactar nada. Mandou uma versao nova? Ela descompacta de novo uma
> vez e apaga a pasta da anterior. Se a descompactacao for interrompida
> (PC desligou), a proxima abertura refaz. Detalhes em `lancador.py`.
>
> **Navegador da automacao:** o `.exe` padrao **nao leva navegador
> proprio** (uns 70 MB, contra uns 180 MB com o Chromium): a extracao usa
> o **Microsoft Edge** que ja vem no Windows, e na falta dele o Google
> Chrome. Para maquina sem nenhum dos dois, gere a versao completa com
> `SCORECARD_BUILD_COM_CHROMIUM=1` (embute o Chromium **headless
> shell**, que fica de reserva). `SCORECARD_BUILD_FULL_CHROMIUM=1` embute
> tambem o Chromium completo, que consegue mostrar a automacao na tela
> (`SCORECARD_HEADLESS=0`, so pra diagnostico). Na maquina,
> `SCORECARD_NAVEGADOR=edge|chrome|chromium` forca um deles; Configuracoes
> > Saude do sistema mostra qual esta sendo usado.

### Pre-requisitos na maquina que gera o .exe

- Python 3.10 a 3.13 (de preferencia o **3.12**), instalado com
  "tcl/tk and IDLE" marcado (o PyInstaller usa o Tcl/Tk na tela de
  abertura do .exe). O pythonnet, de que o pywebview precisa no
  Windows, ainda nao instala no Python mais novo que o 3.13.
- Windows 10/11 com o **Microsoft Edge WebView2 Runtime** (ja vem
  instalado por padrao nas versoes atuais do Windows; se faltar, o
  pywebview avisa e da o caminho pra instalar).

### Pre-requisitos na maquina de quem so vai USAR o .exe

Nenhum — nem Python, nem nada tecnico, nem internet. So o WebView2
Runtime e o Microsoft Edge (os dois ja vem com o Windows atualizado; o
Chrome tambem serve) e, claro, acesso a rede da operacao (VPN) na hora
de rodar a extracao de verdade.

## Log

O app grava o que fez em `%APPDATA%\ScoreCard\logs\scorecard.log`:
abertura, etapas da automacao, extracoes, importacoes e erros com o
detalhe tecnico. Quando algo der errado numa maquina, e esse arquivo que
explica. O tamanho e limitado (1 MB, mais os 3 anteriores). Usuario e
senha nunca entram no log.

Em **Configuracoes > Gerar diagnostico** o app junta o log, a versao e
o ambiente da maquina num zip na pasta Downloads, pronto para mandar a
quem da suporte. Leva so contagens e tamanhos dos dados — nenhum nome de
gestor, matricula, usuario ou senha.

A versao (V.01.0) aparece no rodape da barra lateral, abaixo do nome
do criador; passando o mouse, mostra a data do build e o commit. O
numero fica no arquivo `VERSAO`. Para uma atualizacao nova, rode antes
do build:

```powershell
python tools/subir_versao.py
```

Ele sobe o ultimo digito (V.01.0 -> V.01.1 ... V.01.9) e depois a
dezena (V.01.9 -> V.02.0).

Antes de abrir o navegador, cada extracao confere se o servidor da
operacao responde. Sem VPN, a mensagem aparece em segundos, em vez de
esperar o login dar timeout; na fila, um servidor fora do ar nao e
testado de novo. Se a checagem atrapalhar em alguma rede,
`SCORECARD_SEM_CHECAGEM_VPN=1` desliga.

Os arquivos de dados (`settings.json`, `history.json`,
`indicators.json`, `headcount.json`) sao gravados de forma segura: um
PC que desliga no meio da gravacao deixa o arquivo anterior inteiro, e
nunca um arquivo pela metade.

## Configuracoes / trocar a pasta do SharePoint

Dentro do app, botao **Configuracoes** no topo, depois **Alterar
pasta**. Abre o seletor de pastas nativo do Windows. A pasta e validada
(confere se ainda existe) antes de cada execucao.

## Seguranca das credenciais

- Usuario/senha sao digitados a cada sessao, na tela de login — nunca
  fixos no codigo, no `.spec`, nem em nenhum arquivo de configuracao.
- Ficam guardados **so na memoria** do processo (`api.py`, atributos
  `_username`/`_password` da classe `Api`) enquanto o app esta aberto;
  saem da memoria quando o programa fecha ou quando se clica em Sair.
- Nunca sao escritos em disco, nem em log, nem em cache. Alem de
  nenhum trecho do app registrar credenciais, o log passa todo texto
  por um filtro que troca por `***` o usuario e a senha da sessao, caso
  aparecam dentro de uma mensagem de erro vinda do navegador. O unico
  arquivo persistido (`%APPDATA%\ScoreCard\settings.json`) guarda so o
  caminho da pasta do SharePoint.
- O campo de senha na interface e mascarado (`type="password"`).
- Como o mesmo `.exe` e usado por todo mundo e cada pessoa digita a
  propria credencial, nao ha necessidade de builds diferentes por
  usuario.

## Adicionando uma nova operacao

Mesma coisa de sempre: adicionar uma entrada em `config/operations.py`
com `label`, `login_url`, `sharepoint_folder` e os demais parametros —
aparece sozinha no dropdown, sem precisar mexer em mais nada.

## Estrutura

```
main.py              # cria a janela; --autoteste confere o pacote no build
lancador.py          # o ScoreCard.exe: descompacta o app uma vez e abre
instancia_unica.py   # uma janela so: a segunda abertura traz a primeira
api.py                # metodos chamados pelo JS (login, executar, config)
registro.py           # log local, sem credenciais
versao.py             # versao/data do build, gravada pelo build.spec
diagnostico.py        # zip de diagnostico sem dados pessoais
conexao.py            # checagem rapida do servidor (VPN) antes de extrair
arquivo_seguro.py     # gravacao dos JSON sem corromper no meio
settings_store.py     # persiste a pasta do SharePoint em %APPDATA%
history_store.py      # historico das extracoes em %APPDATA%
indicators_store.py   # indicadores calculados, por operacao e periodo
headcount_store.py    # gestores, quadro e faltas importadas
headcount.py          # monta a tela de Headcount (filtros, cards, linhas)
coverage_store.py     # horas por usuario das extracoes e o digitado no Coverage
coverage_tela.py      # monta a aba Coverage (filtros, cards, linhas, total)
indiretas_store.py    # horas indiretas por operacao e semana
indiretas_tela.py     # monta a aba Horas Indiretas (semanas, cards, tabela)
grupos_store.py       # resultados por gestor e por turno
grupos_tela.py        # monta as abas Resultado Gestor e Resultado Turno
reparo_semanas.py     # acerta semanas gravadas com dia e mes trocados
arquivos_sharepoint.py  # nome com periodo, limpeza e leitura da pasta compartilhada
lancamentos.py        # Headcount e Coverage digitados, compartilhados pela pasta
migracoes.py          # versao dos dados e os consertos do que ja esta gravado
backup.py             # backup diario dos dados e restauracao
atualizacao.py        # aviso de versao nova publicada na pasta do SharePoint
navegadores.py        # Edge, Chrome ou Chromium embutido para a automacao
cache_de_telas.py     # telas montadas guardadas ate os dados mudarem
observador_de_pasta.py  # aviso do Windows quando a pasta do SharePoint muda
explicacoes.py        # a conta de cada indicador, para a dica da tabela
novidades.py          # "O que ha de novo" por versao e o tour do primeiro uso
exportar_imagem.py    # PNG da tabela da Inicio salvo em Downloads
automation/
  base.py              # login, iframe, comboboxes, export (Playwright)
  generic.py            # orquestra o fluxo por operacao
indicators/
  reader.py             # le o xlsx baixado pelo titulo das colunas
  datas.py              # datas dia/mes ou mes/dia (servidor americano)
  weekly.py             # o calculo em si, sem I/O
  limits.py             # metas, faixas de cor e tolerancia
  periodos.py           # numero da semana e rotulos de periodo
  faltas.py             # le a planilha de ausencias e filtra o que conta
  presenteismo.py       # semanas do mes, ciclos 13->12 e a formula
  pico.py               # hora direta dos 5 dias de pico do mes
  coverage.py           # coverage por usuario e total
  grupos.py             # indicadores por gestor e por turno
config/
  operations.py         # cadastro das operacoes
ui/
  index.html             # login + painel + configuracoes
  css/00-tokens.css ... 19-movimento.css
                         # 00 = medidas e cores (tokens); um arquivo por
                         # componente ou aba; no fim animacoes, tema claro,
                         # densidade e movimento (a ordem decide qual
                         # regra vale)
  js/01-base.js ... 15-imagem.js
                         # um arquivo por aba ou assunto; todos dividem o
                         # mesmo escopo e rodam na ordem do numero
tests/
  fixtures/              # paginas de mock e exports de exemplo
  test_automation.py     # fluxo de extracao ponta a ponta
  test_filtros.py        # Group By e Date Range na pagina do relatorio
  test_indicators.py     # calculo conferido contra as planilhas
  test_indicators_store.py  # gravacao e a tabela da aba Inicio
  test_presenteismo.py   # faltas, periodos e o caminho ate o cubo
  test_pico.py           # dias de pico e sabados da escala espanhola
  test_coverage.py       # coverage conferido com a planilha
  test_indiretas.py      # horas indiretas conferidas com a planilha
  test_grupos.py         # gestor, turno, Supervisor na Week e varios filtros
  test_datas.py          # semana e Report Date em dia/mes e mes/dia
  test_sharepoint.py     # nome do arquivo, limpeza e leitura da pasta compartilhada
  test_lancamentos.py    # Headcount e Coverage compartilhados entre duas maquinas
  test_api.py            # extracao unica, fila multipla e validacoes
  test_lancador.py       # app dentro do .exe, descompactado uma vez
  test_infra.py          # gravacao segura e log sem credenciais
  test_instancia_unica.py  # segunda abertura so traz a janela
  test_manutencao.py     # backup, migracoes, aviso de versao e saude da pasta
  test_build.py          # build que nao apaga o dist e o autoteste
  test_navegadores.py    # ordem Edge -> Chrome -> Chromium
  test_cache_de_telas.py # tela guardada ate os dados mudarem
  test_observador.py     # aviso de mudanca na pasta
  test_explicacoes.py    # a conta mostrada na dica de cada indicador
  test_novidades.py      # novidades, tour, imagem da tabela e rodizio da apresentacao
requirements.txt
requirements-dev.txt      # o de cima + pytest
build.spec               # config do PyInstaller (app + lancador)
tools/build.py            # o build passo a passo, com build.log e a causa de cada erro
tools/empacotar.py        # poe o app dentro do lancador, no fim do build
tools/publicar_versao.py  # copia o .exe novo para <pasta>\_ScoreCard (aviso no app)
.github/workflows/testes.yml  # testes e checagens a cada push
build.bat                 # script de build de um clique (Windows)
```

## Dependencias externas (nao ficam dentro do .exe)

Nao podem ser embutidas no executavel — precisam existir na maquina de
quem roda o programa:

- **Microsoft Edge WebView2 Runtime**: exigido pelo pywebview pra
  desenhar a interface. Vem pre-instalado no Windows 10/11 atualizados;
  so precisa instalar manualmente em maquinas bem desatualizadas.
- **VPN da DHL**: o portal do Summary e interno, so acessivel de dentro
  da rede da operacao. Precisa estar conectado antes de clicar em
  Executar.
- **Acesso a pasta do SharePoint/OneDrive**: a pasta escolhida nas
  configuracoes precisa estar sincronizada/acessivel no computador.

- **Microsoft Edge** (ou Google Chrome): o navegador que a automacao
  usa no `.exe` padrao. O Edge vem com o Windows. Para maquina sem
  nenhum dos dois, gere o `.exe` com `SCORECARD_BUILD_COM_CHROMIUM=1`.

Tudo o resto (Python, as bibliotecas, o HTML/CSS/JS da interface) ja vai
embutido dentro do `ScoreCard.exe`.
