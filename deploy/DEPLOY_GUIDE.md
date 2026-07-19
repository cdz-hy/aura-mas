# AURA-MAS 阿里云 Linux 部署指南

> 适用环境：阿里云 ECS / 轻量应用服务器，8GB 内存，Alibaba Cloud Linux 3/4 (x86_64)
> 架构：Java Spring Boot + Python FastAPI + Vue 3 SPA + MySQL + Redis + RabbitMQ + Qdrant (Docker)

---

## 0. 架构总览

```
                         ┌─────────────────────────────────────────┐
                         │            阿里云 Linux 服务器 (8GB)      │
                         │                                         │
  用户浏览器  ──────►    │  Nginx (:80/:443)                       │
                         │    ├── /          → Vue dist/ 静态文件    │
                         │    ├── /api/*     → Java Backend (:8080) │
                         │    └── /ai/*      → Python Backend(:8002)│
                         │                                         │
                         │  MySQL (:3306)    Redis (:6379)         │
                         │  RabbitMQ (:5672) Qdrant (:6333 Docker) │
                         └─────────────────────────────────────────┘
                                      │
                                      ▼ (外部 API)
                         ┌─────────────────────────┐
                         │  七牛云 OSS              │
                         │  DashScope / MiMo API   │
                         │  MinerU / Tavily / Ark  │
                         └─────────────────────────┘
```

### 内存分配方案 (8GB)

| 组件 | 限制 | 说明 |
|---|---|---|
| 系统 OS | ~500MB | 系统进程 + 文件缓存 |
| MySQL | 512MB buffer pool | innodb_buffer_pool_size |
| Redis | 256MB | maxmemory |
| RabbitMQ | 默认 | 不限制，通常 ~300MB |
| Qdrant (Docker) | 512MB | Docker --memory 限制 |
| Java Backend | 800MB | JVM -Xmx800m |
| Python Backend | ~500MB | 无限制，通常够用 |
| Nginx | ~20MB | 极轻量 |
| **合计** | **~3.4GB** | **剩余 ~4.6GB 余量充足** |

---

## 1. 服务器基础配置

### 1.1 连接服务器

```bash
ssh root@你的服务器IP
```

### 1.2 系统更新

```bash
dnf update -y   # Alibaba Cloud Linux 3/4 用 dnf
```

### 1.3 安装基础工具

```bash
dnf install -y git wget curl vim unzip tar
```

### 1.4 创建 swap（1GB 安全网）

```bash
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
```

验证：
```bash
free -h
```

### 1.5 开放防火墙端口

```bash
# 阿里云安全组需要放行: 22, 80, 443
# 本地防火墙（如果启用了 firewalld）:
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload
```

---

## 2. 安装 Docker

Qdrant 需要 Docker 运行，顺便把 Redis 和 RabbitMQ 也用 Docker 管理更统一。

### 2.1 安装 Docker

```bash
dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable --now docker

# 验证
docker --version
docker compose version
```

> 如果 dnf 没有 docker-ce，先添加仓库：
> ```bash
> dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
> ```

### 2.2 创建项目 Docker 网络

```bash
docker network create aura-net
```

---

## 3. 安装 MySQL 8

### 3.1 安装

```bash
dnf install -y mysql-server
systemctl enable --now mysqld
```

### 3.2 安全初始化

```bash
mysql_secure_installation
# 设置 root 密码
# 移除匿名用户: Y
# 禁止远程 root 登录: Y
# 移除 test 数据库: Y
# 刷新权限表: Y
```

### 3.3 创建数据库和用户

```bash
mysql -u root -p
```

```sql
CREATE DATABASE learning_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aura'@'localhost' IDENTIFIED BY '你的数据库密码';
GRANT ALL PRIVILEGES ON learning_system.* TO 'aura'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3.4 导入数据库结构和初始数据

```bash
cd /opt/aura-mas/Java-backend
mysql -u aura -p learning_system < src/main/resources/schema.sql
mysql -u aura -p learning_system < src/main/resources/data.sql

# 如有迁移文件，按时间顺序导入：
# mysql -u aura -p learning_system < src/main/resources/migration_add_note_capture_metadata.sql
```

### 3.5 MySQL 性能调优 (8GB)

```bash
cat > /etc/my.cnf.d/aura-tuning.cnf << 'EOF'
[mysqld]
# InnoDB 缓冲池 512MB（8GB 机器充裕）
innodb_buffer_pool_size = 512M
innodb_log_buffer_size = 16M
innodb_flush_log_at_trx_commit = 2
innodb_io_capacity = 200

# 临时表与连接
tmp_table_size = 64M
max_heap_table_size = 64M
max_connections = 100
table_open_cache = 256

