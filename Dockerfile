# 使用官方 Python 3.12 镜像作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 配置 pip 使用国内镜像源 (清华大学源)
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 配置 APT 使用国内镜像源 (阿里云源)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖 (使用国内镜像源)
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Semgrep (使用国内镜像源)
RUN pip install semgrep

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /app/pr_export /app/workspace /app/logs

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# 运行应用
CMD ["python", "app.py"]
