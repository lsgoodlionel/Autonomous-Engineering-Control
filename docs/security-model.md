# 安全模型

## 保护目标

- 自治执行不能越过仓库、worktree、计划、路径策略或批准范围。
- 不可信文本不能成为任意命令。
- 失败不能通过删除测试、伪造证据或沿用旧 HEAD 结果被掩盖。
- 秘密和原始日志不能进入提交、诊断摘要或 Release 制品。
- 达到停止条件后系统必须暂停，而不是扩大权限继续尝试。

## 信任根

- 当前 Git 仓库、分支、HEAD 与独立 worktree 身份。
- 经人工批准并绑定摘要的计划。
- 已提交且与 HEAD 一致的 wrapper、Gate 矩阵、路径策略和状态 Schema。
- 由操作系统、CI 和仓库平台提供的最小权限边界。

模型输出、Issue、网页、测试日志、构建产物、环境变量值和计划正文均按不可信数据处理。

## 主要控制

- 路径规范化后再匹配，拒绝绝对路径、父级逃逸、目录符号链接和不可解析目标。
- Gate 使用固定参数数组和固定工作目录，不执行动态 Shell 字符串。
- 状态采用原子写入；事件仅追加并使用前一摘要形成完整性链。
- Git 快照绑定分支、HEAD 和工作区；HEAD 变化使验证证据失效。
- delivery 同步逐 descendant commit 和每个 merge parent 检查 `implementationCommit..HEAD` 的 NUL 分隔路径；repository complete 只信任由限定 repository/workflow 对 manifest implementation archive 签发并经 `gh attestation verify` 验证的 GitHub artifact attestation。后续 docs HEAD 不被冒充为已签实现，也不信任环境变量自报。
- distribution 每次打开 validated repository root 都复核设备与 inode；replace/unlink 先将目录项原子移入同父目录 quarantine 并验证被移动 inode。POSIX 无法把 unlink 绑定到已验证 inode，因此私有 temporary/quarantine 不做最终 unlink，而以随机名保留并报告；并发换入文件不会被覆盖或删除。
- 诊断覆盖 URL 凭据、认证 Header、Cookie、常见 Token、密码、私钥块和命名秘密的脱敏。
- 控制平面自身、依赖、认证、迁移、生产与发布路径由宿主设为审批或禁止。
- 自动修复有次数和无进展阈值，执行器不可切换到绕过沙盒的参数。

## 剩余风险

- 宿主 Gate 自身可能测试不足或包含不安全脚本。
- 已授权工具、操作系统账户或 CI runner 可能权限过大。
- 脱敏规则不能证明所有业务秘密形态都被覆盖。
- 缺少自动测试时，状态机只能证明命令成功，不能证明业务正确。
- 外部服务、包仓库和执行器存在供应链与可用性风险。

因此人工代码审查、分支保护、秘密管理、网络隔离、依赖审计和生产审批仍是必需控制。

## 秘密处理

宿主 `secretPolicy.patterns` 应覆盖 `.env`、云凭据目录、SSH 密钥、证书、私钥和项目特有生产配置。allowlist 只允许无秘密模板，例如 `.env.example`；测试伪秘密必须放在精确 fixture 路径并限制扫描豁免范围。

发现泄露时立即停止传播，记录存在性和安全保存位置，交凭据所有者撤销或轮换。不要把泄露值复制到 Issue、诊断、测试或聊天记录。

## 发布安全

Release 从干净、锁定的 commit 构建。制品不得包含 `var/agent-harness/`、缓存、宿主配置、评审报告、运行状态或秘密。发布前生成校验和和 SBOM，并在隔离临时仓库执行安装、doctor、fake drill 和卸载 smoke。
