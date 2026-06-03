# Dockerfile 模板

当仓库没有 Dockerfile 时，根据项目类型生成。所有模板遵循最佳实践：
- 多阶段构建
- 非 root 用户
- 最小化基础镜像
- HEALTHCHECK 指令
- 固定版本标签

---

## Node.js (Express / Fastify / NestJS / Koa)

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && cp -R node_modules /prod_modules
RUN npm ci
COPY . .
RUN npm run build 2>/dev/null || true

FROM node:20-alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=builder /prod_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./
COPY --from=builder /app/src ./src
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/health || exit 1
CMD ["node", "dist/index.js"]
```

> **适配说明**：
> - 端口根据 `package.json` 中的 `PORT` 或代码检测调整
> - 如果没有 build 步骤，去掉 `npm run build` 和 `dist` 目录，直接 `COPY src`
> - 如果用 `yarn`/`pnpm`，替换对应包管理器命令
> - NestJS 启动命令通常为 `node dist/main.js`

---

## Python (FastAPI / Flask / Django)

### FastAPI / Flask

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Django

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN python manage.py collectstatic --noinput 2>/dev/null || true
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "config.wsgi:application"]
```

> **适配说明**：
> - Django 的 WSGI module 路径根据项目结构调整
> - 如果有 `pyproject.toml` 用 `pip install .` 替代 `requirements.txt`
> - Poetry 项目：先 `poetry export -f requirements.txt` 再安装

---

## Go

```dockerfile
FROM golang:1.22-alpine AS builder
RUN apk add --no-cache git ca-certificates
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app/server ./cmd/server

FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/server /server
USER nonroot:nonroot
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD ["/server", "--health-check"]
ENTRYPOINT ["/server"]
```

> **适配说明**：
> - `./cmd/server` 路径根据实际 main package 位置调整
> - 如果有 `main.go` 在根目录，用 `.` 替代
> - distroless 镜像无 shell，如需调试可用 `alpine` 替代
> - HEALTHCHECK 在 distroless 中不支持 CMD shell 形式，K8s probe 代替

---

## Java (Spring Boot / Quarkus)

### Spring Boot (Maven)

```dockerfile
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY pom.xml mvnw ./
COPY .mvn .mvn
RUN chmod +x mvnw && ./mvnw dependency:go-offline -B
COPY src src
RUN ./mvnw package -DskipTests -B && \
    java -Djarmode=layertools -jar target/*.jar extract --destination /extracted

FROM eclipse-temurin:21-jre-alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=builder /extracted/dependencies/ ./
COPY --from=builder /extracted/spring-boot-loader/ ./
COPY --from=builder /extracted/snapshot-dependencies/ ./
COPY --from=builder /extracted/application/ ./
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
```

### Spring Boot (Gradle)

```dockerfile
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY build.gradle* settings.gradle* gradlew ./
COPY gradle gradle
RUN chmod +x gradlew && ./gradlew dependencies --no-daemon
COPY src src
RUN ./gradlew bootJar --no-daemon -x test

FROM eclipse-temurin:21-jre-alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["java", "-jar", "app.jar"]
```

---

## Rust

```dockerfile
FROM rust:1.77-alpine AS builder
RUN apk add --no-cache musl-dev
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main(){}" > src/main.rs && cargo build --release && rm -rf src
COPY . .
RUN touch src/main.rs && cargo build --release

FROM alpine:3.19
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/target/release/<binary-name> /usr/local/bin/app
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/health || exit 1
CMD ["app"]
```

> **适配说明**：`<binary-name>` 替换为 `Cargo.toml` 中 `[[bin]]` 的 name 或 package name

---

## Ruby (Rails)

```dockerfile
FROM ruby:3.3-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY Gemfile Gemfile.lock ./
RUN bundle config set --local without 'development test' && bundle install
COPY . .
RUN SECRET_KEY_BASE=placeholder bundle exec rails assets:precompile 2>/dev/null || true

FROM ruby:3.3-slim
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app
COPY --from=builder /usr/local/bundle /usr/local/bundle
COPY --from=builder /app .
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD ruby -e "require 'net/http'; Net::HTTP.get(URI('http://localhost:3000/health'))" || exit 1
CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0"]
```

---

## .dockerignore（通用）

无论哪种语言，都应生成 `.dockerignore`：

```text
.git
.gitignore
.env
.env.*
node_modules
__pycache__
*.pyc
.pytest_cache
.mypy_cache
target/debug
target/release/deps
target/release/build
*.log
.DS_Store
.vscode
.idea
*.md
!README.md
docker-compose*.yml
Dockerfile
.dockerignore
tests/
test/
spec/
coverage/
.github/
```