# 排序与读取缓冲
sort_buffer_size = 1M
read_buffer_size = 1M
read_rnd_buffer_size = 512K
join_buffer_size = 1M

# 字符集
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# 日志
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
EOF

systemctl restart mysqld
```

---

## 4. 安装 Redis (Docker)

```bash
docker run -d \
  --name aura-redis \
  --network aura-net \
  --restart unless-stopped \
  -p 6379:6379 \
  -v redis_data:/data \
  --memory 256m \
  redis:7-alpine \
  redis-server --appendonly yes --maxmemory 200mb --maxmemory-policy allkeys-lru
```

验证：
```bash
docker exec aura-redis redis-cli ping   # PONG
```

---

## 5. 安装 RabbitMQ (Docker)

```bash
docker run -d \
  --name aura-rabbitmq \
  --network aura-net \
  --restart unless-stopped \
  -p 5672:5672 \
  -p 15672:15672 \
  -v rabbitmq_data:/var/lib/rabbitmq \
  -e RABBITMQ_DEFAULT_USER=aura \
  -e RABBITMQ_DEFAULT_PASS=你的RabbitMQ密码 \
  rabbitmq:3-management-alpine
```

### 启用管理插件并验证

```bash
# 管理界面默认已启用
# 访问 http://你的IP:15672 用户名 aura 密码你设置的
docker exec aura-rabbitmq rabbitmqctl status
```

---

## 6. 安装 Qdrant 向量数据库 (Docker)

```bash
docker run -d \
  --name aura-qdrant \
  --network aura-net \
  --restart unless-stopped \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  --memory 512m \
  qdrant/qdrant:latest
```

### 验证

```bash
curl http://localhost:6333/health   # {"status":"ok"}
```

### 创建集合（Python 后端用到的）

```bash
curl -X PUT http://localhost:6333/collections/aura_multimodal_resources \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 2560,
      "distance": "Cosine"
    }
  }'
```

---

## 7. 安装 Nginx

```bash
dnf install -y nginx
systemctl enable --now nginx
```

验证：
```bash
curl http://localhost
```

---

## 8. 安装 Java 17

```bash
dnf install -y java-17-openjdk java-17-openjdk-devel maven

# 验证
java -version
mvn --version
```

---

## 9. 安装 Python 3.11+

### 9.1 安装 Python

```bash
dnf install -y python3.11 python3.11-pip python3.11-devel

# 验证
python3.11 --version
```

### 9.2 安装 ffmpeg（动画导出需要）

```bash
cd /opt
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar xf ffmpeg-release-amd64-static.tar.xz
cp ffmpeg-*-static/ffmpeg /usr/local/bin/
cp ffmpeg-*-static/ffprobe /usr/local/bin/
chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe
rm -rf ffmpeg-*-static ffmpeg-release-amd64-static.tar.xz

# 验证
ffmpeg -version
```

---

## 10. 拉取项目代码

```bash
mkdir -p /opt/aura-mas
cd /opt/aura-mas
git clone -b main https://github.com/cdz-hy/aura-mas.git .
```

---

## 11. 配置 Python 后端

### 11.1 创建虚拟环境并安装依赖

```bash
cd /opt/aura-mas/Python-backend

python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 11.2 安装 Playwright 浏览器（动画渲染需要，可选）

```bash
# 如果需要动画导出功能
playwright install chromium
playwright install-deps
```

> 如果内存紧张可跳过，动画导出会自动降级

### 11.3 创建 .env 配置文件

```bash
cp .env.template .env
vim .env
```

填写以下配置：

```env
# === 服务端口 ===
PORT=8002
DEBUG=false

# === Java 后端 ===
JAVA_BACKEND_URL=http://127.0.0.1:8080

# === Redis (Docker 容器，宿主机访问用 127.0.0.1) ===
REDIS_URL=redis://127.0.0.1:6379/0

# === RabbitMQ (Docker 容器) ===
RABBITMQ_URL=amqp://aura:你的RabbitMQ密码@127.0.0.1:5672/

# === Qdrant (Docker 容器，本地运行) ===
QDRANT_URL=http://127.0.0.1:6333

# === LLM API Keys ===
DASHSCOPE_API_KEY=你的DashScope Key
MIMO_API_KEY=你的MiMo Key
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1

# === 文件存储 (七牛云) ===
QINIU_ACCESS_KEY=你的七牛AccessKey
QINIU_SECRET_KEY=你的七牛SecretKey
QINIU_BUCKET=你的Bucket名
QINIU_DOMAIN=你的七牛域名

# === 其他外部 API ===
MINERU_API_KEY=你的MinerU Key
TAVILY_API_KEY=你的Tavily Key（可选）
ARK_API_KEY=你的火山方舟Key（可选）
```

