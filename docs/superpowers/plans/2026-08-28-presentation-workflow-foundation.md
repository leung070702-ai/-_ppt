# Presentation Workflow Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 建立固定顺序、可序列化、可观测且失败即终止的 PPT 分析工作流基础结构。

**Architecture:** `PresentationWorkflow` 持有不可变节点顺序和可注入节点实现；节点通过显式 Pydantic 输入/输出模型连接。默认实现只包含上传校验与修改计划校验，其余节点为抛出明确异常的占位节点。

**Tech Stack:** Python 3.11+、Pydantic v2、pytest、标准库 `logging`。

## Global Constraints

- 不覆盖原始 PPT，文件写入必须在已校验 edit plan 之后。
- 不使用多 Agent，LLM 不得改变工作流顺序。
- 节点只返回结构化输出；工作流统一记录状态、错误和日志。

### Task 1: Typed workflow models and node contracts

**Files:**
- Create: `backend/app/workflows/presentation_workflow.py`

- [ ] 定义工作流状态、十组节点输入/输出模型、节点协议、错误类型和固定节点顺序。
- [ ] 为 `validate_upload`、`validate_edit_plan` 提供普通代码实现，为其余节点提供明确占位实现。

### Task 2: Ordered execution and guards

**Files:**
- Modify: `backend/app/workflows/presentation_workflow.py`

- [ ] 实现状态驱动的顺序执行、节点记录、失败终止、后续节点跳过和 `apply_edits` 的已校验计划前置条件。
- [ ] 增加安全日志字段并避免记录文件内容或提示词。

### Task 3: Unit tests

**Files:**
- Create: `backend/tests/test_presentation_workflow.py`

- [ ] 覆盖成功顺序、占位节点失败、失败后跳过、编辑计划校验门禁、状态 JSON 序列化和日志记录。

### Task 4: Verification

- [ ] 运行 `pytest` 与 Ruff，确认现有健康检查和新增工作流测试全部通过。
