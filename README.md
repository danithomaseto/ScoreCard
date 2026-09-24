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
5. Empacota tudo com o PyInstaller em modo **arquivo unico**.

Comando equivalente, se preferir rodar direto:
```powershell
pyinstaller build.spec --noconfirm
```

Ao final, o executavel fica em **`dist\ScoreCard.exe`** — um arquivo
so, sem mais nada junto. E esse arquivo que voce distribui.

> **Sobre o modo arquivo unico:** o Chromium usado pela automacao vai
> embutido dentro do `.exe` (evita depender de download na maquina de
> quem for usar). Isso deixa o arquivo grande (varias centenas de MB)
> e faz o programa demorar um pouco mais pra abrir — a cada abertura, e
> nao so na primeira vez, o Windows precisa descompactar tudo numa
> pasta temporaria antes de iniciar. Pra um uso semanal (abre, roda a
> extracao, fecha), esse tempo extra de abertura e um bom compromisso
> em troca de nao precisar instalar nada na maquina de quem usa.

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
- Nunca sao escritos em disco, nem em log, nem em cache. O unico
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
api.py                # metodos chamados pelo JS (login, executar, config)
settings_store.py     # persiste a pasta do SharePoint em %APPDATA%
history_store.py      # historico das extracoes em %APPDATA%
indicators_store.py   # indicadores calculados, por operacao e periodo
automation/
  base.py              # login, iframe, comboboxes, export (Playwright)
  generic.py            # orquestra o fluxo por operacao
indicators/
  reader.py             # le o xlsx baixado pelo titulo das colunas
  weekly.py             # o calculo em si, sem I/O
  limits.py             # metas, faixas de cor e tolerancia
  periodos.py           # numero da semana e rotulos de periodo
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
  test_api.py            # extracao unica, fila multipla e validacoes
requirements.txt
requirements-dev.txt      # o de cima + pytest
build.spec               # config do PyInstaller (modo arquivo unico)
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
