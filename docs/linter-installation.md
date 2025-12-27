# Linter 安装指南

本文档介绍如何安装和配置 Wise Code Watchers 支持的各种 Linter 工具。

## 支持的 Linter

- **Python**: Ruff
- **JavaScript/TypeScript**: ESLint
- **Go**: golangci-lint
- **Ruby**: RuboCop
- **Java**: Checkstyle, SpotBugs

## 安装指南

### Python - Ruff

Ruff 是一个快速的 Python linter,可以替代多个现有的工具。

```bash
# 使用 pip 安装
pip install ruff

# 使用 pipx 安装(推荐)
pipx install ruff

# 使用 conda 安装
conda install -c conda-forge ruff
```

**配置文件**: `pyproject.toml` 或 `.ruff.toml`

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = ["E501"]
```

### JavaScript/TypeScript - ESLint

ESLint 是 JavaScript 和 TypeScript 的主流 linter。

```bash
# 使用 npm 安装
npm install -D eslint

# 使用 yarn 安装
yarn add -D eslint

# 使用 pnpm 安装
pnpm add -D eslint
```

**配置文件**: `.eslintrc.json` 或 `eslint.config.js`

```json
{
  "env": {
    "browser": true,
    "es2021": true,
    "node": true
  },
  "extends": "eslint:recommended",
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module"
  },
  "rules": {
    "no-unused-vars": "warn",
    "no-console": "off"
  }
}
```

### Go - golangci-lint

golangci-lint 是 Go 的聚合 linter,集成了多个 linter。

```bash
# 使用 curl 安装
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin

# 使用 Homebrew 安装 (macOS)
brew install golangci-lint

# 使用 Chocolatey 安装 (Windows)
choco install golangci-lint

# 使用 Scoop 安装 (Windows)
scoop bucket add golangci-lint https://github.com/golangci/golangci-lint
scoop install golangci-lint
```

**配置文件**: `.golangci.yml` 或 `.golangci.yaml`

```yaml
linters:
  enable:
    - govet
    - errcheck
    - staticcheck
    - unused
    - gosimple
    - ineffassign

linters-settings:
  govet:
    check-shadowing: true
```

### Ruby - RuboCop

RuboCop 是 Ruby 的静态代码分析工具。

```bash
# 使用 gem 安装
gem install rubocop

# 在 Gemfile 中添加
group :development do
  gem 'rubocop', require: false
end
```

**配置文件**: `.rubocop.yml`

```yaml
AllCops:
  TargetRubyVersion: 3.0
  NewCops: enable

Style/Documentation:
  Enabled: false

Metrics/MethodLength:
  Max: 20
```

### Java - Checkstyle

Checkstyle 是 Java 的静态代码分析工具。

```bash
# 使用 Maven 添加依赖
<dependency>
  <groupId>com.puppycrawl.tools</groupId>
  <artifactId>checkstyle</artifactId>
  <version>10.12.0</version>
</dependency>

# 使用 Gradle 添加依赖
implementation 'com.puppycrawl.tools:checkstyle:10.12.0'
```

**配置文件**: `checkstyle.xml` 或 `sun_checks.xml`

```xml
<?xml version="1.0"?>
<!DOCTYPE module PUBLIC
    "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN"
    "https://checkstyle.org/dtds/configuration_1_3.dtd">
<module name="Checker">
  <property name="charset" value="UTF-8"/>
  <module name="TreeWalker">
    <module name="AvoidStarImport"/>
    <module name="UnusedImports"/>
    <module name="NeedBraces"/>
  </module>
</module>
```

### Java - SpotBugs

SpotBugs 是 Java 的静态分析工具,用于查找 Bug。

```bash
# 使用 Maven 添加插件
<plugin>
  <groupId>com.github.spotbugs</groupId>
  <artifactId>spotbugs-maven-plugin</artifactId>
  <version>4.7.3.6</version>
</plugin>

# 使用 Gradle 添加插件
plugins {
  id 'com.github.spotbugs' version '6.0.0'
}
```

## 在 Wise Code Watchers 中使用

安装完 Linter 后,需要在项目的 `.env` 文件中配置:

```bash
# Linter 可执行文件路径 (可选,如果不在 PATH 中)
RUFF_PATH=/usr/local/bin/ruff
ESLINT_PATH=/usr/local/bin/eslint
GOLANGCI_LINT_PATH=/usr/local/bin/golangci-lint
RUBOCOP_PATH=/usr/local/bin/rubocop
CHECKSTYLE_PATH=/usr/local/bin/checkstyle
SPOTBUGS_PATH=/usr/local/bin/spotbugs
```

## 验证安装

安装完成后,可以验证 Linter 是否正确安装:

```bash
# Python
ruff --version

# JavaScript/TypeScript
eslint --version

# Go
golangci-lint --version

# Ruby
rubocop --version

# Java
checkstyle -version
spotbugs -version
```

## Docker 环境安装

如果使用 Docker 部署,需要在 `Dockerfile` 中添加安装命令:

```dockerfile
# 安装 Python Linter
RUN pip install ruff

# 安装 JavaScript/TypeScript Linter
RUN npm install -g eslint

# 安装 Go Linter
RUN curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b /usr/local/bin

# 安装 Ruby Linter
RUN gem install rubocop

# 安装 Java Linter
RUN apt-get update && apt-get install -y checkstyle spotbugs
```

## 故障排除

### 权限问题

如果遇到权限问题,可能需要使用 `sudo` 安装:

```bash
sudo pip install ruff
sudo npm install -g eslint
```

### 路径问题

确保 Linter 的可执行文件在 `PATH` 中:

```bash
# 查看当前 PATH
echo $PATH

# 添加到 PATH (临时)
export PATH=$PATH:/usr/local/bin

# 添加到 PATH (永久,添加到 ~/.bashrc 或 ~/.zshrc)
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
source ~/.bashrc
```

### 版本兼容性

确保使用的 Linter 版本与项目兼容:

```bash
# 查看已安装版本
ruff --version
eslint --version
```

## 更多资源

- [Ruff 官方文档](https://docs.astral.sh/ruff/)
- [ESLint 官方文档](https://eslint.org/)
- [golangci-lint 官方文档](https://golangci-lint.run/)
- [RuboCop 官方文档](https://rubocop.org/)
- [Checkstyle 官方文档](https://checkstyle.org/)
- [SpotBugs 官方文档](https://spotbugs.github.io/)
