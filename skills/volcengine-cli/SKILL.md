---
name: volcengine-cli
description: >-
  Create and manage Volcengine cloud resources using the Volcengine CLI (`ve` command). Supports all
  Volcengine services including ECS, VPC, CLB, RDS, Redis, and more. Trigger this skill whenever the
  user asks to create, query, modify, or delete cloud resources on Volcengine, mentions the `ve` command,
  says "volcengine CLI", or describes infrastructure tasks such as "create an ECS instance",
  "set up a VPC", "list security groups", "allocate an EIP". Also trigger on Chinese prompts
  mentioning "火山引擎" or "火山" (e.g., "火山引擎上有哪些 ECS"、"查一下我火山的云服务器"、
  "火山引擎创建一个 VPC"、"火山的 Redis 实例列一下"). Also trigger when the user encounters
  errors from `ve` commands and needs troubleshooting help.
argument-hint: <task description, e.g., "create an ECS instance in the Beijing region">
user-invocable: true
allowed-tools: Bash, Read, Write
license: MIT
metadata:
  openclaw:
    requires:
      bins:
        - ve
    install:
      - kind: node
        package: "@volcengine/cli"
        bins: [ve]
    envVars:
      - name: VOLCENGINE_ACCESS_KEY
        required: false
        description: AccessKey for AK/SK auth path (alternative to `ve login`)
      - name: VOLCENGINE_SECRET_KEY
        required: false
        description: SecretKey for AK/SK auth path
      - name: VOLCENGINE_REGION
        required: false
        description: Default region; falls back to cn-beijing if unset
---

# Volcengine CLI Skill

Create and manage Volcengine cloud resources by calling Volcengine OpenAPIs through the `ve` command.

---

## 0. Install the ve CLI

If the `ve` command is not available on the system:

**Option 1: npm (recommended)**
```bash
npm i -g @volcengine/cli
```

**Option 2: GitHub Releases**
Download: https://github.com/volcengine/volcengine-cli/releases

Verify the installation: `ve --version`

---

## 1. Initialization (run at the start of every session)

Run the identity verification command to confirm that credentials are usable:

```bash
ve sts GetCallerIdentity
```

**Success** — inform the user of the current account identity and region, then proceed with the task.

> **Switching regions later**: once a profile is set up, `--region` and `VOLCENGINE_REGION` do **not** override the region baked into it. Switch via `ve configure profile --profile <name>` (use `ve configure list` to see profiles). This does not apply to the `--region` flag on `ve login` itself, which is required (see below).

**Failure** — no usable profile. Default plan: use `ve login` (Console Login, OAuth 2.0 + PKCE). Announce this to the user up front, and tell them they can say "use AK/SK", "use STS token", or "use SSO" to switch.

First check the ve version:

```bash
ve --version
```

### Default: Console Login (requires ve >= 1.0.42)

Use `ve login --remote` via the helper script `scripts/ve_login_remote.sh`. It handles the OAuth device-flow subprocess lifecycle (FIFO-bound stdin, URL extraction, code feeding, cleanup) so the agent doesn't have to.

**Resolve the login region:**

1. If the user named a region in this conversation, use it.
2. Else if `VOLCENGINE_REGION` is set, use it.
3. Else default to `cn-beijing`.

**Default procedure** — commit to this path; do NOT present a menu of login methods:

1. **Announce + give the user an off-ramp**, then immediately start:
   > "I'll start `ve login --remote --region <region>` now. Say 'use AK/SK' anytime to switch."

2. **Start the login subprocess and get the URL:**

   ```text
   scripts/ve_login_remote.sh start <region>
   ```

   Prints a `https://signin.volcengine.com/...` URL on stdout. Forward it verbatim to the user with: "Open this URL in any browser, complete login, then send me the 'Authorization code' shown on the page."

3. **When the user replies with the code, complete the flow:**

   ```text
   scripts/ve_login_remote.sh complete <code>
   ```

   The script writes the code into the FIFO bound to the still-running ve, waits for ve to exit, then runs `ve sts GetCallerIdentity` to verify.

4. **If the user interrupts** (says "use AK/SK", "cancel", "this is taking too long", etc.):

   ```text
   scripts/ve_login_remote.sh abort
   ```

   Then switch to the chosen alternative below.

**Critical rules — do NOT improvise OAuth:**

