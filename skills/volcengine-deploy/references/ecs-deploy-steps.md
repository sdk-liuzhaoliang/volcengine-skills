# ECS Deployment Details

Detailed reference for the ECS branch of `volcengine-deploy`. The main `SKILL.md` owns the flow; this document holds build commands, command-channel patterns, and the systemd unit template.

> **Pitfall sources** — for ECS provisioning quirks (instance type availability, image search, Cloud Assistant agent boot delay, RunInstances password/EIP fields, RunCommand invocation name/result polling/timeout), consult `skills/volcengine-cli/references/ecs.md`.

---

## 1. Per-language build commands

Run inside the repo root. Output paths are relative.

### Go
```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
  go build -ldflags="-s -w" -o dist/server \
  $([ -d cmd ] && echo "./cmd/server" || echo ".")
```
**Artifact**: `dist/server` (statically linked, ~10–30 MB typical).

### Node.js
```bash
npm ci --only=production
[ -f tsconfig.json ] && npx tsc 2>/dev/null || true
```
**Artifact**: source dir + `node_modules/`. Bundle as a tarball before upload:
```bash
tar -czf dist/app.tar.gz --exclude='.git' --exclude='node_modules/.cache' .
```

### Python
```bash
python3 -m venv .venv
.venv/bin/pip install --no-cache-dir -r requirements.txt
```
**Artifact**: source dir + `.venv/`. Bundle:
```bash
tar -czf dist/app.tar.gz --exclude='.git' --exclude='.venv/lib/python*/site-packages/__pycache__' .
```

### Java (Maven)
```bash
./mvnw package -DskipTests -B
```
**Artifact**: `target/*-SNAPSHOT.jar` (or release JAR per project naming).

### Java (Gradle)
```bash
./gradlew bootJar --no-daemon -x test
```
**Artifact**: `build/libs/*.jar`.

### Rust
```bash
cargo build --release
```
**Artifact**: `target/release/<binary-name>` (binary name = package name in `Cargo.toml`).

### Ruby
```bash
bundle install --deployment --without development test
```
**Artifact**: source dir + `vendor/bundle/`. Bundle as tarball.

---

## 2. Command channel

New public ECS deployments must allocate an EIP. Ask the user whether to open SSH 22:

- If the user allows SSH and port 22 is reachable, SSH/scp can be used for upload and debugging.
- If the user declines SSH, SSH is blocked, or the connection is slow/unreliable, use Cloud Assistant.
- When creating an instance, install/enable Cloud Assistant so fallback is always available.

Only detect the outbound IP when the user chooses to open SSH 22. Application ports normally stay public, so they do not need a source-IP probe.

Before writing the SSH rule, detect the current outbound IP from the same machine that will run SSH and restrict port 22 to that CIDR when possible. Re-check before deployment if there was a delay; if the outbound IP changed, update the rule instead of troubleshooting a stale whitelist.

Keep SSH retries short. If `nc -zw5 "$eip" 22` fails or SSH does not connect promptly, switch to Cloud Assistant instead of waiting.

Use local wrappers for every Cloud Assistant command so examples cannot drift from the ECS CLI rules. `InvocationName` is required; keep it short, stable, and compliant with the naming rules in `skills/volcengine-cli/references/ecs.md`. `CommandContent` must be base64-encoded; `RunCommand` returns only scheduling metadata, so `run_cmd` submits the command and then polls the actual result.

```bash
submit_cmd() {
  local invocation_name="$1"
  local timeout_seconds="$2"
  local command_content="$3"
  local command_b64
  command_b64=$(printf '%s' "$command_content" | base64 | tr -d '\n')
  ve ecs RunCommand \
    --Type "Shell" \
    --InstanceIds.1 "$instance_id" \
    --InvocationName "$invocation_name" \
    --Timeout "$timeout_seconds" \
    --CommandContent "$command_b64"
}

wait_cmd_result() {
  local invocation_id="$1"
  local max_attempts="${2:-60}"
  local sleep_seconds="${3:-5}"
  local result result_status exit_code

  for _ in $(seq 1 "$max_attempts"); do
    result=$(ve ecs DescribeInvocationResults \
      --InvocationId "$invocation_id" \
      --InstanceId "$instance_id")
    result_status=$(echo "$result" | jq -r '.Result.InvocationResults[0].InvocationResultStatus // empty')
    exit_code=$(echo "$result" | jq -r '.Result.InvocationResults[0].ExitCode // empty')
    case "$result_status" in
      Success|Failed|Timeout)
        echo "$result"
        [ "$result_status" = "Success" ] && [ "$exit_code" = "0" ]
        return
        ;;
    esac
    sleep "$sleep_seconds"
  done

  echo "Timed out waiting for invocation $invocation_id" >&2
  return 124
}

run_cmd() {
  local response invocation_id
  response=$(submit_cmd "$@")
  invocation_id=$(echo "$response" | jq -r '.Result.InvocationId // empty')
  [ -n "$invocation_id" ] || { echo "$response"; return 1; }
  wait_cmd_result "$invocation_id"
}

cmd_output() {
  jq -r '.Result.InvocationResults[0].Output // ""' | base64 -d 2>/dev/null || true
}
```

