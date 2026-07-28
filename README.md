# Score Card - Automacao

Automatiza a montagem semanal do Score Card. Arquitetura 100% web, dividida
em duas partes porque o portal de origem (Hugo Boss) fica na rede interna
da DHL, inacessivel para servidores na nuvem:

- **Painel** (`public/index.html` + `api/`): pagina unica HTML/CSS/JS,
  hospedada no Vercel. Acessivel de qualquer lugar. Deixa escolher a
  Operacao, disparar uma execucao e acompanhar o status/baixar o
  resultado.
- **Agente** (`agent/`): script Node.js que roda numa maquina com acesso a
  rede da operacao (ex.: seu PC conectado na VPN da DHL). Ele fica de olho
  no painel, pega as tarefas pendentes, faz a automacao (login + extracao
  do relatorio via Playwright) e envia o Excel de volta pro painel.

```
Voce (navegador) --> Painel (Vercel) <-- Agente local (sua maquina/VPN) --> Portal Hugo Boss
        |                    ^
        +---- clica Executar-+  (cria tarefa)
        |                    |
        +---- baixa Excel <--+  (agente envia o resultado)
```

## 1. Publicar o painel no Vercel

1. No painel do Vercel, importe este repositorio como um novo projeto
   (Framework Preset: "Other").
2. Em **Storage**, crie um **Blob Store** e conecte ao projeto (isso injeta
   automaticamente a variavel `BLOB_READ_WRITE_TOKEN`).
3. Em **Settings > Environment Variables**, adicione:
   - `APP_TOKEN` = um token secreto qualquer, escolhido por voce (ex.: gere
     com `openssl rand -hex 20`). Ele protege o painel e a API — sem ele,
     ninguem consegue disparar tarefas nem ver o historico.
4. Faça o deploy (push nesta branch, ou `vercel --prod` pela CLI).
5. Acesse a URL publicada. Na primeira vez, ele vai pedir o token — cole o
   mesmo valor de `APP_TOKEN`.

> O token fica salvo no navegador (localStorage). Trate a URL + token como
> informacao sensivel: quem tiver os dois consegue disparar extracoes e
> baixar os relatorios.

## 2. Configurar o agente local

O agente precisa rodar numa maquina com acesso a rede da operacao (para a
Hugo Boss, conectada na VPN da DHL).

```bash
cd agent
npm install
npx playwright install chromium
cp .env.example .env
```

Edite `agent/.env` com os valores reais (veja `agent/.env.example` para o
formato completo):
```
DASHBOARD_URL=https://seu-projeto.vercel.app
APP_TOKEN=<o mesmo APP_TOKEN configurado no Vercel>
HUGO_BOSS_USERNAME=<seu usuario>
HUGO_BOSS_PASSWORD=<sua senha>
```

Rode o agente:
```bash
npm start
```
Ele fica verificando o painel a cada poucos segundos. Deixe essa janela
aberta enquanto for usar o painel (não precisa ficar rodando 24/7 — só
quando quiser executar uma extração).

## 3. Usar

1. Abra o painel no navegador (celular, notebook, de onde for).
2. Escolha a operacao e clique em **Executar**.
3. Com o agente rodando na maquina com VPN, ele pega a tarefa em poucos
   segundos, faz login, aplica os filtros do relatorio (Last Week / User
   ID) e exporta em Excel.
4. Quando o status virar **Concluido** no painel, clique em **Baixar
   Excel**.

Se der erro, o status fica **Falhou** com a mensagem de qual etapa travou,
e um screenshot é salvo em `agent/screenshots/` na maquina do agente, para
ajudar a ajustar a automacao.

## Adicionando uma nova operacao

1. `agent/config/operations.js`: adicione a entrada com `loginUrl` e os
   nomes das variaveis de usuario/senha.
2. Adicione essas variaveis no `agent/.env` (e no `agent/.env.example`).
3. Crie `agent/automation/<operacao>.js` seguindo o padrao de
   `hugoBoss.js`.
4. Registre o runner em `agent/agent.js` (objeto `RUNNERS`).
5. `api/_lib/operations.js`: adicione a mesma chave, só com o `label`
   (isso é o que faz a operacao aparecer no dropdown do painel).

## Limitacoes conhecidas

- O upload do relatorio para o painel passa por uma Vercel Function, que
  tem limite de ~4.5 MB por requisicao. Para os relatorios de resumo
  semanal isso costuma ser suficiente; se um relatorio futuro for maior,
  o upload vai falhar e vamos precisar mudar para upload direto no Blob.
- O agente processa uma tarefa por vez, em sequencia.