### 11.4 测试启动

```bash
source /opt/aura-mas/Python-backend/venv/bin/activate
cd /opt/aura-mas/Python-backend
python main.py
# 看到 "Uvicorn running on http://0.0.0.0:8002" 即成功
# Ctrl+C 停止，后面用 systemd 管理
```

---

## 12. 配置 Java 后端

### 12.1 创建 application-prod.yml

```bash
cd /opt/aura-mas/Java-backend
cat > src/main/resources/application-prod.yml << 'EOF'
server:
  port: 8080

spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/learning_system?useUnicode=true&characterEncoding=utf-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
    username: aura
    password: 你的数据库密码
    driver-class-name: com.mysql.cj.jdbc.Driver
  data:
    redis:
      host: 127.0.0.1
      port: 6379
  rabbitmq:
    host: 127.0.0.1
    port: 5672
    username: aura
    password: 你的RabbitMQ密码
  servlet:
    multipart:
      max-file-size: 200MB
      max-request-size: 200MB

mybatis-plus:
  configuration:
    map-underscore-to-camel-case: true
  global-config:
    db-config:
      logic-delete-field: deleted
      logic-delete-value: 1
      logic-not-delete-value: 0

# JWT
jwt:
  secret: $(openssl rand -base64 48 | tr -d '\n')
  expiration: 86400000

# 文件上传
file:
  upload-dir: /opt/aura-mas/uploads

# MinIO（可选，也可以只用七牛）
minio:
  endpoint: http://127.0.0.1:9000
  access-key: minioadmin
  secret-key: minioadmin
  bucket: learning-resources

# 七牛
qiniu:
  access-key: 你的七牛AccessKey
  secret-key: 你的七牛SecretKey
  bucket: 你的Bucket名
  domain: 你的七牛域名

# Python 后端地址
python:
  backend:
    url: http://127.0.0.1:8002

# 邮件（可选）
spring.mail:
  host: smtp.qq.com
  port: 587
  username: 你的QQ邮箱
  password: 你的QQ邮箱授权码
  properties:
    mail.smtp.auth: true
    mail.smtp.starttls.enable: true
EOF
```

### 12.2 打包

```bash
cd /opt/aura-mas/Java-backend
mvn clean package -DskipTests
```

打包产物在 `target/*.jar`，记下文件名。

### 12.3 测试启动

```bash
java -Xmx800m -Xms256m -XX:+UseG1GC \
  -jar target/learning-0.0.1-SNAPSHOT.jar \
  --spring.profiles.active=prod

# 看到 "Started LearningApplication" 即成功
# Ctrl+C 停止
```

---

## 13. 构建 Vue 前端

### 13.1 安装 Node.js 20 LTS

```bash
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs

# 验证
node -v   # v20.x
npm -v
```

### 13.2 构建

```bash
cd /opt/aura-mas/Vue-frontend
npm install
npm run build
```

构建产物在 `dist/` 目录。

---

## 14. 配置 Nginx

```bash
cat > /etc/nginx/conf.d/aura-mas.conf << 'EOF'
server {
    listen 80;
    server_name 你的域名.com;

    client_max_body_size 200M;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 1000;

    # Vue 前端静态文件
    location / {
        root /opt/aura-mas/Vue-frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;

        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$ {
            expires 7d;
            add_header Cache-Control "public, immutable";
        }
    }

    # Java 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 长连接支持
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;

        # 上传大小
        client_max_body_size 200M;
    }

    # Python 后端 AI API
    location /ai/ {
        proxy_pass http://127.0.0.1:8002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式输出支持
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
    }

    # Swagger 文档（可选，生产环境建议关闭）
    location /swagger-ui/ {
        proxy_pass http://127.0.0.1:8080/swagger-ui/;
    }
    location /v3/api-docs/ {
        proxy_pass http://127.0.0.1:8080/v3/api-docs/;
    }
}
EOF

# 测试配置
nginx -t

# 重载
systemctl reload nginx
```

---

## 15. 配置 Systemd 服务

### 15.1 Java 后端服务

```bash
# 先确认 jar 文件名
ls /opt/aura-mas/Java-backend/target/*.jar
```

```bash
cat > /etc/systemd/system/aura-java.service << 'EOF'
[Unit]
Description=AURA-MAS Java Backend
After=network.target mysqld.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aura-mas/Java-backend
ExecStart=/usr/bin/java -Xmx800m -Xms256m -XX:+UseG1GC -XX:MaxGCPauseMillis=100 -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/opt/aura-mas/logs/java-heapdump.hprof -jar target/learning-0.0.1-SNAPSHOT.jar --spring.profiles.active=prod
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=JAVA_HOME=/usr/lib/jvm/java-17-openjdk

[Install]
WantedBy=multi-user.target
EOF
```

