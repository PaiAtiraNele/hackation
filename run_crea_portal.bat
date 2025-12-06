@echo off
setlocal
REM Windows helper to run the CREA Connect AI portal CLI.
REM It forwards all arguments to the Python module entrypoint.

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%Review CREA Connect AI project

if not exist "%PROJECT_DIR%" (
    echo [ERRO] Diretório "Review CREA Connect AI project" nao encontrado ao lado deste .bat.
    exit /b 1
)

pushd "%PROJECT_DIR%" >nul
python -m review_crea_connect_ai.examples.cli_portal %*
set EXITCODE=%ERRORLEVEL%
popd >nul
exit /b %EXITCODE%
