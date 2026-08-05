@echo off
REM Gera o ScoreCard.exe. Rode este arquivo dando duplo-clique, ou pelo
REM PowerShell/CMD dentro da pasta do projeto.

echo ============================================
echo  Score Card - gerando o executavel (.exe)
echo ============================================

if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -r requirements.txt

echo Baixando o Chromium (usado pela automacao)...
python -m playwright install chromium

echo Gerando o executavel com o PyInstaller...
pyinstaller build.spec --noconfirm

echo.
echo ============================================
echo  Pronto! O executavel esta em:
echo  dist\ScoreCard\ScoreCard.exe
echo ============================================
pause
