# 🐳 Docker Compose 使用说明

本项目包含两个服务，都可以通过 Docker Compose 管理。

## 📦 服务列表

1. **telegram-bot** - Telegram 天气机器人
   - 提供天气查询功能
   - 每天早上 8:00 发送早安问候
   - 容器名：`tg-weather-bot`

2. **price-monitor** - 价差监控服务
   - 实时监控 TSLAX 现货/合约价差
   - 价差超过阈值时推送通知
   - 容器名：`tg-price-monitor`

## 🚀 常用命令

### 启动所有服务
```bash
docker compose up -d
```

### 启动指定服务
```bash
# 只启动天气机器人
docker compose up -d telegram-bot

# 只启动价差监控
docker compose up -d price-monitor
```

### 停止服务
```bash
# 停止所有服务
docker compose down

# 停止指定服务
docker compose stop telegram-bot
docker compose stop price-monitor
```

### 重启服务
```bash
# 重启所有服务
docker compose restart

# 重启指定服务
docker compose restart price-monitor
```

### 查看服务状态
```bash
docker compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker compose logs -f

# 查看指定服务日志
docker compose logs -f telegram-bot
docker compose logs -f price-monitor

# 查看最近 100 行日志
docker compose logs --tail=100 price-monitor
```

### 重新构建镜像
```bash
# 修改代码后，重新构建并启动
docker compose up -d --build

# 只重新构建，不启动
docker compose build
```

## ⚙️ 配置修改

所有配置都在 `.env` 文件中：

```bash
# 编辑配置
nano .env

# 修改后重启服务使配置生效
docker compose restart
```

### 价差监控配置示例

```env
# 监控币对
MONITOR_SYMBOL=TSLAX_USDT

# 价差阈值（百分比）
PRICE_DIFF_THRESHOLD=0.5

# 使用百分比
USE_PERCENTAGE=True

# 检查间隔（秒）
CHECK_INTERVAL=1

# 通知冷却时间（秒）
COOLDOWN_SECONDS=300
```

## 🔍 监控和调试

### 查看容器资源使用
```bash
docker stats tg-weather-bot tg-price-monitor
```

### 进入容器内部
```bash
# 进入天气机器人容器
docker exec -it tg-weather-bot /bin/bash

# 进入价差监控容器
docker exec -it tg-price-monitor /bin/bash
```

### 查看健康状态
```bash
docker inspect tg-price-monitor | grep -A 10 Health
```

## 🛠️ 故障排查

### 问题：服务无法启动

1. 查看日志
   ```bash
   docker compose logs telegram-bot
   docker compose logs price-monitor
   ```

2. 检查 .env 配置是否正确

3. 检查端口是否被占用

### 问题：WebSocket 连接失败

检查代理配置：
```bash
# 如果服务器不需要代理，删除 docker-compose.yml 中的这几行：
environment:
  - HTTP_PROXY=http://localhost:7890
  - HTTPS_PROXY=http://localhost:7890
```

### 问题：Telegram 推送失败

1. 检查 BOT_TOKEN 和 ADMIN_CHAT_ID 是否正确
2. 检查网络连接
3. 查看详细错误日志

## 📊 日志管理

日志自动轮转：
- 单个日志文件最大：10MB
- 最多保留：3 个文件
- 自动清理旧日志

手动清理日志：
```bash
docker compose down
docker system prune -f
docker compose up -d
```

## 🔄 更新部署

```bash
# 1. 停止服务
docker compose down

# 2. 拉取最新代码（如果使用 Git）
git pull

# 3. 重新构建并启动
docker compose up -d --build
```

## 📝 备份和恢复

### 备份配置
```bash
cp .env .env.backup
```

### 导出日志
```bash
docker compose logs > logs_backup.txt
```

## 🌐 服务器部署

### 上传到服务器
```bash
scp -r /home/kenijima/usr/work/GoPlus/new/tg_bot user@server:/path/to/
```

### 在服务器上运行
```bash
cd /path/to/tg_bot

# 确保 .env 配置正确
vim .env

# 启动服务
docker compose up -d

# 查看状态
docker compose ps
docker compose logs -f
```

## 🎯 生产环境建议

1. **设置自动重启**（已配置）
   - `restart: unless-stopped`

2. **监控服务健康**
   ```bash
   # 添加到 crontab 定期检查
   */5 * * * * cd /path/to/tg_bot && docker compose ps | grep -q "healthy" || docker compose restart
   ```

3. **定期更新**
   ```bash
   # 每周自动更新
   0 3 * * 0 cd /path/to/tg_bot && git pull && docker compose up -d --build
   ```

4. **日志监控**
   - 使用 `docker compose logs -f` 监控实时日志
   - 或者使用日志收集工具（如 ELK Stack）

## ⚡ 快速参考

| 操作 | 命令 |
|------|------|
| 启动所有 | `docker compose up -d` |
| 停止所有 | `docker compose down` |
| 重启所有 | `docker compose restart` |
| 查看状态 | `docker compose ps` |
| 查看日志 | `docker compose logs -f` |
| 重新构建 | `docker compose up -d --build` |
| 只启动监控 | `docker compose up -d price-monitor` |
| 停止监控 | `docker compose stop price-monitor` |
