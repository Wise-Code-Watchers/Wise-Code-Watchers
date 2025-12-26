#!/bin/bash
# 智能备份脚本 - 遵守 .gitignore 规则

set -e  # 遇到错误立即退出

# 配置
PROJECT_DIR="${PROJECT_DIR:-/home/landasika/Wise-Code-Watchers}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_FILE:-wise_code_watchers_${TIMESTAMP}.tar.gz}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Wise Code Watchers 智能备份脚本${NC}"
echo ""

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 错误: 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi

echo -e "${BLUE}📁 项目目录:${NC} $PROJECT_DIR"
echo -e "${BLUE}📦 输出文件:${NC} $BACKUP_FILE"
echo ""

# 检查是否已存在输出文件
if [ -f "$BACKUP_FILE" ]; then
    echo -en "${YELLOW}⚠️  文件已存在，是否覆盖? (y/N): ${NC}"
    read -r response
    if [ "$response" != "y" ]; then
        echo -e "${RED}❌ 已取消${NC}"
        exit 0
    fi
    rm -f "$BACKUP_FILE"
fi

# 切换到项目目录
cd "$PROJECT_DIR"

echo -e "${BLUE}🔍 开始备份（遵守 .gitignore 规则）...${NC}"
echo ""

# 方法1: 使用 git archive（最干净）
if [ -d ".git" ]; then
    echo -e "${GREEN}✓ 使用 git archive 创建备份${NC}"

    # 获取当前分支名
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

    # 使用 git archive 创建压缩包
    # 这会自动遵守 .gitignore
    git archive --format=tar HEAD | gzip > "$BACKUP_FILE"

    echo ""
    echo -e "${GREEN}✅ 备份完成!${NC}"
    echo -e "   分支: ${CURRENT_BRANCH}"
    echo -e "   文件: ${BACKUP_FILE}"
    echo -e "   大小: $(du -h "$BACKUP_FILE" | cut -f1)"
else
    # 方法2: 手动过滤
    echo -e "${YELLOW}⚠️  不是 git 仓库，使用手动过滤${NC}"

    # 创建临时目录
    TEMP_DIR=$(mktemp -d)
    echo -e "${BLUE}   创建临时目录: ${TEMP_DIR}${NC}"

    # 使用 rsync 复制并排除文件
    rsync -av \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.py[cod]' \
        --exclude='*.so' \
        --exclude='.Python' \
        --exclude='build/' \
        --exclude='dist/' \
        --exclude='*.egg-info/' \
        --exclude='venv/' \
        --exclude='.venv/' \
        --exclude='.idea/' \
        --exclude='.vscode/' \
        --exclude='*.swp' \
        --exclude='*.log' \
        --exclude='pr_export/' \
        --exclude='secret/' \
        --exclude='*.tar.gz' \
        --exclude='.env*' \
        "$PROJECT_DIR/" "$TEMP_DIR/"

    # 创建压缩包
    echo -e "${BLUE}   创建压缩包...${NC}"
    tar -czf "$BACKUP_FILE" -C "$TEMP_DIR" .

    # 清理临时目录
    rm -rf "$TEMP_DIR"

    echo ""
    echo -e "${GREEN}✅ 备份完成!${NC}"
    echo -e "   文件: ${BACKUP_FILE}"
    echo -e "   大小: $(du -h "$BACKUP_FILE" | cut -f1)"
fi

echo ""
echo -e "${GREEN}🎉 备份成功创建!${NC}"
echo -e "   位置: ${BACKUP_FILE}"
echo ""
echo -e "${BLUE}💡 提示: 可以使用以下命令恢复备份${NC}"
echo -e "   tar -xzf ${BACKUP_FILE} -C /target/directory"