- ❌ Do NOT present a menu like "A. URL  B. local browser  C. AK/SK". Commit to `--remote`; let the user interrupt to switch.
- ❌ Do NOT pre-fetch the URL by running `ve login --remote` and exiting. The PKCE challenge dies with the subprocess; the URL becomes useless and the next attempt fails with PKCE mismatch.
- ❌ Do NOT construct `signin.volcengine.com/authorize/...` URLs yourself.
- ❌ Do NOT decode, parse, or transform the user's reply. Whatever they paste IS the authorization code — pass it verbatim to `complete <code>`. No base64 decode (even if the string looks base64-shaped), no URL query-string parsing, no extracting `code=` from callback URLs.
- ❌ Do NOT pipe codes in (`echo "<code>" | ve login --remote`). The code arrives before the user completes browser login and fails verification.
- ❌ Do NOT spawn parallel `ve login` subprocesses. One at a time, tracked by the helper.
- ❌ Do NOT call `ve login --remote` directly. **Always** go through `scripts/ve_login_remote.sh`. The script binds ve's stdin to a FIFO so the still-running ve can receive the user's code via a separate `complete` call. Calling ve directly orphans the subprocess and breaks the code-feeding step.
- ✅ Use `scripts/ve_login_remote.sh start` / `complete` / `abort`.

> **Switching region mid-flow**: `scripts/ve_login_remote.sh abort`, then `start <new-region>`.
> **No browser on any device** (true offline / CI): skip `ve login`, fall back to AK/SK below.

If `ve login` fails (network error, non-interactive terminal, version too old), or the user explicitly asks for a different method, fall back to one of the alternatives below. If installed via npm, upgrade with `npm i -g @volcengine/cli@latest`.

### Alternative: AK/SK (long-term credentials, for CI/CD or scripting)

Ask the user for AccessKey and SecretKey, then:

```text
ve configure set --profile default --region cn-beijing \
  --endpoint open.volcengineapi.com \
  --access-key <AK> --secret-key <SK>
```

For STS (temporary) credentials, also pass `--session-token <TOKEN>`.

Alternative for the current shell only: export `VOLCENGINE_ACCESS_KEY`, `VOLCENGINE_SECRET_KEY`, `VOLCENGINE_REGION`, optionally `VOLCENGINE_SESSION_TOKEN`.

### Alternative: SSO / Cloud Identity Center (requires ve >= 1.0.38, for enterprise federation)

Three-step setup; ask the user for the SSO start URL and session name first:

```text
ve configure sso-session --name <session-name> \
  --start-url https://<sso-host>/userportal \
  --region cn-beijing \
  --registration-scopes cloudidentity:account:access,offline_access

ve configure sso --profile <profile-name> --sso-session <session-name>

ve configure profile --profile <profile-name>
```

Then `ve sso login --sso-session <session-name>` (use `--no-browser` on headless machines).

### Credential safety

- **Never read `~/.volcengine/config.json`** — it contains AK/SK and session tokens.
- When running `ve configure set` with `--secret-key`, prefer letting the **user** paste and run the command in their own shell rather than executing it via Claude — secrets passed as command-line arguments end up in shell history and process listings.
- Never echo AK/SK, secret keys, or session tokens back to the user in plain text.

---

## 2. Safety Rules (mandatory)

### Read/Write Classification

| Level | Operation Types | Behavior |
|-------|----------------|----------|
| **Read-only** | Describe\* / List\* / Get\* / Query\* | Execute directly, no confirmation needed |
| **Write** | Create\* / Run\* / Allocate\* / Attach\* / Associate\* / Authorize\* | Show the full command and wait for user confirmation |
| **Destructive** | Delete\* / Terminate\* / Release\* / Revoke\* / Modify\* / Stop\* / Detach\* | Show command + impact summary; **require** user confirmation |

### Core Principles

1. **Default to read-only** — unless the user explicitly requests a change, execute in read-only mode
2. **DryRun first** — if a write/destructive operation supports `--DryRun true`, run a DryRun to preview the plan, then confirm before executing
3. **Confirm before executing** — show the full command for write operations and wait for approval
4. **Protect credentials** — never read `~/.volcengine/config.json`; never expose access-key, secret-key, or session-token in output

### DryRun Notes

A successful DryRun validation returns **exit code 1** (non-zero) with `DryRunOperation` in stderr. This is expected behavior:

```text
output=$(ve <svc> <action> --DryRun true ... 2>&1)
if echo "$output" | grep -q "DryRunOperation"; then
  echo "Parameter validation passed"
fi
```

---

## 3. Locate APIs and Retrieve Parameters

### Locate the API (find the service name + Action name)

```text
Step 1: Service name + Action known? -> Use them directly; skip to "Retrieve parameters"
Step 2: Service name known, Action unknown?
  -> ve <service> 2>&1 | grep -i <keyword>
Step 3: Service name also unknown?
  -> ve 2>&1 | grep -i <service keyword>
Step 4: None of the above work?
  -> python3 scripts/find_api.py <keyword>
```

