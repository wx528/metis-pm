# Project Manager System - Docker Compose 管理
# 统一使用 docker-compose.yml，通过 .env 控制开发/生产行为

COMPOSE      = docker compose
BACKEND_SERVICE  = pm-backend
FRONTEND_SERVICE = pm-frontend

.PHONY: up up-build restart logs logs-front logs-all stop down clean test lint build tag release help

# 默认目标：启动并查看日志
up:
	@echo "正在启动服务..."
	$(COMPOSE) up -d

# 重新构建并启动
up-build:
	@echo "正在重新构建并启动..."
	$(COMPOSE) up -d --build

# 重启
restart:
	@echo "正在重启服务..."
	$(COMPOSE) restart
	$(MAKE) logs

# 查看 backend 日志
logs:
	@echo "正在连接到 $(BACKEND_SERVICE) 的日志流..."
	docker logs $(BACKEND_SERVICE) -f

# 查看 frontend 日志
logs-front:
	@echo "正在连接到 $(FRONTEND_SERVICE) 的日志流..."
	docker logs $(FRONTEND_SERVICE) -f

# 查看所有服务日志
logs-all:
	@echo "正在查看所有服务日志..."
	$(COMPOSE) logs -f

# 停止服务（保留容器）
stop:
	@echo "正在停止服务..."
	$(COMPOSE) stop

# 停止并移除容器
down:
	@echo "正在停止并移除容器..."
	$(COMPOSE) down

# 清理容器、卷及孤立资源（慎用：会删除数据卷）
clean:
	@echo "正在彻底清理..."
	$(COMPOSE) down -v --remove-orphans

# ─── 开发 & CI 命令 ────────────────────────────────────

# 运行后端测试
test:
	@echo "运行后端测试..."
	cd backend && pytest tests/ -v --tb=short

# 代码检查
lint:
	@echo "检查后端代码..."
	cd backend && pip install -q ruff && ruff check . --ignore=E501,F401,F841 --quiet
	@echo "检查前端代码..."
	cd frontend && npx tsc --noEmit

# 构建 Docker 镜像（本地）
build:
	@echo "构建 Docker 镜像..."
	$(COMPOSE) build

# 打 tag 并推送（触发 CI 构建）
tag:
	@read -p "输入版本号 (如 1.3.1): " ver; \
	echo "版本: v$$ver"; \
	git tag v$$ver && git push origin v$$ver

# 发布：更新 VERSION + tag + push
release:
	@read -p "输入版本号 (如 1.3.1): " ver; \
	echo $$ver > VERSION; \
	git add VERSION && git commit -m "release: v$$ver"; \
	git tag v$$ver && git push origin main v$$ver

# 帮助
help:
	@echo "可用命令："
	@echo ""
	@echo "  Docker 服务："
	@echo "  make up         - 启动所有服务"
	@echo "  make up-build   - 重新构建并启动所有服务"
	@echo "  make restart    - 重启服务并进入日志监控"
	@echo "  make logs       - 查看 $(BACKEND_SERVICE) 日志"
	@echo "  make logs-front - 查看 $(FRONTEND_SERVICE) 日志"
	@echo "  make logs-all   - 查看所有服务日志"
	@echo "  make stop       - 停止服务（保留容器）"
	@echo "  make down       - 停止并移除容器"
	@echo "  make clean      - 清理容器、卷及孤立资源（慎用）"
	@echo ""
	@echo "  开发 & CI："
	@echo "  make test       - 运行后端测试"
	@echo "  make lint       - 代码检查（ruff + tsc）"
	@echo "  make build      - 构建 Docker 镜像"
	@echo "  make tag        - 打版本 tag 并推送（触发 CI）"
	@echo "  make release    - 更新 VERSION + commit + tag + push"
