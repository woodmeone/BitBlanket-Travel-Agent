# 部署指南

本指南介绍如何将项目部署到生产环境，支持多种部署方式。

---

## 部署架构

```
互联网用户
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                    负载均衡器                        │
│                   (Nginx/Cloud)                      │
└─────────────────────┬───────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ Next.js (43001) │     │ FastAPI (48081) │
│    前端服务      │     │    API 服务     │
└─────────────────┘     └────────┬────────┘
                                 │
                                 │ gRPC (50051)
                                 ▼
                        ┌─────────────────┐
                        │  Agent (50051)  │
                        │   AI 推理服务    │
                        └─────────────────┘
```

---

## 1. 环境准备

### 1.1 服务器要求

| 配置 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 1核 | 2核+ |
| 内存 | 1GB | 4GB+ |
| 磁盘 | 10GB | 50GB+ |
| 带宽 | 1Mbps | 10Mbps+ |

### 1.2 安装 Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 添加用户到 docker 组
sudo usermod -aG docker $USER
```

### 1.3 安装 Docker Compose

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

---

## 2. Docker 部署（推荐）

### 2.1 配置环境变量

创建 `.env` 文件：

```bash
# LLM 配置
LLM_API_KEY=your-api-key-here
LLM_PROVIDER_TYPE=openai
LLM_MODEL=gpt-4o-mini

# Agent 配置
AGENT_HOST=0.0.0.0
AGENT_PORT=50051

# Web 配置
WEB_HOST=0.0.0.0
WEB_PORT=48081

# 前端配置
NEXT_PUBLIC_API_BASE=https://api.your-domain.com
```

### 2.2 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 仅启动基础设施
docker-compose up -d redis milvus-etcd milvus-minio milvus nacos mysql

# 仅启动应用服务
docker-compose up -d --build agent web frontend

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 2.3 Docker 服务配置

当前 `docker-compose.yml` 包含完整的全栈服务编排：

**应用服务：**

| 服务 | 容器名 | 端口 | Dockerfile |
|------|--------|------|-----------|
| Agent | agent | 50051 | `agent/Dockerfile` |
| Web | web | 48081 | `web/Dockerfile` |
| Frontend | frontend | 43001 | `frontend/Dockerfile` |

**基础设施服务：**

| 服务 | 容器名 | 端口 | 镜像 |
|------|--------|------|------|
| Redis | redis | 6379 | redis:7-alpine |
| Milvus | milvus | 19530 | milvusdb/milvus:v2.5.10 |
| Milvus etcd | milvus-etcd | 2379 | quay.io/coreos/etcd:v3.5.16 |
| Milvus MinIO | milvus-minio | 9001 | minio/minio |
| Nacos | nacos | 38848 | nacos/nacos-server:v2.3.2 |
| MySQL | mysql | 3306 | mysql:8.0-debian |

所有端口绑定 `127.0.0.1`，仅本地可访问。所有服务运行在 `shuai-network` bridge 网络中。

### 2.4 Dockerfile 说明

所有 Dockerfile 使用多阶段构建优化镜像大小。

**agent/Dockerfile** (多阶段构建):

- 阶段 1 (builder): 使用 `python:3.10-slim`，安装 gcc 编译依赖，创建虚拟环境，安装 pip 依赖
- 阶段 2 (runner): 仅复制虚拟环境和代码，安装运行时工具 (curl)，以非 root 用户运行
- 构建上下文: 项目根目录 (`context: .`)
- 入口: `python run_agent.py`

**web/Dockerfile** (多阶段构建):

- 阶段 1 (builder): 使用 `python:3.10-slim`，安装依赖到虚拟环境
- 阶段 2 (runner): 复制虚拟环境和代码，设置 `PYTHONPATH=/app`
- 入口: `python -m uvicorn src.main:app --host 0.0.0.0 --port 48081`

**frontend/Dockerfile** (三阶段构建):

- 阶段 1 (deps): `node:20-alpine`，仅安装 npm 依赖
- 阶段 2 (builder): 复制依赖和源码，执行 `npm run build`
- 阶段 3 (runner): 仅复制 `.next/standalone` 产物，以非 root 用户运行
- 入口: `node server.js` (standalone 模式，端口 43001)

---

## 3. 手动部署

### 3.1 部署 Agent 服务

```bash
# 克隆代码
git clone your-repo-url
cd ShuaiTravelAgent/agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements-agent.txt

# 配置环境变量
export LLM_API_KEY=your-api-key

