@echo off
chcp 65001 >nul
echo ============================================
echo   小帅旅游助手 - 前端启动脚本
echo ============================================
echo.

cd frontend

REM 检查 node_modules
if not exist node_modules (
    echo [1/2] 安装前端依赖...
    call npm install
    if errorlevel 1 (
        echo 错误: npm install 失败
        pause
        exit /b 1
    )
) else (
    echo [1/2] 依赖已安装
)

REM 启动前端
echo [2/2] 启动前端服务...
echo.
echo 前端地址: http://localhost:33001
echo.
echo 按 Ctrl+C 停止服务
echo.

call npm run dev
