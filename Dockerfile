# 使用官方 Python 3.10 精简版镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# 防止 Python 生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE=1
# 确保 Python 输出直接发送到终端，不缓冲
ENV PYTHONUNBUFFERED=1

# 安装系统工具（用于健康检查）
RUN apt-get update && \
    apt-get install -y --no-install-recommends procps && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY main.py .
COPY handlers.py .
COPY services.py .
COPY jobs.py .
COPY price_monitor.py .

# 创建非 root 用户运行应用（安全最佳实践）
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# 切换到非 root 用户
USER botuser

# 默认启动命令（可在 docker-compose 中覆盖）
CMD ["python", "main.py"]