# 启动服务
python -m src.server --port 50051
```

### 3.2 部署 Web 服务

```bash
cd ShuaiTravelAgent/web

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements-web.txt

# 配置环境变量
export AGENT_GRPC_HOST=localhost
export AGENT_GRPC_PORT=50051

# 启动服务
python -m src.main --port 48081
```

### 3.3 部署前端

**构建:**

```bash
cd frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 预览构建结果
npm run start
```

**使用 Nginx:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /var/www/shuai-travel-frontend/.next;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:48081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## 4. 云服务部署

### 4.1 Vercel（前端）

```bash
cd frontend

# 安装 Vercel CLI
npm i -g vercel

# 部署
vercel --prod
```

**vercel.json:**

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs"
}
```

### 4.2 Railway

1. 连接 GitHub 仓库
2. 添加服务：
   - Agent 服务
   - Web 服务
3. 配置环境变量
4. 部署

### 4.3 AWS

**使用 ECS:**

```bash
# 构建镜像
docker build -t shuai-travel-agent ./agent
docker build -t shuai-travel-web ./web
docker build -t shuai-travel-frontend ./frontend

# 推送到 ECR
aws ecr create-repository --repository-name shuai-travel-agent
docker tag shuai-travel-agent:latest aws-account.dkr.ecr.region.amazonaws.com/shuai-travel-agent:latest
docker push aws-account.dkr.ecr.region.amazonaws.com/shuai-travel-agent:latest

# 创建 ECS 任务定义和服务
```

### 4.4 阿里云

**使用容器服务 ACK:**

1. 创建 Kubernetes 集群
2. 配置 Helm Chart
3. 部署应用

---

## 5. 域名与 HTTPS

### 5.1 配置域名

| 服务 | 域名 | 端口 |
|------|------|------|
| 前端 | www.your-domain.com | 443 |
| API | api.your-domain.com | 443 |

### 5.2 配置 HTTPS

**使用 Let's Encrypt:**

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d www.your-domain.com -d api.your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

**Nginx 配置:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:48081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## 6. 监控与日志

### 6.1 日志配置

**Python 日志:**

```python
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/shuai-travel/agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
```

### 6.2 监控

**使用 Prometheus + Grafana:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'shuai-travel'
    static_configs:
      - targets: ['agent:8000', 'web:8000']
```

### 6.3 健康检查端点

```bash
# 检查所有服务
curl http://localhost:48081/health
curl http://localhost:50051/health

# 检查容器状态
docker-compose ps
```

---

## 7. 备份与恢复

### 7.1 备份会话数据

```bash
# 备份到文件
cp data/sessions.json backups/sessions-$(date +%Y%m%d).json

# 定时备份
# crontab -e
0 3 * * * cp /path/to/data/sessions.json /path/to/backups/
```

### 7.2 恢复数据

```bash
# 从备份恢复
cp backups/sessions-20240115.json data/sessions.json
```

### 7.3 Docker 卷备份

```bash
# 备份卷
docker run --rm -v shuai-travel_data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .

# 恢复卷
docker run --rm -v shuai-travel_data:/data -v $(pwd):/backup alpine tar xzf /backup/backup.tar.gz -C /data
```

---

## 8. 故障排查

### 8.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 服务无法启动 | 端口被占用 | 检查端口或修改配置 |
| 前端无法连接 API | CORS 问题 | 检查 CORS 配置 |
| LLM 调用失败 | API Key 错误 | 检查环境变量 |
| SSE 连接断开 | 网络问题 | 检查网络配置 |
| 内存不足 | 并发过高 | 优化代码或增加资源 |

### 8.2 查看日志

```bash
# Docker 日志
docker-compose logs -f agent
docker-compose logs -f web

# 系统日志
sudo journalctl -u shuai-travel-agent -f

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 8.3 性能优化

```bash
# 检查资源使用
docker stats

# 检查磁盘空间
df -h

# 检查内存使用
free -m
```

---

## 9. 更新部署

### 9.1 Docker 更新

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker-compose up -d --build

# 清理旧镜像
docker image prune -f
```

### 9.2 手动更新

```bash
# 停止服务
sudo systemctl stop shuai-travel-agent
sudo systemctl stop shuai-travel-web

# 更新代码
git pull

# 重启服务
sudo systemctl start shuai-travel-agent
sudo systemctl start shuai-travel-web
```

### 9.3 回滚

```bash
# Docker 回滚
docker-compose down
docker-compose up -d --build <previous-commit>

# 使用 Docker Hub 标签
docker-compose pull
docker-compose up -d
```