### 15.2 Python 后端服务

```bash
cat > /etc/systemd/system/aura-python.service << 'EOF'
[Unit]
Description=AURA-MAS Python Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aura-mas/Python-backend
Environment=PATH=/opt/aura-mas/Python-backend/venv/bin:/usr/local/bin:/usr/bin
ExecStart=/opt/aura-mas/Python-backend/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

### 15.3 启用并启动

```bash
mkdir -p /opt/aura-mas/logs

systemctl daemon-reload
systemctl enable aura-java aura-python
systemctl start aura-java aura-python
```

---

## 16. 验证部署

### 16.1 检查所有服务

```bash
# 系统服务
for svc in mysqld nginx aura-java aura-python; do
  echo -n "$svc: "; systemctl is-active $svc
done

# Docker 容器
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### 16.2 检查端口

```bash
ss -tlnp | grep -E ':(80|8080|8002|3306|6379|5672|6333)\s'
```

应看到 7 个端口全部在监听。

### 16.3 访问测试

```bash
# 前端
curl -I http://你的域名

# Java 后端
curl http://127.0.0.1:8080/api/health

# Python 后端
curl http://127.0.0.1:8002/docs

# Qdrant
curl http://127.0.0.1:6333/health

# 通过 Nginx 反代
curl -I http://你的域名/ai/docs
```

### 16.4 浏览器访问

打开 `http://你的域名`，应能看到登录页面。

---

## 17. 内存监控

```bash
# 实时总览
watch -n 2 'free -h && echo "---Docker---" && docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" && echo "---Systemd---" && ps -C java,python3.11 -o pid,rss,comm --sort=-rss'

# 快速检查
free -h
docker stats --no-stream
```

---

## 18. 日志排查

```bash
# Java 后端
journalctl -u aura-java -f --no-pager -n 100

# Python 后端
journalctl -u aura-python -f --no-pager -n 100

# Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# Docker 容器日志
docker logs -f aura-rabbitmq --tail 50
docker logs -f aura-qdrant --tail 50
docker logs -f aura-redis --tail 50
```

---

## 19. 常见问题

### Q: Java 启动报 OOM
确认 JVM 参数：`-Xmx800m`，检查实际内存 `free -h`

### Q: Python 后端连不上 Qdrant
确认 Qdrant 容器运行：`docker ps | grep qdrant`，测试连接：`curl http://localhost:6333/health`

### Q: 前端页面白屏
1. 检查 `dist/` 是否构建成功：`ls /opt/aura-mas/Vue-frontend/dist/`
2. 检查 Nginx 配置：`nginx -t`
3. 浏览器控制台查看 API 请求路径

### Q: SSE 流式输出不工作
确认 Nginx 配置了 `proxy_buffering off` 和 `proxy_cache off`

### Q: Docker 容器自动重启
查看日志：`docker logs 容器名 --tail 50`，常见原因是内存不足

### Q: RabbitMQ 管理界面打不开
确认安全组放行 15672 端口，或通过 Nginx 反代

---

## 20. 更新部署

```bash
cd /opt/aura-mas
git pull origin main

# Java
cd /opt/aura-mas/Java-backend
mvn clean package -DskipTests
systemctl restart aura-java

# Python
cd /opt/aura-mas/Python-backend
source venv/bin/activate
pip install -r requirements.txt
systemctl restart aura-python

# Vue
cd /opt/aura-mas/Vue-frontend
npm install
npm run build
```

---

## 21. 后续优化

1. **HTTPS**：`dnf install certbot python3-certbot-nginx && certbot --nginx -d 你的域名`
2. **七牛云 OSS**：https://www.qiniu.com/ → 创建 Bucket 获取密钥
3. **DashScope API Key**：https://dashscope.console.aliyun.com/
4. **定时备份 MySQL**：
   ```bash
   crontab -e
   0 3 * * * mysqldump -u aura -p你的密码 learning_system | gzip > /opt/backup/db_$(date +\%Y\%m\%d).sql.gz
   ```
5. **日志轮转**（防止日志撑满磁盘）：
   ```bash
   cat > /etc/logrotate.d/aura-mas << 'EOF'
   /opt/aura-mas/logs/*.log {
       daily
       rotate 7
       compress
       missingok
       notifempty
   }
   EOF
   ```
6. **监控告警**：安装 `htop` + `ncdu` 实时监控
   ```bash
   dnf install -y htop ncdu
   ```
