# 已批准实施计划

**Status:** approved

## Milestone milestone-1: 最小可验证变更

**目标：** 完成一个边界明确、可自动验证的宿主变更。

**Files:**

- Modify: `src/example.txt`
- Test: `tests/test_example.py`

**实施步骤：**

1. 先增加能够证明预期行为的失败测试。
2. 运行测试并确认按预期失败。
3. 编写最小实现。
4. 运行自动选择的全部 Gate。
5. 自审 diff，并记录当前 HEAD 的脱敏证据。

**验收：** 单元测试和 diff 检查在当前 HEAD 通过；没有修改批准范围外文件。
