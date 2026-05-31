@echo off
chcp 65001 >nul

REM 小满后端启动脚本
REM 使用 Python 3.14（Alice 系统自带的 Python 3.11 不兼容 LanceDB）

set PYTHON=C:\Python314\python.exe
set SCRIPT_DIR=%~dp0

echo ==========================================
echo 小满后端启动脚本
echo Python: %PYTHON%
echo ==========================================

REM 检查 Python 3.14
if not exist "%PYTHON%" (
    echo [错误] 找不到 Python 3.14: %PYTHON%
    echo 请先安装 Python 3.14
    pause
    exit /b 1
)

REM 检查依赖
echo [1/3] 检查依赖...
%PYTHON% -c "import lancedb" 2>nul
if errorlevel 1 (
    echo [1/3] 安装依赖...
    %PYTHON% -m pip install -r "%SCRIPT_DIR%requirements.txt"
) else (
    echo [1/3] 依赖已安装 ✓
)

REM 检查环境变量
echo [2/3] 检查环境变量...
if "%LLM_API_KEY%"=="" (
    echo [警告] LLM_API_KEY 未设置，将从 xiaoman.json 读取
)

REM 启动服务器
echo [3/3] 启动服务器...
echo ==========================================
cd /d "%SCRIPT_DIR%"
%PYTHON% main.py

pause
