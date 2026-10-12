# Project Memory

## 身份与权威入口

This repository contains the reusable control-plane runtime. Host project facts belong in the host repository's own `docs/agent/PROJECT_MEMORY.md`; transient run state belongs only under ignored `var/agent-harness/`.

## 技术栈与边界

Token-efficient execution is defined by `TOKEN_EFFICIENCY.md`; it must not weaken tests, review, security, release or production acceptance.

## 质量门

The repository's tracked tests, CI workflow and release verification are the acceptance authority.

## 维护决策

Keep host-specific facts out of this reusable distribution and preserve backwards-compatible upgrade behavior.