### Cloud Assistant Pattern A — small files (< 1 MB)
Embed base64-encoded content in the command body. Suitable for binaries and config files.

```bash
encoded=$(base64 < dist/server | tr -d '\n')
run_cmd "upload-small" 300 "mkdir -p /opt/$repo_name && \
echo '$encoded' | base64 -d > /opt/$repo_name/server && \
chmod +x /opt/$repo_name/server"
```

> **Note**: Volcengine RunCommand's CommandContent has a size limit. For files larger than ~1 MB, use Pattern B, SSH/scp when SSH is allowed, or a user-provided artifact URL.

### Cloud Assistant Pattern B — large files via TOS pre-signed URL

`ve tos` is not available in all Volcengine CLI builds. If `tosutil` is installed and configured, upload the artifact with `tosutil`, generate a short-lived pre-signed download URL, then have the instance pull it via `wget`. If `tosutil` is unavailable, use SSH/scp when SSH is open, or ask the user for an existing HTTPS artifact URL.

```bash
# 1. Upload to TOS (bucket created or provided before this step)
tosutil cp dist/app.tar.gz "tos://$deploy_bucket/artifacts/$repo_name-$git_sha.tar.gz"

# 2. Pre-signed url (15 minute validity)
url=$(tosutil presign "tos://$deploy_bucket/artifacts/$repo_name-$git_sha.tar.gz" -vp=15min | tail -1)

# 3. Pull on the instance
run_cmd "upload-tos" 600 "mkdir -p /opt/$repo_name && \
wget -q -O /tmp/app.tar.gz '$url' && \
tar -xzf /tmp/app.tar.gz -C /opt/$repo_name && \
rm /tmp/app.tar.gz"
```

### Pre-flight: agent readiness
Before any `RunCommand`, confirm the Cloud Assistant agent is `Running`:

```bash
for _ in $(seq 1 24); do
  ca_status=$(ve ecs DescribeCloudAssistantStatus --InstanceIds.1 "$instance_id" \
    | jq -r '.Result.Instances[0].Status // empty')
  [ "$ca_status" = "Running" ] && break
  sleep 5
done
[ "$ca_status" = "Running" ] || { echo "Cloud Assistant not ready; reboot or wait"; exit 1; }
```

If the agent isn't running and the instance was just created without `--InstallRunCommandAgent true`, a reboot is required. Always pass `--InstallRunCommandAgent true` at `RunInstances` time to avoid this.

### Instance type retry

Use `DescribeAvailableResource` to build a short candidate list. If `RunInstances` reports the chosen type unavailable, sold out, or not found in the zone, try the next candidate automatically. Only stop after the candidate list is exhausted or the error is unrelated to capacity/type availability.

### RunInstances credentials and EIP fields

`RunInstances` requires either `--Password` or `--KeyPairName` even when SSH is not opened and Cloud Assistant will be used. For no-SSH deployments, generate a one-time strong password only for instance creation and do not print or persist it.

For inline EIP creation, `--EipAddress.ChargeType` accepts `PayByBandwidth`, `PayByTraffic`, or `PrePaid`. Do not pass values from other EIP APIs such as `PostPaidByBandwidth`.

### CLI ECS creation skeleton with inline EIP

This shape was verified in `cn-beijing` with a temporary VPC/subnet/security group, `veLinux 2.0 64 bit`, `ecs.r4i.large`, inline EIP, and Cloud Assistant. Query zone inventory first and substitute the IDs; do not hardcode this instance type outside validation.

