# Score Card - Aplicativo Desktop

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
horas/dia) e digitado ali e as faltas vem de uma planilha de ausencias,
que nunca sao digitadas. A planilha e filtrada — ferias nao e falta,
temporario fica de fora e so entram as funcoes que compoem o quadro
(Log I, Log II, Operador, mais as que forem cadastradas na tela para
a operacao do gestor). Cada
falta e roteada pela data para a semana do mes e para o ciclo da folha
ponto (dia 13 ao dia 12) ao mesmo tempo.

Nada precisa ser "aplicado": a aba Inicio **calcula o presenteismo na
hora**, do quadro e das faltas, sempre que abre. Por isso qualquer
mudanca — planilha nova, HC corrigido, gestor ou funcao a mais — ja
aparece la, e o **CUBO** sai sozinho nas semanas que tem efetividade e
hora direta. Cada semana (segunda a domingo, a mesma do Summary) recebe
o valor dela, e o mes e o ciclo da folha que comeca no dia 13. So
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
terminal). Ele:
1. Cria um ambiente virtual Python (se ainda nao existir).
2. Instala as dependencias.
3. Baixa o Chromium (`playwright install chromium`).
4. Limpa builds anteriores (`build/`, `dist/`).
5. Empacota tudo com o PyInstaller e junta num **arquivo unico**.

Comando equivalente, se preferir rodar direto:
```powershell
pyinstaller build.spec --noconfirm
```

Ao final, o executavel fica em **`dist\ScoreCard.exe`** — um arquivo
so, sem mais nada junto. E esse arquivo que voce distribui.

> **Como o arquivo unico abre rapido:** o `ScoreCard.exe` e um lancador
> pequeno com o app inteiro (Python, interface, Chromium) guardado
> dentro. Na **primeira abertura de cada versao** ele descompacta o app
> em `%LOCALAPPDATA%\ScoreCard\app-<versao>` — a tela de abertura
> mostra o andamento no rodape — e nas seguintes so abre, sem
> descompactar nada. Mandou uma versao nova? Ela descompacta de novo uma
> vez e apaga a pasta da anterior. Se a descompactacao for interrompida
> (PC desligou), a proxima abertura refaz. Detalhes em `lancador.py`.
>
> O Chromium embutido e o **headless shell**, a versao feita pra rodar
> sem janela, com mais ou menos metade do tamanho do completo. Para
> gerar um .exe que consiga mostrar a automacao na tela
> (`SCORECARD_HEADLESS=0`, so pra diagnostico), rode o build com
> `SCORECARD_BUILD_FULL_CHROMIUM=1`.

### Pre-requisitos na maquina que gera o .exe

- Python 3.10+ instalado.
- Windows 10/11 com o **Microsoft Edge WebView2 Runtime** (ja vem
  instalado por padrao nas versoes atuais do Windows; se faltar, o
  pywebview avisa e da o caminho pra instalar).

### Pre-requisitos na maquina de quem so vai USAR o .exe

Nenhum — nem Python, nem nada tecnico, nem internet (o Chromium ja vai
embutido). So o WebView2 Runtime (que, de novo, ja vem com o Windows
atualizado) e, claro, acesso a rede da operacao (VPN) na hora de rodar
a extracao de verdade.

## Log

O app grava o que fez em `%APPDATA%\ScoreCard\logs\scorecard.log`:
abertura, etapas da automacao, extracoes, importacoes e erros com o
detalhe tecnico. Quando algo der errado numa maquina, e esse arquivo que
explica. O tamanho e limitado (1 MB, mais os 3 anteriores). Usuario e
senha nunca entram no log.

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
main.py              # cria a janela, garante que o Chromium existe
lancador.py          # o ScoreCard.exe: descompacta o app uma vez e abre
api.py                # metodos chamados pelo JS (login, executar, config)
registro.py           # log local, sem credenciais
arquivo_seguro.py     # gravacao dos JSON sem corromper no meio
settings_store.py     # persiste a pasta do SharePoint em %APPDATA%
history_store.py      # historico das extracoes em %APPDATA%
indicators_store.py   # indicadores calculados, por operacao e periodo
headcount_store.py    # gestores, quadro e faltas importadas
headcount.py          # monta a tela de Headcount (filtros, cards, linhas)
automation/
  base.py              # login, iframe, comboboxes, export (Playwright)
  generic.py            # orquestra o fluxo por operacao
indicators/
  reader.py             # le o xlsx baixado pelo titulo das colunas
  weekly.py             # o calculo em si, sem I/O
  limits.py             # metas, faixas de cor e tolerancia
  periodos.py           # numero da semana e rotulos de periodo
  faltas.py             # le a planilha de ausencias e filtra o que conta
  presenteismo.py       # semanas do mes, ciclos 13->12 e a formula
  pico.py               # hora direta dos 5 dias de pico do mes
config/
  operations.py         # cadastro das operacoes
ui/
  index.html             # login + painel + configuracoes
  style.css
  app.js
tests/
  fixtures/              # paginas de mock e exports de exemplo
  test_automation.py     # fluxo de extracao ponta a ponta
  test_filtros.py        # Group By e Date Range na pagina do relatorio
  test_indicators.py     # calculo conferido contra as planilhas
  test_indicators_store.py  # gravacao e a tabela da aba Inicio
  test_presenteismo.py   # faltas, periodos e o caminho ate o cubo
  test_pico.py           # dias de pico e sabados da escala espanhola
  test_api.py            # extracao unica, fila multipla e validacoes
  test_lancador.py       # app dentro do .exe, descompactado uma vez
  test_infra.py          # gravacao segura e log sem credenciais
requirements.txt
requirements-dev.txt      # o de cima + pytest
build.spec               # config do PyInstaller (app + lancador)
tools/empacotar.py        # poe o app dentro do lancador, no fim do build
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

Tudo o resto (Python, as bibliotecas, o Chromium usado pela automacao,
o HTML/CSS/JS da interface) ja vai embutido dentro do `ScoreCard.exe`.
