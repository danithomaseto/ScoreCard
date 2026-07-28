# Score Card - Automacao

Automatiza a montagem semanal do Score Card. Fase atual: interface web para
escolher a Operacao e executar o login automatico no portal de origem dos
dados. Extracao/download do arquivo sera adicionado na proxima etapa.

## Operacoes

Cada operacao tem seu proprio link de login e credenciais, cadastrados em
`config/operations.py`. Hoje so a **Hugo Boss** esta configurada; as demais
serao replicadas depois seguindo o mesmo padrao.

## Configuracao

1. Instale as dependencias:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. Copie `.env.example` para `.env` e preencha usuario/senha reais:
   ```bash
   cp .env.example .env
   ```
   O arquivo `.env` nunca deve ser commitado (ja esta no `.gitignore`).
3. Rode a aplicacao:
   ```bash
   python app.py
   ```
4. Acesse `http://localhost:5000`, escolha a operacao "Hugo Boss" e clique em
   "Executar login".

O resultado (sucesso/erro) aparece na tela, e um screenshot da pagina apos a
tentativa e salvo em `screenshots/` para conferencia.

> Importante: o portal da Hugo Boss fica na rede interna da DHL. Para o login
> funcionar, a maquina que roda esta aplicacao precisa ter acesso a essa rede
> (ex.: VPN corporativa).

## Adicionando uma nova operacao

1. Adicione a entrada em `config/operations.py` com `label`, `login_url` e os
   nomes das variaveis de ambiente de usuario/senha.
2. Adicione essas variaveis no `.env` (e no `.env.example`, sem valores).
3. Crie `automation/<operacao>.py` seguindo o padrao de
   `automation/hugo_boss.py`.
4. A operacao aparece automaticamente no dropdown da interface.
