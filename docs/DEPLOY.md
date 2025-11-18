# 🚀 Telegram 机器人 Docker 部署指南

本文档介绍如何使用 Docker Compose 将 Telegram 机器人部署到服务器并持续运行。

## 📋 前置要求

### 服务器要求
- Linux 服务器（Ubuntu/Debian/CentOS等）
- 至少 256MB 可用内存
- 至少 500MB 可用磁盘空间

### 软件要求
- Docker（版本 20.10 或更高）
- Docker Compose（版本 2.0 或更高）

## 🔧 安装 Docker 和 Docker Compose

### Ubuntu/Debian
```bash
# 更新包索引
sudo apt update

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo apt install docker-compose-plugin

# 将当前用户添加到 docker 组（避免每次使用 sudo）
sudo usermod -aG docker $USER

# 重新登录以使组权限生效
```

### CentOS/RHEL
```bash
# 安装 Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
```

### 验证安装
```bash
docker --version
docker compose version
```

## 📦 部署步骤

### 1. 上传项目文件到服务器

**方式一：使用 Git（推荐）**
```bash
# 在服务器上克隆项目（如果项目在 Git 仓库中）
git clone <你的仓库地址>
cd tg_bot
```

**方式二：使用 SCP 上传**
```bash
# 在本地执行，将项目文件上传到服务器
scp -r /home/kenijima/usr/work/GoPlus/new/tg_bot user@your-server-ip:/home/user/
```

**方式三：使用 SFTP 或 FTP 客户端**
- 使用 FileZilla、WinSCP 等工具上传整个 `tg_bot` 目录

### 2. 配置环境变量

```bash
# 进入项目目录
cd tg_bot

# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用 vim .env
```

填入以下配置：
```env
# Telegram 机器人令牌（从 @BotFather 获取）
BOT_TOKEN=your_bot_token_here

# OpenWeatherMap API 密钥（从 https://openweathermap.org/api 获取）
WEATHER_API_KEY=your_weather_api_key_here

# 管理员 Chat ID（先留空，稍后获取）
ADMIN_CHAT_ID=
```

**保存文件**（nano: `Ctrl+X` → `Y` → `Enter`）

### 3. 获取 Chat ID

```bash
# 先启动机器人（ADMIN_CHAT_ID 留空）
docker compose up -d

# 在 Telegram 中向机器人发送 /start 命令
# 机器人会回复你的 Chat ID

# 获取 Chat ID 后，停止机器人
docker compose down

# 编辑 .env 文件，填入 ADMIN_CHAT_ID
nano .env

# 重新启动机器人
docker compose up -d
```

### 4. 启动机器人

```bash
# 构建并启动容器（后台运行）
docker compose up -d

# 查看日志
docker compose logs -f

# 按 Ctrl+C 退出日志查看（容器继续运行）
```

## 🎛️ 常用管理命令

### 查看容器状态
```bash
docker compose ps
```

### 查看实时日志
```bash
docker compose logs -f
```

### 查看最近 100 行日志
```bash
docker compose logs --tail=100
```

### 重启机器人
```bash
docker compose restart
```

### 停止机器人
```bash
docker compose down
```

### 更新机器人代码后重新部署
```bash
# 停止并删除旧容器
docker compose down

# 拉取最新代码（如果使用 Git）
git pull

# 重新构建镜像并启动
docker compose up -d --build
```

### 查看容器资源使用情况
```bash
docker stats tg-weather-bot
```

### 进入容器内部（调试用）
```bash
docker exec -it tg-weather-bot /bin/bash
```

## 🔄 自动重启配置

Docker Compose 已配置为 `restart: unless-stopped`，这意味着：
- ✅ 容器崩溃时自动重启
- ✅ 服务器重启后自动启动
- ✅ 除非手动停止（`docker compose down`），否则一直运行

## 📊 监控和日志

### 日志管理
Docker Compose 已配置日志轮转：
- 每个日志文件最大 10MB
- 最多保留 3 个日志文件
- 自动清理旧日志

### 健康检查
容器每 30 秒检查一次进程是否正常运行，如果检测到异常会自动重启。

查看健康状态：
```bash
docker inspect tg-weather-bot | grep -A 10 Health
```

## 🔒 安全建议

1. **保护 .env 文件**
   ```bash
   chmod 600 .env  # 只有所有者可以读写
   ```

2. **使用非 root 用户**
   - Dockerfile 已配置使用非特权用户 `botuser` 运行

3. **定期更新依赖**
   ```bash
   # 更新基础镜像和依赖
   docker compose build --no-cache
   docker compose up -d
   ```

4. **备份 .env 文件**
   ```bash
   cp .env .env.backup
   ```

## 🐛 故障排查

### 问题：容器启动后立即退出
```bash
# 查看完整日志
docker compose logs

# 常见原因：
# 1. BOT_TOKEN 未设置或无效
# 2. Python 代码有语法错误
```

### 问题：无法连接到 Telegram
```bash
# 检查网络连接
docker exec tg-weather-bot ping -c 3 api.telegram.org

# 如果无法连接，可能需要配置代理
```

### 问题：天气 API 返回 401
```bash
# 检查 WEATHER_API_KEY 是否正确
docker exec tg-weather-bot printenv WEATHER_API_KEY

# 运行测试脚本
docker exec tg-weather-bot python test_api.py
```

### 问题：定时任务不工作
```bash
# 检查时区设置
docker exec tg-weather-bot date

# 检查 ADMIN_CHAT_ID 是否设置
docker compose logs | grep "ADMIN_CHAT_ID"
```

## 🔧 高级配置

### 修改资源限制
编辑 `docker-compose.yml`：
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'      # 最多使用 1 个 CPU 核心
      memory: 512M     # 最多使用 512MB 内存
```

### 添加数据持久化
如果需要保存日志文件到宿主机：
```yaml
volumes:
  - ./logs:/app/logs
```

### 配置时区
在 `docker-compose.yml` 中添加：
```yaml
environment:
  - TZ=Asia/Shanghai
```

## 📞 支持

如有问题，请检查：
1. Docker 日志：`docker compose logs`
2. 容器状态：`docker compose ps`
3. 系统资源：`docker stats`

## 🎉 完成

你的 Telegram 机器人现在应该在服务器上稳定运行了！

测试功能：
- ✅ 发送 `/start` 查看欢迎消息
- ✅ 发送 `/weather` 获取天气信息
- ✅ 等待明天早上 8:00 查看是否收到自动问候
