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

echo Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Gerando o executavel com o PyInstaller (arquivo unico)...
pyinstaller build.spec --noconfirm

echo.
echo ============================================
echo  Pronto! O executavel esta em:
echo  dist\ScoreCard.exe
echo  (esse arquivo sozinho ja e o suficiente pra
echo  distribuir - nao precisa de mais nada da
echo  pasta dist junto)
echo ============================================
pause
