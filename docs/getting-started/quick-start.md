# Quick Start

## 前置条件

- uv
- Python 3.13
- Node.js 18+
- npm 9+

## 1. 创建虚拟环境（Python 3.13）

```bash
uv python install 3.13
uv venv .venv --python 3.13
.\.venv\Scripts\activate
```

## 2. 安装依赖

```bash
uv pip install -r requirements.txt
cd frontend && npm install
```

## 3. 准备配置

```bash
copy config\\llm_config.yaml.example config\\llm_config.yaml
```

`config/server_config.yaml` 已在仓库中提供默认端口配置。

## 4. 手动启动

### 终端 1：启动 API

```bash
.\.venv\Scripts\python.exe -m uvicorn shuai_web.main:app --host 0.0.0.0 --port 38000 --app-dir web
```

### 终端 2：启动前端

```bash
cd frontend
npm run dev
```

## 5. 访问地址

- Frontend: `http://localhost:33001`
- API: `http://localhost:38000`
- API Docs: `http://localhost:38000/rapidoc`
- Health: `http://localhost:38000/api/health`
