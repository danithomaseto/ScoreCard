# Score Card - Automacao

Automatiza a montagem semanal do Score Card. A interface web deixa escolher
a Operacao e, com um clique, faz login no portal de origem, abre o relatorio
configurado, aplica os filtros e baixa o arquivo Excel direto para a pasta
de destino (por padrao, a Area de Trabalho).

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

O resultado (sucesso/erro) aparece na tela. Em caso de sucesso, o Excel e
salvo direto na pasta de destino (por padrao, a Area de Trabalho do usuario
que esta rodando a aplicacao). Em caso de erro, um screenshot da pagina no
momento da falha e salvo em `screenshots/` para ajudar a diagnosticar.

Para mudar a pasta de destino do arquivo baixado, defina a variavel
`DOWNLOAD_DIR` no `.env` (ex.: `DOWNLOAD_DIR=C:\Users\seu.usuario\Downloads`).

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
