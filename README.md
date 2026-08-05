# Score Card - Aplicativo Desktop

Versao 100% local do Score Card: sem Vercel, sem Supabase, sem depender
de internet pra funcionar (so precisa de rede pra acessar o Summary e,
na primeira vez, baixar o Chromium usado internamente). Roda como um
programa desktop de verdade (janela nativa, sem barra de navegador),
usando [pywebview](https://pywebview.flowrl.com/) pra mostrar a
interface (HTML/CSS/JS) com um backend em Python.

## Como funciona

1. Tela de login: cada pessoa entra com o **seu proprio** usuario/senha
   do Summary (nada fixo no codigo).
2. Na primeira vez, pede pra selecionar a pasta do SharePoint/OneDrive
   onde os relatorios vao ser salvos — fica guardado localmente
   (`%APPDATA%\ScoreCard\settings.json`), nao precisa selecionar de novo
   nas proximas vezes. Da pra trocar depois em Configuracoes.
3. Escolhe a operacao, clica em Executar — a automacao roda com as
   credenciais informadas, e salva o relatorio na subpasta daquela
   operacao dentro da pasta configurada.

Toda a logica de automacao (login no Summary, navegacao pelo iframe de
relatorios, filtros, exportacao) e a mesma ja validada nas versoes
anteriores do projeto — nada mudou nesse ponto, so a forma como o
usuario interage com o programa.

## Rodando em modo desenvolvimento (sem gerar o .exe)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python main.py
```

## Gerando o .exe

**Precisa ser feito numa maquina Windows** (o PyInstaller gera o
executavel pro sistema operacional em que ele roda — nao da pra gerar
um .exe a partir de Linux/Mac).

Na pasta do projeto, de duplo-clique em `build.bat` (ou rode pelo
terminal). Ele:
1. Cria um ambiente virtual Python (se ainda nao existir).
2. Instala as dependencias.
3. Baixa o Chromium.
4. Empacota tudo com o PyInstaller.

Ao final, o executavel fica em `dist\ScoreCard\ScoreCard.exe`. Essa
pasta inteira (`dist\ScoreCard`) e o que voce distribui pras outras
pessoas — nao só o `.exe` sozinho, ele precisa dos arquivos ao lado.

### Pre-requisitos na maquina que gera o .exe

- Python 3.10+ instalado.
- Windows 10/11 com o **Microsoft Edge WebView2 Runtime** (ja vem
  instalado por padrao nas versoes atuais do Windows; se faltar, o
  pywebview avisa e da o caminho pra instalar).

### Pre-requisitos na maquina de quem so vai USAR o .exe

Nenhum — nem Python, nem nada tecnico. So o WebView2 Runtime (que,
de novo, ja vem com o Windows atualizado).

## Primeira execucao (para quem usa o .exe)

Na primeira vez que o programa roda, se o Chromium interno ainda nao
estiver presente, ele baixa sozinho antes de abrir a janela (pode
demorar um pouco, dependendo da internet — no momento essa etapa nao
mostra uma mensagem na tela, ja que o executavel roda sem console;
funciona silenciosamente, so demora um pouco mais na primeira vez).

## Configuracoes / trocar a pasta do SharePoint

Dentro do app, botao **Configuracoes** no topo, depois **Alterar
pasta**. Abre o seletor de pastas nativo do Windows.

## Adicionando uma nova operacao

Mesma coisa de sempre: adicionar uma entrada em `config/operations.py`
com `label`, `login_url`, `sharepoint_folder` e os demais parametros —
aparece sozinha no dropdown, sem precisar mexer em mais nada.

## Estrutura

```
main.py              # cria a janela, garante que o Chromium existe
api.py                # metodos chamados pelo JS (login, executar, config)
settings_store.py     # persiste a pasta do SharePoint em %APPDATA%
automation/
  base.py              # login, iframe, comboboxes, export (Playwright)
  generic.py            # orquestra o fluxo por operacao
config/
  operations.py         # cadastro das operacoes
ui/
  index.html             # login + painel + configuracoes
  style.css
  app.js
requirements.txt
build.spec               # config do PyInstaller
build.bat                 # script de build de um clique (Windows)
```
