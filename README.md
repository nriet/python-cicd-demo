# python-cicd-demo

用于验证 **GitHub Actions CI/CD 流程** 的 Python 示例项目：代码质量检查 → 单元测试 → 多架构 Docker 镜像构建 → 自动登录并推送到 Docker Hub。

| 项目 | 说明 |
| --- | --- |
| 目标镜像 | `<DOCKERHUB_USERNAME>/<IMAGE_REPO>`（真实值存放在仓库变量 `DOCKERHUB_IMAGE` 中，不写入仓库代码） |
| 构建平台 | `linux/amd64`、`linux/arm64` |
| 触发器 | 推送到 `main`、推送 `v*` 标签、Pull Request、手动 `workflow_dispatch` |
| 质量门禁 | `ruff check` + `pytest --cov`，不通过则不构建镜像 |

## 目录结构

```
.
├── app/
│   ├── __init__.py            # 应用包出口
│   ├── config.py              # 环境变量配置
│   └── main.py                # Flask 服务（工厂函数 + 路由）
├── tests/
│   └── test_app.py            # pytest 单测，作为构建前质量门禁
├── .github/workflows/
│   └── docker-build-push.yml  # CI/CD 工作流
├── Dockerfile                 # 多阶段构建 + 非 root 运行
├── requirements.txt           # 运行依赖
├── requirements-dev.txt       # 开发/CI 依赖（不打进镜像）
├── pyproject.toml             # ruff / pytest 配置
├── .dockerignore
└── .gitignore
```

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 服务名、版本、环境 |
| GET | `/healthz` | 健康检查，供容器 `HEALTHCHECK` 使用 |
| GET | `/api/v1/info` | 返回真实 CPU 架构，用于验证多架构镜像 |
| POST | `/api/v1/echo` | 回显 JSON 请求体 |

`/api/v1/info` 是验证多架构构建的关键接口：拉到 amd64 镜像时返回 `x86_64`，拉到 arm64 镜像时返回 `aarch64`。

## 本地运行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

ruff check .                       # 代码检查
pytest --cov=app                   # 单元测试
python -m app.main                 # 本地启动，默认 http://127.0.0.1:8000
curl http://127.0.0.1:8000/api/v1/info
```

## 容器运行

```bash
docker build -t <DOCKERHUB_USERNAME>/<IMAGE_REPO>:local .
docker run --rm -p 8000:8000 <DOCKERHUB_USERNAME>/<IMAGE_REPO>:local
curl http://127.0.0.1:8000/healthz
```

## 必需配置：仓库 Secrets 与 Variables

工作流推送镜像前会向 Docker Hub 登录，凭据必须由你手动添加到仓库 Secrets（仓库设置 → Secrets and variables → Actions）：

| Secret 名称 | 值 | 说明 |
| --- | --- | --- |
| `DOCKERHUB_USERNAME` | `<你的 Docker Hub 账号名>` | Docker Hub 账号名 |
| `DOCKERHUB_TOKEN` | `<Docker Hub Personal Access Token>` | 在 https://hub.docker.com/settings/security 创建，权限选 **Read & Write**，不要用登录密码 |

镜像推送目标由**仓库变量**提供（同一页面的 Variables 页签），不写死在仓库代码里：

| Variable 名称 | 值 | 说明 |
| --- | --- | --- |
| `DOCKERHUB_IMAGE` | `<namespace>/<repository>` | 镜像目标地址，工作流 `env.IMAGE_NAME` 读取该变量 |

```bash
# 用 gh CLI 快速创建，也可在网页 Variables 页签手动新增
gh variable set DOCKERHUB_IMAGE --body "<namespace>/<repository>"
```

缺少两个 Secret 时，`Log in to Docker Hub` 步骤会直接失败；缺少 `DOCKERHUB_IMAGE` 变量时，`Validate image configuration` 步骤会带明确报错中断构建，不会推送到空地址。

## 触发与验证

```bash
# 1) 推送 main —— 触发构建，产出 latest / main / sha-xxxxxxx 标签
git push origin main

# 2) 打标签 —— 触发发布构建，产出 v1.0.0 / 1.0.0 / 1.0 / 1 / latest 标签
git tag -a v1.0.0 -m "release v1.0.0"
git push origin v1.0.0
```

验证远端镜像确实包含两个架构：

```bash
docker buildx imagetools inspect <DOCKERHUB_USERNAME>/<IMAGE_REPO>:latest
```

`Platforms` 字段应同时列出 `linux/amd64` 与 `linux/arm64`。再分别拉取运行，确认 `/api/v1/info` 返回的 `architecture` 与平台一致。

## 工作流说明

- **quality**：PR 与 push 都会执行，负责 `ruff` 静态检查与 `pytest` 单测，产出覆盖率报告。
- **build-and-push**：依赖 `quality` 通过；PR 事件下跳过（不推送镜像）。步骤依次为配置校验 → QEMU → Buildx → Docker Hub 登录 → 元数据生成标签 → 多架构构建推送。镜像地址取自仓库变量 `DOCKERHUB_IMAGE`，仓库代码中不出现真实账号。
- **缓存**：`cache-from/to: type=gha` 复用 GitHub Actions 缓存，二次构建显著加速（含 QEMU 模拟的 arm64 层）。
- **供应链**：开启 `provenance` 与 `sbom`，镜像附带构建来源证明与软件物料清单。
- **标签策略**：由 `docker/metadata-action` 统一生成，分支推送带分支名与短 SHA，标签推送额外带语义化版本号，默认分支自动打 `latest`。