### Retrieve parameters (once the Action is known)

Choose a strategy based on operation type:

| Operation Type | Strategy | Rationale |
|---------------|----------|-----------|
| **Read-only** (Describe/List/Get) | `ve <svc> <action> --help` | Few, simple parameters — names alone are sufficient |
| **Write/destructive** (Create/Run/Delete, etc.) | `scripts/fetch_swagger.py` for full docs | Many parameters, nested structures — need required fields, examples, and descriptions |
| **Still unclear after `--help`** | Supplement with `scripts/fetch_swagger.py` | Use whenever parameter meaning is uncertain |
| **Errors like `Invalid*` / `Missing*`** | Recheck with `scripts/fetch_swagger.py` | On `InvalidParameter`, `InvalidXxx.NotFound`, or `MissingParameter`, verify parameter names, required fields, and value ranges |

```text
# Read-only — --help is sufficient
ve ecs DescribeInstances --help

# Write — retrieve full documentation
python3 scripts/fetch_swagger.py --service ecs --action RunInstances
```

### ve command name and API version relationship

- Default version -> ve command = base service name (e.g., `iam`)
- Non-default version -> ve command = `service name + version without hyphens` (e.g., `iam` v2021-08-01 -> `iam20210801`)
- When in doubt: `ve 2>&1 | grep <service>` to confirm

### Python helper usage

```text
# Search for an API (when the service name is unknown)
python3 scripts/find_api.py <keyword> [--limit N]

# Get full API parameter documentation (when descriptions/examples are needed)
python3 scripts/fetch_swagger.py --service <ServiceCode> --action <ActionName>

# List all APIs for a service
python3 scripts/fetch_swagger.py --service <ServiceCode> --list
```

> Always pass the **base service name** to scripts/fetch_swagger.py (e.g., `--service iam`, not `iam20210801`) — the script auto-detects the version.

---

## 4. Execute API Calls

### Basic Format

```text
ve <ServiceCode> <ActionName> --ParamName "value"
```

### Parameter Passing Rules

Determine the format from `--help` output:
- **Flat parameter format**: `--help` lists individual `--Key type` entries (e.g., ECS, VPC, IAM) -> pass with `--Key "value"`
- **JSON format**: `--help` only shows `--body '{...}'` (e.g., Redis, CR, and other POST APIs) -> pass with `--body '{...}'`

```bash
# Flat parameters — nested fields use dot notation; arrays use .N index (starting from 1)
ve ecs RunInstances --Placement.ZoneId "cn-beijing-a"
ve ecs RunInstances --NetworkInterfaces.1.SubnetId "subnet-xxxx"
ve ecs RunInstances --Tags.1.Key "env" --Tags.2.Key "app"

# JSON format (when --help only shows --body)
ve redis CreateDBInstance --body '{"InstanceName":"demo", "RegionId":"cn-beijing", ...}'
```

### Response Format

```json
// Success
{ "ResponseMetadata": { "RequestId": "..." }, "Result": { ... } }

// Failure
{ "ResponseMetadata": { "Error": { "Code": "...", "Message": "..." } } }
```

### Async Resource Creation Requires Polling

Some resources (VKE clusters, RDS instances, ECS instances, etc.) take several minutes to create. After creation, poll the Describe endpoint until the resource reaches the desired status before proceeding.

> Creating sub-resources (e.g., security groups) immediately after VPC creation may fail with `InvalidVpc.InvalidStatus`. Create sub-resources sequentially (subnet first, then security group), or wait a few seconds and retry.

```text
# General polling pattern: check every 30 seconds until the target status is reached
while true; do
  cur_status=$(ve <svc> Describe<Resource> --<IdParam> "xxx" 2>&1 | grep -o '"Status":"[^"]*"')
  echo "$(date +%H:%M:%S) $cur_status"
  echo "$cur_status" | grep -q '"Status":"Running"' && break
  sleep 30
done
```

---

## 5. End-to-End Execution Flow (Summary)

```text
1. Initialize: verify credentials -> GetCallerIdentity -> confirm region
2. Understand the task: is the user querying or making changes?
3. Locate the API: ve --help first -> Python helpers as fallback
4. Query dependent resources: use Describe*/List* to obtain required IDs
5. Read operation -> execute directly and display results
   Write operation -> show command -> DryRun (if supported) -> user confirmation -> execute
6. Parse the response and report results to the user
```

---

## 6. Service-Specific Notes

Consult or update the corresponding notes file when encountering service-specific issues:

- ECS: [references/ecs.md](references/ecs.md)
- IAM: [references/iam.md](references/iam.md)
- Redis: [references/redis.md](references/redis.md)