```bash
name="deploy-$repo_name-$git_sha"
password="<generated-one-time-strong-password>"

# If this run just created VPC/SG resources, wait before creating child resources
# or writing rules. Otherwise short consistency windows can return
# InvalidVpc.InvalidStatus or InvalidSecurityGroup.InvalidStatus.
for _ in $(seq 1 30); do
  vpc_status=$(ve vpc DescribeVpcs --VpcIds.1 "$vpc_id" \
    | jq -r '.Result.Vpcs[0].Status // empty')
  [ "$vpc_status" = "Available" ] && break
  sleep 5
done

for _ in $(seq 1 30); do
  sg_seen=$(ve vpc DescribeSecurityGroups --SecurityGroupIds.1 "$sg_id" \
    | jq -r '.Result.SecurityGroups[0].SecurityGroupId // empty')
  [ "$sg_seen" = "$sg_id" ] && break
  sleep 5
done

# 1. DryRun validates parameters and creates nothing. A successful DryRun exits non-zero
# and prints DryRunOperation.
ve ecs RunInstances \
  --ZoneId "$zone_id" \
  --InstanceTypeId "$instance_type_id" \
  --ImageId "$image_id" \
  --NetworkInterfaces.1.SubnetId "$subnet_id" \
  --NetworkInterfaces.1.SecurityGroupIds.1 "$sg_id" \
  --SystemVolume.Size 40 \
  --SystemVolume.VolumeType ESSD_PL0 \
  --InstanceName "$name" \
  --HostName "$name" \
  --Password "$password" \
  --InstallRunCommandAgent true \
  --EipAddress.ChargeType PayByBandwidth \
  --EipAddress.BandwidthMbps 1 \
  --EipAddress.ReleaseWithInstance true \
  --Count 1 \
  --DryRun true

# 2. Create after DryRun passes.
create_json=$(ve ecs RunInstances \
  --ZoneId "$zone_id" \
  --InstanceTypeId "$instance_type_id" \
  --ImageId "$image_id" \
  --NetworkInterfaces.1.SubnetId "$subnet_id" \
  --NetworkInterfaces.1.SecurityGroupIds.1 "$sg_id" \
  --SystemVolume.Size 40 \
  --SystemVolume.VolumeType ESSD_PL0 \
  --InstanceName "$name" \
  --HostName "$name" \
  --Password "$password" \
  --InstallRunCommandAgent true \
  --EipAddress.ChargeType PayByBandwidth \
  --EipAddress.BandwidthMbps 1 \
  --EipAddress.ReleaseWithInstance true \
  --Count 1)
instance_id=$(printf '%s' "$create_json" | jq -r '.Result.InstanceIds[0]')

# 3. Poll until RUNNING and capture the EIP.
for _ in $(seq 1 60); do
  instance_json=$(ve ecs DescribeInstances --InstanceIds.1 "$instance_id")
  inst_status=$(printf '%s' "$instance_json" | jq -r '.Result.Instances[0].Status // empty')
  eip=$(printf '%s' "$instance_json" | jq -r '.Result.Instances[0].EipAddress.IpAddress // empty')
  [ "$inst_status" = "RUNNING" ] && [ -n "$eip" ] && break
  sleep 10
done

# 4. Confirm Cloud Assistant is available before using RunCommand.
for _ in $(seq 1 24); do
  ca_status=$(ve ecs DescribeCloudAssistantStatus --InstanceIds.1 "$instance_id" \
    | jq -r '.Result.Instances[0].Status // empty')
  [ "$ca_status" = "Running" ] && break
  sleep 5
done
[ "$ca_status" = "Running" ] || { echo "Cloud Assistant not ready"; exit 1; }
```

When `ReleaseWithInstance=true`, do not treat the inline EIP as an independent mandatory cleanup item. Delete the ECS instance first, then confirm the EIP is gone before deleting the security group, subnet, and VPC.

### Docker on veLinux and China networks

veLinux 2 is Debian-like, but `VERSION_CODENAME` may be `lyra`; do not use that value as the Docker official Debian repository codename. Prefer the system package:

```bash
apt-get update
apt-get install -y docker.io
systemctl enable --now docker
```

Docker Hub and GHCR may be slow or unreachable from China regions. Prefer Volcengine CR or a user-provided registry for deployment images. For temporary Docker Hub pulls, test currently available registry-mirror candidates such as `https://docker.1ms.run`, `https://dockerproxy.net`, `https://proxy.vvvv.ee`, and `https://dockerproxy.link`, then keep the first one that successfully pulls the required image. For non-Docker-Hub images, or when a registry mirror fails, inspect the actual pull command from a domestic sync site before using it. `docker.aityp.com` is useful as a search/sync site for some images; open the image detail page and use the exact pull command it provides instead of assuming `docker.aityp.com/<image>` is a universal registry path. DaoCloud `docker.m.daocloud.io` can work for many public/allowlisted images by prefix rewrite; it is not a universal drop-in mirror. If image pulls remain blocked, deploy a release binary with systemd when the project supports it.

