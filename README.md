# Score Card - Automacao

Automatiza a montagem semanal do Score Card: uma interface web local deixa
escolher a Operacao, faz login no portal de origem (BlueYonder/RP),
navega ate o relatorio, aplica os filtros (Last Week / User ID) e exporta
o Excel direto para a subpasta da operacao dentro da pasta do SharePoint
sincronizada via OneDrive.

## Operacoes cadastradas

Todas cadastradas em `config/operations.py`, usando o mesmo fluxo de
automacao (`automation/generic.py` + `automation/base.py`):

Hugo Boss, Hughes, Swa, Nike/Fisia, Sumup, Rede, JCB, Lego, SpaceX, HPE,
Armani, ABB.

## Configuracao

1. Instale as dependencias:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. Copie `.env.example` para `.env` e preencha as credenciais reais:
   ```bash
   cp .env.example .env
   ```
   O arquivo `.env` **nunca** deve ser commitado (ja esta no
   `.gitignore`) — ele guarda usuario e senha em texto puro.
3. Confirme que a pasta do SharePoint esta sincronizada via OneDrive no
   seu computador (deve aparecer como uma pasta normal no Explorador de
   Arquivos). O caminho base esta fixo em
   `automation/generic.py` (`SHAREPOINT_BASE_DIR`) — ajuste se o caminho
   na sua maquina for diferente.
4. Conecte na VPN da DHL (os portais sao internos).
5. Rode a aplicacao:
   ```bash
   python app.py
   ```
6. Acesse `http://localhost:5000`, escolha a operacao e clique em
   "Executar login".

## Onde o relatorio e salvo

Cada operacao salva na sua subpasta dentro de:
```
<SHAREPOINT_BASE_DIR>/<sharepoint_folder da operacao>
```
Ex.: `.../CLM GESTÃO CONJUNTA - Automação Score/Hugo Boss/`. Para forçar
todas as operações a salvarem num único lugar fixo (útil para testes),
defina `DOWNLOAD_DIR` no `.env`.

Em caso de falha, um screenshot da tela no momento do erro é salvo em
`screenshots/` (fora do controle de versão), para ajudar a diagnosticar.

## Adicionando uma nova operacao

1. Adicione uma entrada em `config/operations.py` com `label`,
   `login_url`, `sharepoint_folder` e os demais parametros (todos
   seguem o mesmo padrao das operacoes existentes).
2. A operacao aparece automaticamente no dropdown — nao precisa criar
   nenhum arquivo novo, `automation/generic.py` funciona para todas.

## Estrutura do site (BlueYonder RP)

A area de relatorios roda dentro de um `<iframe>` cujo nome muda a cada
sessao (contém um token/timestamp); por isso o codigo localiza o frame
por um trecho fixo do nome (`reporting-ReportOpr`) em vez do nome
completo. Os campos "Date Range" e "Group By 1" sao comboboxes que só
reagem a digitação real (tecla por tecla), não a `fill()` direto — ver
`select_combobox` em `automation/base.py`.

## Proximo passo (painel web)

A ideia e evoluir para um painel hospedado (Vercel) acessivel de
qualquer lugar, com um agente local (rodando numa maquina com VPN da
DHL) processando as extracoes em segundo plano. Este repositorio, por
enquanto, e a versao local (Flask) que ja funciona ponta a ponta.
