# 通用宿主模板

将本目录内容复制到接入项目根目录后再定制。模板中的 `example`、示例命令和空白状态必须替换为宿主真实事实，不能照搬为完成证据。

## 必须填写

- `AGENTS.md`：项目范围、测试、人工审批和交付约束。
- `docs/agent/GATE_MATRIX.yaml`：真实、非交互、退出码可靠的质量门。
- `docs/agent/PROTECTED_PATHS.yaml`：秘密、控制平面、依赖、迁移、生产和生成文件规则。
- `docs/agent/HARNESS_HOST.json`：批准计划、交付清单、ledger、fixture 与文档标记路径。
- `docs/agent/PROJECT_MEMORY.md`：稳定事实与权威入口。
- `docs/agent/AUTONOMY.md`：宿主准入、失败预算、恢复和升级边界。
- `docs/agent/STATE_SCHEMA.json`：保持与安装版本一致，不做项目化修改。
- `docs/agent/HARNESS_DELIVERY.json`：从空白状态开始，由交付控制器更新。

## 接入检查

1. 所有路径均为仓库相对 POSIX 路径。
2. 配置使用严格 JSON，不含 YAML 注释或重复 key。
3. 不包含个人目录、真实凭据、其他项目名称、commit 或交付状态。
4. `/var/agent-harness/` 已加入 `.gitignore`。
5. 已在独立 worktree 中运行 `doctor`、测试和 fake drills。
