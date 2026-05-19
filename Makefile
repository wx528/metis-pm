# 变量定义
COMPOSE      = docker compose
COMPOSE_DEV  = docker compose -f docker-compose.dev.yml
BACKEND_SERVICE  = pm-backend
FRONTEND_SERVICE = pm-frontend

.PHONY: dev up restart rebuild logs logs-front logs-all stop down clean help

# 默认目标：启动并查看日志
dev: restart logs

# 启动生产环境
up:
	@echo "正在启动生产环境..."
	$(COMPOSE) up -d

# 重启开发环境
restart:
	@echo "正在启动开发环境..."
	$(COMPOSE_DEV) up -d
	$(MAKE) logs

# 重新构建并启动
rebuild:
	@echo "正在重新构建并启动开发环境..."
	$(COMPOSE_DEV) up -d --build
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
	$(COMPOSE_DEV) logs -f

# 停止开发环境
stop:
	@echo "正在停止开发环境..."
	$(COMPOSE_DEV) stop

# 停止并移除容器
down:
	@echo "正在停止并移除开发环境容器..."
	$(COMPOSE_DEV) down

# 清理容器、卷及孤立资源（慎用）
clean:
	@echo "正在彻底清理开发环境..."
	$(COMPOSE_DEV) down -v --remove-orphans

# 帮助
help:
	@echo "可用命令："
	@echo "  make dev         - 启动开发环境并自动进入日志监控 (推荐)"
	@echo "  make up          - 启动生产环境"
	@echo "  make restart     - 重启开发环境"
	@echo "  make rebuild     - 强制重新构建并启动开发环境"
	@echo "  make logs        - 查看 $(BACKEND_SERVICE) 日志"
	@echo "  make logs-front  - 查看 $(FRONTEND_SERVICE) 日志"
	@echo "  make logs-all    - 查看所有服务日志"
	@echo "  make stop        - 停止开发环境"
	@echo "  make down        - 停止并移除开发环境容器"
	@echo "  make clean       - 清理容器、卷及孤立资源（慎用）"
