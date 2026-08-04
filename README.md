# Score Card - Automacao

Automatiza a montagem semanal do Score Card. Duas formas de usar:

- **Painel web** (`panel/`): pagina publicada no Vercel, acessivel de
  qualquer lugar, pra escolher a Operacao, disparar a extracao e
  acompanhar o status/baixar o resultado.
- **App local** (`app.py`): interface Flask rodando so na sua maquina,
  em `http://localhost:5000` — util pra testar sem depender do Vercel.

Em ambos os casos, quem faz o trabalho pesado (login no portal, navegar
ate o relatorio, aplicar filtros, exportar em Excel) e sempre o mesmo
codigo Python (`automation/`), rodando numa maquina com acesso a rede da
operacao (VPN da DHL) — os portais sao internos e nao podem ser
alcancados por um servidor na nuvem.

```
Painel (Vercel, de qualquer lugar) <--> agent.py (sua maquina/VPN) --> Portal da operacao
App local (so na sua maquina)      <--> automation/ (direto, sem painel) --> Portal da operacao
```

## Operacoes cadastradas

Todas em `config/operations.py`, usando o mesmo fluxo de automacao
(`automation/generic.py` + `automation/base.py`): Hugo Boss, Hughes,
Swa, Nike/Fisia, Sumup, Rede, JCB, Lego, SpaceX, HPE, Armani, ABB.

## Configuracao comum (local)

1. Instale as dependencias:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. Copie `.env.example` para `.env` e preencha:
   ```bash
   cp .env.example .env
   ```
   O arquivo `.env` **nunca** deve ser commitado (ja esta no
   `.gitignore`) — guarda usuario/senha em texto puro.
3. Confirme que a pasta do SharePoint esta sincronizada via OneDrive no
   seu computador (deve aparecer como pasta normal no Explorador de
   Arquivos). O caminho base esta fixo em `automation/generic.py`
   (`SHAREPOINT_BASE_DIR`) — ajuste se for diferente na sua maquina.
4. Conecte na VPN da DHL antes de rodar qualquer automacao.

## Opcao 1: usar o painel web

1. **Publicar o painel no Vercel**: importe a pasta `panel/` como
   projeto (em Settings do projeto Vercel, configure "Root Directory"
   = `panel`). Em Storage, crie um **Blob Store** e conecte ao projeto
   (injeta `BLOB_READ_WRITE_TOKEN` automaticamente). Em Environment
   Variables, adicione `APP_TOKEN` (um valor secreto a sua escolha).
2. **Rodar o agente local**: no `.env` (raiz do repo), preencha tambem
   `DASHBOARD_URL` (a URL do projeto Vercel) e `APP_TOKEN` (o mesmo
   valor). Rode:
   ```bash
   python agent.py
   ```
   Ele fica verificando o painel a cada poucos segundos — deixe rodando
   enquanto for usar (nao precisa 24/7).
3. **Usar**: abra a URL do painel no navegador (de onde for), informe o
   token, escolha a operacao e clique em Executar. Quando o agente
   processar, o status muda pra "Concluido" com um link de download.

## Opcao 2: usar so localmente (sem painel)

```bash
python app.py
```
Acesse `http://localhost:5000`, escolha a operacao e clique em
"Executar login". Nao depende do Vercel nem do agente.

## Onde o relatorio e salvo

Em ambas as opcoes, cada operacao salva na sua subpasta dentro de:
```
<SHAREPOINT_BASE_DIR>/<sharepoint_folder da operacao>
```
Ex.: `.../CLM GESTÃO CONJUNTA - Automação Score/Hugo Boss/`. Pelo painel,
o agente tambem envia uma copia pro Vercel Blob, pra aparecer o link de
download no historico. Para forcar tudo numa unica pasta fixa (util pra
testes), defina `DOWNLOAD_DIR` no `.env`.

Em caso de falha, um screenshot da tela no momento do erro e salvo em
`screenshots/` (fora do controle de versao), pra ajudar a diagnosticar.

## Adicionando uma nova operacao

1. Adicione uma entrada em `config/operations.py` com `label`,
   `login_url`, `sharepoint_folder` e os demais parametros (mesmo
   padrao das operacoes existentes).
2. Se for usar o painel, adicione a mesma chave (so com `label`) em
   `panel/api/_lib/operations.js`.
3. Pronto — aparece no dropdown automaticamente, sem precisar criar
   nenhum arquivo novo.

## Estrutura do site (BlueYonder RP)

A area de relatorios roda dentro de um `<iframe>` cujo nome muda a cada
sessao (contem um token/timestamp); por isso o codigo localiza o frame
por um trecho fixo do nome (`reporting-ReportOpr`) em vez do nome
completo. Os campos "Date Range" e "Group By 1" sao comboboxes que so
reagem a digitacao real (tecla por tecla), nao a `fill()` direto — ver
`select_combobox` em `automation/base.py`.

## Limitacoes conhecidas

- O upload do relatorio pro painel passa por uma Vercel Function, com
  limite de ~4.5 MB por requisicao — suficiente pros relatorios atuais.
- O agente processa uma tarefa por vez, em sequencia.
- O agente so funciona enquanto a maquina que roda ele estiver ligada
  (tela travada nao e problema; suspensao/hibernacao, sim).
