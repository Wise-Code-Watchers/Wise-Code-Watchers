# PR Review Bot - Multi-language Linter Environment
# Supports: Python, TypeScript/JavaScript, Java, Go, Ruby

FROM python:3.12-slim

LABEL maintainer="PR Review Bot"
LABEL description="Multi-language PR review environment with linters"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    unzip \
    ca-certificates \
    gnupg \
    # For Node.js
    nodejs \
    npm \
    # For Ruby
    ruby \
    ruby-dev \
    # For Java (checkstyle)
    default-jre-headless \
    # Build tools
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Install Go
# ============================================
ENV GO_VERSION=1.21.5
RUN curl -LO https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz \
    && rm go${GO_VERSION}.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"
ENV GOPATH="/root/go"

# ============================================
# Install Linters
# ============================================

# Python - Ruff (fast Python linter)
RUN pip install --no-cache-dir ruff

# TypeScript/JavaScript - ESLint
RUN npm install -g eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin

# Go - golangci-lint
RUN curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b /usr/local/bin v1.55.2

# Ruby - RuboCop
RUN gem install rubocop --no-document

# Java - Checkstyle (code style)
ENV CHECKSTYLE_VERSION=10.12.5
RUN wget -q https://github.com/checkstyle/checkstyle/releases/download/checkstyle-${CHECKSTYLE_VERSION}/checkstyle-${CHECKSTYLE_VERSION}-all.jar \
    -O /usr/local/lib/checkstyle.jar \
    && echo '#!/bin/bash\njava -jar /usr/local/lib/checkstyle.jar "$@"' > /usr/local/bin/checkstyle \
    && chmod +x /usr/local/bin/checkstyle

# Java - SpotBugs (memory/resource leak detection)
ENV SPOTBUGS_VERSION=4.8.3
RUN wget -q https://github.com/spotbugs/spotbugs/releases/download/${SPOTBUGS_VERSION}/spotbugs-${SPOTBUGS_VERSION}.tgz \
    -O /tmp/spotbugs.tgz \
    && tar -xzf /tmp/spotbugs.tgz -C /opt \
    && ln -s /opt/spotbugs-${SPOTBUGS_VERSION}/bin/spotbugs /usr/local/bin/spotbugs \
    && rm /tmp/spotbugs.tgz

# ============================================
# Install Python Dependencies
# ============================================

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Copy Application Code
# ============================================
COPY . .

# ============================================
# Verify Linter Installation
# ============================================
RUN echo "Verifying linter installations..." \
    && ruff --version \
    && eslint --version \
    && golangci-lint --version \
    && rubocop --version \
    && checkstyle --version \
    && echo "All linters installed successfully!"

# ============================================
# Environment Variables
# ============================================
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["python", "app.py"]
