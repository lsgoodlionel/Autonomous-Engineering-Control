# Token-efficient Control Plane 0.2.0 Verification

日期：2026-10-12

分支：`feat/token-efficient-control-plane`

基线：`5915164`

## 结论

0.2.0 的 Context Capsule、Gate Summary、EvidenceKey/GateLease、Token Telemetry、知识库投影、全局规则安装、GitHub evidence 和 distribution format 4 已完成本地实现与验证。验证不替代 GitHub `main` push 的 provenance attestation，也不表示已创建正式 Release。

## 证据

| 检查 | 结果 |
| --- | --- |
| 非 Docker 完整套件 | PASS，508 tests，zero skip，364.743 秒 |
| 固定 digest Linux Docker fixture | PASS，9 tests，zero skip，7.800 秒 |
| Token Telemetry 最终聚焦回归 | PASS，6 tests，0.011 秒 |
| 故障注入 | PASS，50 tests；包含超时、状态中断、历史漂移、秘密脱敏和便携副本 smoke |
| distribution lifecycle | PASS；install、format 1-3 upgrade、format 4、rollback 和 uninstall 均在完整套件中通过 |
| diff hygiene | PASS，`git diff --check` 无输出 |
| 产品耦合/秘密扫描 | PASS，通用 runtime 与模板未发现 Survey/LimeSurvey 名称或凭据形态 |

## 独立审查

限定安全审查首轮发现一个 Important：只按 `cwd` 前缀归属 Token session 时，宿主仓库内嵌套的独立 Git 仓库可能被误计。实现已收紧为“session `cwd` 最近 Git 根必须等于报告项目根”，并要求报告根本身是 Git 根；新增窗口事件与嵌套仓库回归测试。复审确认该问题关闭，未发现新的 Critical/Important。

## 外部边界

- GitHub CI 的 Gate Summary 只在 `main` push 且 unit/Linux jobs 成功后生成，再由 GitHub artifact attestation 签名并上传。
- 正式 Release、tag、Release asset、SBOM 和许可证选择不属于本次分支推送；不得把功能分支推送写成正式发布。
- Token 报告只处理数值 token metadata；不会把 prompt、message、source payload 或原始日志写入报告。