### Long command phases

Split long remote work into separate invocations for clone, install, image pull, build, run, and health check. Write each phase to `/var/log/volcengine-deploy/<phase>.log`; when cancelling a clone/build/pull phase, stop the process tree so child processes such as `git-remote-https` or stale `docker pull` jobs do not continue after the Cloud Assistant command exits. Use bounded timeouts for raw GitHub scripts and public image pulls.

### RunCommand result polling

`ve ecs RunCommand` returns scheduling metadata. Treat it as "command submitted", not "command succeeded". Extract the invocation ID, then poll `DescribeInvocationResults` and use `.Result.InvocationResults[0].InvocationResultStatus` plus `.ExitCode` as documented in `skills/volcengine-cli/references/ecs.md`. Decode `Output` from base64 when inspecting command output. Use `submit_cmd` only when you intentionally want the scheduling response; otherwise use `run_cmd`, which returns the polled result JSON.

---

## 3. systemd unit template

Write the unit file through the chosen channel. For Cloud Assistant, encode it and write via `RunCommand`; for SSH, copy it and run the same `systemctl` commands.

```ini
[Unit]
Description=__REPO_NAME__ service
After=network.target

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/opt/__REPO_NAME__
EnvironmentFile=-/opt/__REPO_NAME__/.env
ExecStart=__EXEC_START__
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Replace `__REPO_NAME__` with the project slug and `__EXEC_START__` with the language-appropriate command:

| Language | `ExecStart` value |
|---|---|
| Go / Rust | `/opt/<repo>/server` |
| Node.js | `/usr/bin/node /opt/<repo>/dist/index.js` (or `npm start --prefix /opt/<repo>`) |
| Python | `/opt/<repo>/.venv/bin/python -m <module>` (or `gunicorn` / `uvicorn` invocation) |
| Java | `/usr/bin/java -jar /opt/<repo>/app.jar` |
| Ruby | `/opt/<repo>/bin/<bootstrap>` (Rails: `bundle exec rails s -e production`) |

Install via Cloud Assistant:

```bash
unit_content=$(envsubst < unit-template.service)   # after substituting placeholders
encoded_unit=$(echo "$unit_content" | base64 | tr -d '\n')
run_cmd "install-unit" 60 "echo '$encoded_unit' | base64 -d > /etc/systemd/system/$repo_name.service && \
systemctl daemon-reload && \
systemctl enable --now $repo_name.service"
```

User creation (run once per instance, before first deploy):

```bash
run_cmd "create-user" 60 "id appuser >/dev/null 2>&1 || useradd --system --no-create-home appuser; \
chown -R appuser:appuser /opt/$repo_name"
```

Environment file injection (run after collecting non-secret and secret values, and before starting the service):

```bash
database_url="<resolved-database-url>"
redis_url="<resolved-redis-url>"
env_content=$(printf '%s\n' \
  "NODE_ENV=production" \
  "PORT=$port" \
  "DATABASE_URL=$database_url" \
  "REDIS_URL=$redis_url")
encoded_env=$(printf '%s' "$env_content" | base64 | tr -d '\n')
run_cmd "write-env" 60 "install -d -m 0750 /opt/$repo_name && \
echo '$encoded_env' | base64 -d > /opt/$repo_name/.env && \
chmod 0600 /opt/$repo_name/.env && \
chown appuser:appuser /opt/$repo_name/.env"
```

---

## 4. Health check polling

After `systemctl start`, first confirm the process is listening on the expected port, then poll the local health endpoint through SSH or Cloud Assistant. Then verify the public EIP endpoint from the agent machine. Prefer a detected health path such as `/health` or `/actuator/health`; if none is known, verify TCP/listening state and the root path.

```bash
if ! listen_result=$(run_cmd "check-listen" 60 "ss -ltnp | grep -E '(:$port\\b).*LISTEN' && \
(ss -ltnp | grep -E '0\\.0\\.0\\.0:$port\\b|\\*:$port\\b|\\[::\\]:$port\\b' || true)"); then
  echo "$listen_result" | cmd_output
  echo "Port $port is not listening on $instance_id"
  exit 1
