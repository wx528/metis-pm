# Project Manager System - Docker Compose 管理
# 统一使用 docker-compose.yml，通过 .env 控制开发/生产行为

COMPOSE      = docker compose
BACKEND_SERVICE  = pm-backend
FRONTEND_SERVICE = pm-frontend

.PHONY: up up-build restart logs logs-front logs-all stop down clean help

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

# 帮助
help:
	@echo "可用命令："
	@echo "  make up         - 启动所有服务"
	@echo "  make up-build   - 重新构建并启动所有服务"
	@echo "  make restart    - 重启服务并进入日志监控"
	@echo "  make logs       - 查看 $(BACKEND_SERVICE) 日志"
	@echo "  make logs-front - 查看 $(FRONTEND_SERVICE) 日志"
	@echo "  make logs-all   - 查看所有服务日志"
	@echo "  make stop       - 停止服务（保留容器）"
	@echo "  make down       - 停止并移除容器"
	@echo "  make clean      - 清理容器、卷及孤立资源（慎用）"
