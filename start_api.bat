@echo off
chcp 65001 >nul
echo ============================================
echo   小帅旅游助手 - 启动脚本
echo ============================================
echo.

REM 激活 conda 环境
echo [1/3] 激活 Python 环境...
call conda activate agents
if errorlevel 1 (
    echo 错误: 无法激活 agents 环境
    echo 请确保已安装 Anaconda 并创建 agents 环境
    pause
    exit /b 1
)

REM 检查配置文件
echo [2/3] 检查配置文件...
if not exist config\llm_config.yaml (
    echo 警告: 配置文件不存在
    echo 请复制 config\llm_config.yaml.example 为 config\llm_config.yaml
)

REM 启动 API 服务
echo [3/3] 启动 Web API 服务...
echo.
echo 服务地址: http://localhost:38000
echo API 文档:  http://localhost:38000/rapidoc
echo.
echo 按 Ctrl+C 停止服务
echo.

python run_api.py