fi

if [ -n "${health_path:-}" ]; then
  for i in $(seq 1 12); do
    result=$(run_cmd "health-check" 60 "curl -sf http://localhost:$port$health_path -o /dev/null && echo OK || echo FAIL")
    output=$(echo "$result" | cmd_output)
    if printf '%s\n' "$output" | grep -qx "OK"; then
      echo "Service healthy on $instance_id"
      exit 0
    fi
    sleep 10
  done
  echo "Health check timeout on $instance_id"
  exit 1
fi

echo "No health_path detected; port listening check passed on $instance_id"
```

**Note**: `RunCommand` itself has a 60-second minimum timeout per the volcengine-cli ECS notes. The `--Timeout` value above must be ≥ 60 even for fast curls.

If the app does not have `/health`, fall back to checking process state:

```bash
systemctl is-active --quiet $repo_name.service && echo OK
ss -ltnp | grep -E ":$port\\b"
```

Public endpoint check:

```bash
if [ -n "${health_path:-}" ]; then
  curl -fsS "http://$eip:$port$health_path"
else
  curl -fsS "http://$eip:$port/"
fi
```

For final acceptance, do not stop at RunCommand `Success`, a listening port, or an HTTP 200 home page. Verify one core application behavior when the app exposes one: login, create/read a record, run a database-backed request, or another user-visible operation tied to the deployed service.

Avoid `curl ... | head` inside `set -o pipefail` checks; `head` can close the pipe early and make a healthy response look failed through `curl: (23) Failure writing output to destination`.

---

## 5. Multi-instance rolling restart

For N instances tagged `project=$repo_name` (lookup via `ve ecs DescribeInstances --TagKey.1 project --TagValue.1 $repo_name`), iterate one at a time. **Never stop more than one instance simultaneously** unless the user explicitly opts out of rolling.

```bash
# Pseudocode flow per instance — execute via your shell loop, not as a single block
for instance_id in $instance_ids; do
  echo "==> Updating $instance_id"
  # 1. Drain (if behind a load balancer, deregister first; skip if not)
  # 2. systemctl stop $repo_name.service
  # 3. Upload new artifact (Pattern A or B)
  # 4. systemctl start $repo_name.service
  # 5. Health check (section 4)
  # 6. Re-register with load balancer (if applicable)
done
```

Drain via CLB: `ve clb DeregisterServers` to remove the instance from the listener; after health check passes, `ve clb RegisterServers` to add back.

---

## 6. Security group inbound rules

The application port must be opened for public access:

```bash
ve vpc AuthorizeSecurityGroupIngress \
  --SecurityGroupId "$sg_id" \
  --PortStart "$port" --PortEnd "$port" \
  --Protocol tcp \
  --CidrIp "0.0.0.0/0" \
  --Policy accept
```

For multi-tier deployments, restrict source CIDR to the LB or front-tier security group ID instead of `0.0.0.0/0`.

SSH 22 is optional. Ask before opening it. If opened, prefer a trusted CIDR rather than `0.0.0.0/0`. If not opened, use Cloud Assistant.

If a source CIDR was derived from outbound IP detection, write the rule immediately after detection and re-check before first SSH use if enough time has passed for NAT egress to drift.

---

## 7. Resource ledger and cleanup

Every new ECS-side resource must be recorded in `.volcengine/created-resources.json` immediately after creation: instance, EIP, security group, security group rule, TOS artifact bucket if created, and any managed dependency. Mark reused resources as `reused=true` and never include them in destructive cleanup.

There is currently no one-command cleanup runner. On failure, print reverse-order cleanup commands from the ledger. The user must review and run the `delete_command` values manually; do not delete automatically without user confirmation.

---

## 8. Failure paths

If health check times out, the deploy skill prints (and does **not** auto-execute):

```bash
# Stop the failing service
run_cmd "stop-service" 60 "systemctl stop $repo_name.service"

# Roll back to previous binary (kept at /opt/<repo>/server.bak by the deploy script before overwrite)
run_cmd "rollback-service" 60 "[ -f /opt/$repo_name/server.bak ] && \
mv /opt/$repo_name/server.bak /opt/$repo_name/server && \
systemctl start $repo_name.service"
```

The user runs these manually after reading the failure summary. Auto-rollback is intentionally avoided — the deploy skill surfaces the issue with full context instead of silently masking it.
