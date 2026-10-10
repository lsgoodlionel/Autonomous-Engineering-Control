# Release 指南

## 准入

正式 Release 必须满足：

- 从干净、已审查、锁定的 commit 构建。
- 完整非 Docker 单元测试在 Ubuntu 与 macOS 的 Python 3.11-3.14 矩阵通过。
- 固定 digest 的 Linux wrapper 集成测试零 skip。
- portable install、`doctor`、fake drill 和 uninstall smoke 通过。
- workflow 危险参数扫描、文档引用、`git diff --check` 和秘密扫描通过。
- repository complete 由匹配 `expectedRepository`、`repositoryAttestation.signerWorkflow` 与 `sourceRef` 的 GitHub Actions 对 exact-head archive 生成签名 artifact attestation；`check-docs` 重建 archive 并以 `gh attestation verify --repo --signer-workflow --source-digest --source-ref` 在线验证。自报或手填环境输出不是发布证据，无 attestation、`gh`、令牌或网络时失败关闭。
- 发布包内容检查证明不含宿主状态、运行证据、缓存或秘密。
- 仓库所有者已选择许可证并创建 `LICENSE`；在此之前不得正式公开发布。

## 版本与标签

使用语义化版本，`VERSION`、`CHANGELOG.md` 和 tag 必须一致。Release workflow 只接受新建的 `v*` tag，不覆盖已有标签。构建前再次验证 tag 指向的 commit 与已通过 CI 的 commit 相同。

## 制品

至少生成：

- `tar.gz` 与 `zip` 源码/安装制品。
- `SHA256SUMS`。
- 文件清单和版本信息。
- 建议生成 SPDX 或 CycloneDX SBOM。

制品只包含核心、必要文档和通用模板。排除 `var/agent-harness/`、`__pycache__/`、`*.pyc`、本地环境、宿主交付清单、真实评审报告和临时测试输出。

## 权限

普通测试 CI 使用只读仓库权限。exact-head attestation job 仅增加 `id-token: write` 与 `attestations: write`；仅 Release job 在所有验证成功后获得最小 `contents: write`，且不拥有生产部署、包仓库管理或秘密读取的额外权限。

## 发布后验证与回滚

在空白临时 Git 仓库中从发布制品接入最小宿主，执行版本检查、`doctor`、初始化、Gate、fake drill 和卸载。校验失败时撤回有问题的 Release 说明并发布修复版本，不覆盖原标签或原制品。
