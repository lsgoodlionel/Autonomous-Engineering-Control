# 贡献指南

## 开始前

1. 阅读 `AGENTS.md`、相关 Issue/设计和本次变更范围。
2. 从最新目标分支创建独立 Git worktree 与功能分支。
3. 使用 Python 3.11-3.14 中至少一个受支持版本运行 `doctor` 和测试。
4. 不把宿主业务事实、个人目录、秘密或运行证据写入核心与通用模板。

## 开发要求

- 缺陷和功能遵循测试先行；提交应聚焦一个职责。
- 核心保持 Python 标准库实现，新增依赖必须先获得维护者批准。
- 用户可见文本以中文为主；稳定机器字段保持兼容。
- 配置解析失败关闭；新字段必须版本化，并同步 Schema、模板、示例和迁移说明。
- 不编辑生成文件来绕过生成器，不降低质量门、审批、路径保护或脱敏规则。

## 验证

至少运行：

```sh
scripts/agent-harness --python \
  -m unittest discover -s tools/agent-harness/tests -p 'test_*.py' -v
scripts/agent-harness --python tools/agent-harness/drills/run_drills.py
git diff --check
```

涉及 wrapper、Linux 路径信任或 Docker 集成时，还需运行固定镜像摘要的 Linux 集成测试。涉及模板时，应将 `examples/minimal/` 复制到临时 Git 仓库执行 `doctor`、初始化、Gate 与卸载演练。

## Pull Request

PR 说明应包含目标、变更范围、风险、测试证据、兼容性影响和回滚方式。不得附加原始运行日志或秘密。许可证尚待仓库所有者选择，外部贡献接收策略也应在许可证确定后最终确认。
