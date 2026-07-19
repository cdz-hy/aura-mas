# AURA-MAS Ubuntu 22.04 部署指南

> 目标环境：Ubuntu 22.04 LTS，2 核 8GB 内存
> 架构：Nginx 反向代理 + Java/Python 双后端 + Docker 基础设施
> 项目路径：`/opt/aura-mas`（git clone 到此目录）

---

## 目录

1. [架构总览](#1-架构总览)
2. [端口规划](#2-端口规划)
3. [内存预算](#3-内存预算)
4. [Step 1：系统初始化](#step-1系统初始化)
5. [Step 2：安装 Docker](#step-2安装-docker)
6. [Step 3：Docker 部署基础设施](#step-3docker-部署基础设施)
7. [Step 4：安装 MySQL 8](#step-4安装-mysql-8)
8. [Step 5：安装 Java 21](#step-5安装-java-21)
9. [Step 6：构建并部署 Java 后端](#step-6构建并部署-java-后端)
10. [Step 7：安装 Python 3.11 并部署 Python 后端](#step-7安装-python-311-并部署-python-后端)
11. [Step 8：构建并部署 Vue 前端](#step-8构建并部署-vue-前端)
12. [Step 9：安装并配置 Nginx](#step-9安装并配置-nginx)
13. [Step 10：防火墙配置](#step-10防火墙配置)
14. [Step 11：验证与测试](#step-11验证与测试)
15. [运维命令速查](#运维命令速查)
16. [常见问题排查](#常见问题排查)

---

## 1. 架构总览

```
                        ┌─────────────────────────────────────────────┐
                        │              Ubuntu 22.04 Server            │
                        │                                             │
  Browser / App ───────►│  Nginx (:80/:443)                          │
                        │     ├── /          → Vue dist/ 静态文件     │
                        │     ├── /api/*     → Java Backend (:8080)   │
                        │     └── /ai/*      → Python Backend (:8002) │
                        │                                             │
                        │  Docker 容器:                               │
                        │     ├── Redis 7       (:6379)               │
                        │     ├── RabbitMQ 3    (:5672/:15672)        │
                        │     └── Qdrant        (:6333/:6334)         │
                        │                                             │
                        │  系统服务:                                  │
                        │     ├── MySQL 8       (:3306)               │
                        │     ├── Java Backend  (systemd)             │
                        │     └── Python Backend (systemd)            │
                        └─────────────────────────────────────────────┘
```

### 项目目录结构

```
/opt/aura-mas/                    # git clone 根目录
├── Java-backend/                 # Spring Boot 后端
│   ├── pom.xml
│   ├── src/main/resources/
│   │   ├── application.yml       # 默认配置
│   │   ├── application-prod.yml  # 生产配置（需手动创建）
│   │   ├── schema.sql            # 建表语句
│   │   └── data.sql              # 种子数据
│   └── target/
│       └── learning-system-1.0.0.jar  # 构建产物
├── Python-backend/               # FastAPI 后端
│   ├── main.py                   # 入口
│   ├── requirements.txt
│   ├── .env                      # 环境变量（需手动创建）
│   └── app/
├── Vue-frontend/                 # Vue 3 SPA
│   ├── package.json
│   ├── .env.production           # 生产环境变量（需手动创建）
│   └── dist/                     # 构建产物
├── docker-compose.yml            # 基础设施 Docker 编排
└── uploads/                      # 文件上传目录（需手动创建）
```

---

## 2. 端口规划

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 80, 443 | HTTP/HTTPS 入口 |
| Java Backend | 8080 | Spring Boot API |
| Python Backend | 8002 | FastAPI AI 服务 |
| MySQL | 3306 | 数据库 |
| Redis | 6379 | 缓存 |
| RabbitMQ | 5672, 15672 | 消息队列 / 管理后台 |
| Qdrant | 6333, 6334 | 向量数据库 REST/gRPC |

---

## 3. 内存预算

| 组件 | 内存上限 | 说明 |
|------|----------|------|
| OS + 系统进程 | ~500 MB | |
| MySQL | 512 MB | innodb_buffer_pool_size |
| Redis | 256 MB | maxmemory |
| RabbitMQ | ~300 MB | |
| Qdrant | 1024 MB | Docker --memory |
| Java Backend | 800 MB | JVM -Xmx |
| Python Backend | ~500 MB | |
| Nginx | ~20 MB | |
| **合计** | **~3.9 GB** | 留 ~4.1 GB 余量 |

---

## Step 1：系统初始化

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git vim unzip software-properties-common \
    apt-transport-https ca-certificates gnupg lsb-release \
    build-essential libssl-dev libffi-dev

# 设置时区
sudo timedatectl set-timezone Asia/Shanghai

# 设置主机名（可选）
sudo hostnamectl set-hostname aura-mas
```

---

## Step 2：安装 Docker

```bash
# 卸载旧版本（如果有）
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# 添加 Docker 官方 GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 将当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER

# 验证安装
docker --version
docker compose version

# 配置 Docker 镜像加速（国内服务器推荐）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://hub-mirror.c.163.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
sudo systemctl enable docker
```

> **注意**：加入 docker 组后需要重新登录终端才生效，或执行 `newgrp docker`。

---

## Step 3：Docker 部署基础设施

### 3.1 拉取代码并启动容器

```bash
# 克隆项目
cd /opt
sudo git clone https://github.com/cdz-hy/aura-mas.git
sudo chown -R $USER:$USER /opt/aura-mas

# 创建 Docker 网络
docker network create aura-net

# 使用 docker-compose 一键启动基础设施
cd /opt/aura-mas
docker compose up -d

# 验证三个容器都正常运行
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### 3.2 创建 Qdrant 向量集合

```bash
curl -X PUT http://localhost:6333/collections/aura_multimodal_resources \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 2560,
      "distance": "Cosine"
    }
  }'

# 验证
curl http://localhost:6333/collections/aura_multimodal_resources
```

### 3.3 逐个验证

```bash
# Redis
docker exec aura-redis redis-cli ping
# → PONG

# RabbitMQ 管理后台：http://<服务器IP>:15672（guest/guest）

# Qdrant
curl http://localhost:6333/healthz
```

---

## Step 4：安装 MySQL 8

```bash
sudo apt install -y mysql-server

# 启动并设为开机自启
sudo systemctl start mysql
sudo systemctl enable mysql

# 安全初始化（设置 root 密码、移除匿名用户等）
sudo mysql_secure_installation
```

安全初始化建议选项：
- Validate password component: **Y**（可选）
- 密码强度: **0 (LOW)** 或 **1 (MEDIUM)**
- 设置 root 密码: **输入你的强密码**
- Remove anonymous users: **Y**
- Disallow root login remotely: **Y**
- Remove test database: **Y**
- Reload privilege tables: **Y**

### 4.1 创建数据库

```bash
sudo mysql -u root -p
```

```sql
CREATE DATABASE IF NOT EXISTS learning_system
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 验证
SHOW DATABASES;
EXIT;
```

> 数据库表和初始数据由 Java 后端首次启动时自动执行 `schema.sql` + `data.sql` 创建。

### 4.2 MySQL 内存优化

```bash
sudo vim /etc/mysql/mysql.conf.d/mysqld.cnf
```

在 `[mysqld]` 段添加/修改：

```ini
innodb_buffer_pool_size = 512M
innodb_log_file_size = 64M
innodb_flush_log_at_trx_commit = 2
max_connections = 100
table_open_cache = 200
sort_buffer_size = 2M
read_buffer_size = 1M
```

```bash
sudo systemctl restart mysql
```

---

## Step 5：安装 Java 21

```bash
sudo add-apt-repository ppa:openjdk-r/ppa -y
sudo apt update
sudo apt install -y openjdk-21-jdk

# 验证
java -version
javac -version

# 设置 JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

### 5.1 安装 Maven

```bash
sudo apt install -y maven
mvn -version
```

---

## Step 6：构建并部署 Java 后端

### 6.1 构建 JAR 包

```bash
cd /opt/aura-mas/Java-backend
mvn clean package -DskipTests
```

构建产物：`target/learning-system-1.0.0.jar`

### 6.2 确认 application-local.yml

配置值写在 `application-local.yml` 中（已加入 `.gitignore`），通过 `SPRING_PROFILES_ACTIVE=local` 加载。

```bash
cat src/main/resources/application-local.yml
```

确认以下配置正确：

| 配置 | 说明 |
|------|------|
| `spring.datasource.password` | MySQL root 密码 |
| `jwt.secret` | JWT 签名密钥 |
| `internal.secret` | 服务间通信密钥（需与 Python 的 `JAVA_SERVICE_SECRET` 一致） |
| `qiniu.*` | 七牛云 OSS 配置 |
| `mail.*` | 邮件服务配置 |

> `application-local.yml` 中 `spring.sql.init.mode` 默认为 `always`，首次启动会自动建表。建表成功后可改为 `never` 加快重启速度。

### 6.3 创建上传目录

```bash
mkdir -p /opt/aura-mas/uploads
```

### 6.4 创建 systemd 服务

配置值写在 `application-local.yml` 中，systemd 只需指定 profile，无需注入环境变量。

```bash
sudo tee /etc/systemd/system/aura-java.service <<'EOF'
[Unit]
Description=AURA Java Backend
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aura-mas/Java-backend
Environment=SPRING_PROFILES_ACTIVE=local
ExecStart=/usr/lib/jvm/java-21-openjdk-amd64/bin/java \
    -Xmx800m -Xms256m \
    -XX:+UseG1GC -XX:MaxGCPauseMillis=100 \
    -jar target/learning-system-1.0.0.jar
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

### 6.5 启动 Java 后端

```bash
sudo systemctl daemon-reload
sudo systemctl start aura-java
sudo systemctl enable aura-java

# 查看启动日志（等待 ~15 秒）
sudo journalctl -u aura-java -f

# 另开终端检查状态
sudo systemctl status aura-java

# 快速验证
curl http://localhost:8080/
```

---

## Step 7：安装 Python 3.11 并部署 Python 后端

### 7.1 安装 Python 3.11 和系统依赖

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# ffmpeg（音频/视频处理依赖）
sudo apt install -y ffmpeg

# 验证
python3.11 --version
ffmpeg -version
```

### 7.2 创建虚拟环境并安装依赖

```bash
cd /opt/aura-mas/Python-backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（动画导出功能需要，可选）
python -m playwright install chromium
python -m playwright install-deps chromium

# 验证
python -c "import fastapi; print(fastapi.__version__)"
```

### 7.3 创建生产环境 .env

```bash
cat > /opt/aura-mas/Python-backend/.env <<'EOF'
# === 必填 API Keys ===
DASHSCOPE_API_KEY=你的阿里云百炼Key
MIMO_API_KEY=你的小米MiMoKey
MINERU_API_KEY=你的MinerUKey

# === 可选 API Keys ===
TAVILY_API_KEY=
ARK_API_KEY=

# === 七牛云 OSS ===
QINIU_ACCESS_KEY=你的七牛AccessKey
QINIU_SECRET_KEY=你的七牛SecretKey
QINIU_BUCKET_NAME=你的Bucket名
QINIU_DOMAIN=http://你的域名

# === 基础设施连接 ===
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=aura_multimodal_resources
QDRANT_VECTOR_SIZE=2560

# === 服务间通信 ===
JAVA_BACKEND_URL=http://localhost:8080
JAVA_SERVICE_SECRET=learning-system-internal-service-secret-2024

# === 应用设置 ===
DEBUG=False
PORT=8002
EOF
```

> `JAVA_SERVICE_SECRET` 必须与 Java 后端的 `INTERNAL_SECRET` 一致。

### 7.4 创建 systemd 服务

```bash
sudo tee /etc/systemd/system/aura-python.service <<'EOF'
[Unit]
Description=AURA Python Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aura-mas/Python-backend
Environment=PATH=/opt/aura-mas/Python-backend/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/aura-mas/Python-backend/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8002 --workers 2
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

> `--workers 2`：2 核机器建议 2 个 worker。

### 7.5 启动 Python 后端

```bash
sudo systemctl daemon-reload
sudo systemctl start aura-python
sudo systemctl enable aura-python

# 查看日志
sudo journalctl -u aura-python -f

# 验证
curl http://localhost:8002/
# → {"message":"AURA Python 后端服务已启动 (RAG + 多智能体)"}
```

---

## Step 8：构建并部署 Vue 前端

### 8.1 安装 Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

node -v
npm -v
```

### 8.2 构建前端

```bash
cd /opt/aura-mas/Vue-frontend

# 创建生产环境变量（前端 SSE 直连 Python 后端）
cat > .env.production <<'EOF'
VITE_PYTHON_AI_BASE=http://cdzhy.top:8002
EOF

# 安装依赖并构建
npm install
npm run build
```

构建产物在 `dist/` 目录。

### 8.3 部署到 Nginx 目录

```bash
sudo mkdir -p /var/www/aura-mas
sudo cp -r /opt/aura-mas/Vue-frontend/dist/* /var/www/aura-mas/
sudo chown -R www-data:www-data /var/www/aura-mas
```

---

## Step 9：安装并配置 Nginx

### 9.1 安装

```bash
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 9.2 配置反向代理

```bash
sudo tee /etc/nginx/sites-available/aura-mas <<'EOF'
server {
    listen 80;
    server_name cdzhy.top;

    # 前端静态文件
    root /var/www/aura-mas;
    index index.html;

    # Vue Router history 模式
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Java 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Python 后端 AI 接口代理
    location /ai/ {
        proxy_pass http://127.0.0.1:8002/api/ai/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式支持（AI 流式输出必须）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    # Python 后端其他 API 代理
    location /api/v1/ {
        proxy_pass http://127.0.0.1:8002/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    # 上传文件大小限制
    client_max_body_size 100M;
}
EOF

# 启用站点
sudo ln -sf /etc/nginx/sites-available/aura-mas /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重载
sudo systemctl reload nginx
```

### 9.3 HTTPS 配置

```bash
# 安装 certbot
sudo apt install -y certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d cdzhy.top

# 测试自动续期
sudo certbot renew --dry-run
```

申请成功后访问 `https://cdzhy.top`。证书每 90 天自动续期。

> **注意**：开启 HTTPS 后，`.env.production` 中的 `VITE_PYTHON_AI_BASE` 需要改为 `http://cdzhy.top:8002`（Python 后端仍走 HTTP，因为 SSE 直连不经过 Nginx）。如需全部走 HTTPS，需要让 Nginx 也代理 Python SSE 请求，但这会增加配置复杂度。

---

## Step 10：防火墙配置

```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 'Nginx Full'

# 如需远程访问 RabbitMQ 管理后台：
# sudo ufw allow from 你的IP to any port 15672

sudo ufw status verbose
```

---

## Step 11：验证与测试

### 11.1 全部服务状态检查

```bash
# Docker 容器
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# systemd 服务
sudo systemctl status aura-java aura-python nginx mysql

# 端口监听
ss -tlnp | grep -E '80|8080|8002|3306|6379|5672|6333'
```

### 11.2 逐项测试

```bash
# 前端
curl -I http://localhost
# HTTP/1.1 200 OK

# Java 后端
curl http://localhost:8080/

# Python 后端
curl http://localhost:8002/
# {"message":"AURA Python 后端服务已启动 (RAG + 多智能体)"}

# Qdrant
curl http://localhost:6333/healthz

# Redis
docker exec aura-redis redis-cli ping

# MySQL
mysql -u root -p -e "SELECT 1"
```

### 11.3 浏览器访问

```
http://<服务器IP>
```

---

## 运维命令速查

```bash
# ===== 服务管理 =====
sudo systemctl start|stop|restart|status aura-java
sudo systemctl start|stop|restart|status aura-python
sudo systemctl start|stop|restart|status nginx
sudo systemctl start|stop|restart|status mysql

# ===== 查看日志 =====
sudo journalctl -u aura-java -f
sudo journalctl -u aura-python -f
sudo journalctl -u aura-java --since today
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# ===== Docker 管理 =====
docker ps
docker logs aura-redis --tail 100
docker logs aura-rabbitmq --tail 100
docker logs aura-qdrant --tail 100
docker stats
docker restart aura-redis aura-rabbitmq aura-qdrant

# ===== 重新构建部署 =====
# Java 后端更新（改了 Java-backend/ 下的任何文件才需要 mvn 重新构建）
cd /opt/aura-mas && git pull
cd /opt/aura-mas/Java-backend && mvn clean package -DskipTests
sudo systemctl restart aura-java

# Java 后端仅重启（没改代码，只改了 Nginx/systemd 等配置）
sudo systemctl restart aura-java

# Python 后端更新
cd /opt/aura-mas && git pull
sudo systemctl restart aura-python

# 前端更新
cd /opt/aura-mas && git pull
cd /opt/aura-mas/Vue-frontend && npx vite build
sudo cp -r dist/* /var/www/aura-mas/
sudo systemctl reload nginx

# ===== 磁盘空间 =====
df -h
du -sh /opt/aura-mas/*
docker system df
docker system prune -f
```

---

## 常见问题排查

### 1. Java 后端启动失败

```bash
sudo journalctl -u aura-java --no-pager -n 50
```

常见原因：
- MySQL 连接失败 → 检查 `DB_PASSWORD`、MySQL 是否启动
- Redis 连接失败 → 检查 `docker ps` 确认 Redis 容器运行中
- RabbitMQ 连接失败 → 检查 RabbitMQ 容器是否运行
- 端口占用 → `ss -tlnp | grep 8080`
- JAR 找不到 → 确认 `target/learning-system-1.0.0.jar` 存在

### 2. Python 后端启动失败

```bash
sudo journalctl -u aura-python --no-pager -n 50
```

常见原因：
- 虚拟环境路径错误 → 检查 `/opt/aura-mas/Python-backend/venv/bin/python` 是否存在
- 依赖缺失 → `source venv/bin/activate && pip install -r requirements.txt`
- .env 缺失 → 检查 `/opt/aura-mas/Python-backend/.env`
- 端口占用 → `ss -tlnp | grep 8002`

### 3. 前端页面空白

```bash
ls /var/www/aura-mas/index.html   # 确认文件存在
sudo nginx -t                      # 检查配置语法
sudo tail -20 /var/log/nginx/error.log
```

### 4. API 请求 404/502

```bash
curl http://localhost:8080/
curl http://localhost:8002/
sudo cat /etc/nginx/sites-available/aura-mas
```

### 5. spring.sql.init.mode 每次重启建表

当前 `application-prod.yml` 设为 `never`。首次部署时临时改为 `always`，启动一次建表后改回 `never`。

### 6. 内存不足 (OOM)

```bash
free -h
ps aux --sort=-%mem | head -10
```

如 Java 频繁 OOM，降低 JVM 内存：
```bash
# 编辑 /etc/systemd/system/aura-java.service
# -Xmx800m → -Xmx600m
sudo systemctl daemon-reload
sudo systemctl restart aura-java
```

### 7. git pull 后需要更新依赖

```bash
# Java
cd /opt/aura-mas/Java-backend && mvn clean package -DskipTests

# Python（如果 requirements.txt 有变动）
cd /opt/aura-mas/Python-backend && source venv/bin/activate && pip install -r requirements.txt

# 前端（如果 package.json 有变动）
cd /opt/aura-mas/Vue-frontend && npm install && npm run build
```
