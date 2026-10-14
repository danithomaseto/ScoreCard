@echo off
REM Gera o ScoreCard.exe. Rode este arquivo dando duplo-clique, ou pelo
REM PowerShell/CMD (de qualquer pasta).
REM
REM O trabalho e feito por tools\build.py: ele para no primeiro erro, diz
REM a causa provavel e grava tudo em build.log. O dist\ScoreCard.exe
REM anterior so e trocado quando o novo fica pronto.

setlocal
cd /d "%~dp0"
title Score Card - gerando o executavel

echo ============================================
echo  Score Card - gerando o executavel (.exe)
echo ============================================
echo.

REM ---- Python: o lancador "py" escolhe uma versao testada; sem ele, o
REM ---- "python" do PATH (que pode ser o atalho da Microsoft Store).
set "PY="
for %%V in (3.12 3.13 3.11 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERRO] Nao encontrei o Python neste computador.
    echo        Instale o Python 3.12 em https://www.python.org/downloads/
    echo        marcando "Add python.exe to PATH" e "tcl/tk and IDLE",
    echo        e rode este arquivo de novo.
    goto erro
)
echo Python escolhido: %PY%

REM ---- Ambiente virtual: refeito se estiver quebrado (Python trocado ou
REM ---- desinstalado) ou se for de uma versao fora da faixa testada.
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe -c "import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo O ambiente virtual ^(venv^) esta quebrado ou e de outra versao do Python: refazendo...
        rmdir /s /q venv
    )
)
if not exist venv\Scripts\python.exe (
    echo Criando o ambiente virtual ^(venv^)...
    %PY% -m venv venv
    if errorlevel 1 (
        echo [ERRO] Nao consegui criar o ambiente virtual com %PY%.
        goto erro
    )
)

venv\Scripts\python.exe tools\build.py %*
if errorlevel 1 goto erro

echo.
echo Na primeira abertura de cada versao o .exe se prepara uma vez;
echo depois abre direto.
pause
exit /b 0

:erro
echo.
echo O executavel NAO foi gerado. A causa provavel esta logo acima e o
echo registro completo em build.log (nesta pasta) - mande esse arquivo
echo para quem da suporte se nao resolver.
pause
exit /b 1
