# ─── Stage 1: 构建 ─────────────────────────────────────
FROM node:20-alpine AS builder

ARG APP_VERSION=0.0.0
ARG VITE_API_URL=/api/v1
ENV APP_VERSION=$APP_VERSION
ENV VITE_API_URL=$VITE_API_URL

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ─── Stage 2: 运行时 ──────────────────────────────────
FROM nginx:alpine

# 安全：非 root 监听端口 > 1024
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
