# Kubernetes 部署清单模板

生成 K8s manifests 时必须包含以下最佳实践。默认把 YAML 文件放在 `.volcengine/k8s/` 目录下；远程 Git URL 的临时 clone 可以先使用 `/tmp`，但最终状态和可复用文件应落在仓库的 `.volcengine/` 下。

---

## 1. Namespace

```yaml
# k8s/00-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: <repo-name>
  labels:
    project: <repo-name>
    managed-by: volcengine-deploy
```

---

## 2. ConfigMap & Secret

Generate ConfigMap and Secret only after resolving runtime configuration. Values can come from `.env.example`, user input, IaC outputs, or CLI-created dependency outputs. Do not apply manifests that still contain placeholder connection strings.

```yaml
# k8s/01-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: <repo-name>-config
  namespace: <repo-name>
data:
  # 非敏感配置
  NODE_ENV: "production"
  PORT: "<port>"
  LOG_LEVEL: "info"
---
apiVersion: v1
kind: Secret
metadata:
  name: <repo-name>-secret
  namespace: <repo-name>
type: Opaque
stringData:
  # 敏感配置（数据库连接等）；生成时替换为真实值，禁止保留占位符
  DATABASE_URL: "<resolved-database-url>"
  REDIS_URL: "<resolved-redis-url>"
```

Before `kubectl apply`, grep for unresolved placeholders:

```bash
! rg -n "<connection-string>|<redis-connection-string>|<resolved-" .volcengine/k8s
```

---

## 3. Deployment

```yaml
# k8s/02-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: <repo-name>
  namespace: <repo-name>
  labels:
    app: <repo-name>
    project: <repo-name>
    managed-by: volcengine-deploy
spec:
  replicas: 2
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: <repo-name>
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: <repo-name>
    spec:
      # 反亲和：分散到不同节点
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - <repo-name>
              topologyKey: kubernetes.io/hostname
      # 优雅终止
      terminationGracePeriodSeconds: 30
      # VKE 节点通常为 linux/amd64；构建/推送镜像时必须与节点架构一致
      nodeSelector:
        kubernetes.io/arch: amd64
      # CR 免密拉取依赖 VKE 插件 cr-credential-controller；不要把 CR 密码写入业务 Secret
      imagePullSecrets:
      - name: volcengine-cr-credential
      containers:
      - name: <repo-name>
        image: <cr-endpoint>/<namespace>/<repo-name>:<tag>
        ports:
        - containerPort: <port>
          name: http
          protocol: TCP
        # 环境变量
        envFrom:
        - configMapRef:
            name: <repo-name>-config
        - secretRef:
            name: <repo-name>-secret
        # 资源限制
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: "1"
            memory: 512Mi
        # 存活探针：容器是否还活着；仅在确认应用提供 health path 时使用 httpGet
        livenessProbe:
          httpGet:
            path: <health-path>
            port: http
          initialDelaySeconds: 15
          periodSeconds: 20
          timeoutSeconds: 3
          failureThreshold: 3
        # 就绪探针：是否可以接收流量；如果没有 HTTP health path，改用下方 tcpSocket 模板
        readinessProbe:
          httpGet:
            path: <health-path>
            port: http
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        # 启动探针：慢启动应用（Java 等）
        startupProbe:
          httpGet:
            path: <health-path>
            port: http
          initialDelaySeconds: 10
          periodSeconds: 5
          failureThreshold: 30
        # 安全上下文
        securityContext:
          runAsNonRoot: true
          readOnlyRootFilesystem: false
          allowPrivilegeEscalation: false
```

> **适配说明**：
> - 不要默认假设应用有 `/health` 端点；先从代码、Dockerfile HEALTHCHECK、框架默认值或用户输入确定 `health_path`
> - 如果应用没有 HTTP health path，使用 `tcpSocket` 探针替代 `httpGet`
> - Java/Spring Boot 应用 `startupProbe.failureThreshold` 可能需要增大（启动慢）
> - 资源 limits 根据应用类型调整（Java 通常需要更多内存）

TCP probe fallback:

```yaml
livenessProbe:
  tcpSocket:
    port: http
  initialDelaySeconds: 15
  periodSeconds: 20
readinessProbe:
  tcpSocket:
    port: http
  initialDelaySeconds: 5
  periodSeconds: 10
startupProbe:
  tcpSocket:
    port: http
  periodSeconds: 5
  failureThreshold: 30
```

---

## 4. Service

```yaml
# k8s/03-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: <repo-name>
  namespace: <repo-name>
  labels:
    app: <repo-name>
  annotations:
    # 火山引擎 CLB 注解
    service.beta.kubernetes.io/volcengine-loadbalancer-subnet-id: "<subnet-id>"
    service.beta.kubernetes.io/volcengine-loadbalancer-address-type: "PUBLIC"
spec:
  type: LoadBalancer
  selector:
    app: <repo-name>
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```

> **说明**：
> - `LoadBalancer` 类型会自动创建火山引擎 CLB
> - 需要指定 subnet-id 注解，CLB 才能正确创建
> - 如果不需要公网访问，改为 `ClusterIP` 类型

---

## 5. HPA（水平自动扩缩容）

```yaml
# k8s/04-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: <repo-name>
  namespace: <repo-name>
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: <repo-name>
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60
```

---

## 6. PDB（Pod Disruption Budget）

```yaml
# k8s/05-pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: <repo-name>
  namespace: <repo-name>
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: <repo-name>
```

---

## 7. NetworkPolicy（可选，推荐）

```yaml
# k8s/06-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: <repo-name>-policy
  namespace: <repo-name>
spec:
  podSelector:
    matchLabels:
      app: <repo-name>
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # 仅允许来自 CLB 的入站流量
  - ports:
    - port: <port>
      protocol: TCP
  egress:
  # 允许 DNS 解析
  - to: []
    ports:
    - port: 53
      protocol: UDP
    - port: 53
      protocol: TCP
  # 允许访问数据库等内网服务
  - to:
    - ipBlock:
        cidr: 172.16.0.0/16
```

---

## 文件组织

生成的 K8s 清单按编号排序，确保按顺序 apply：

```text
k8s/
├── 00-namespace.yaml
├── 01-config.yaml
├── 02-deployment.yaml
├── 03-service.yaml
├── 04-hpa.yaml
├── 05-pdb.yaml
└── 06-network-policy.yaml    # 可选
```

一键部署：
```bash
kubectl apply -f .volcengine/k8s/
```
