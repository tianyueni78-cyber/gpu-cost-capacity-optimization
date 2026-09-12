# 真实客户试点包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可直接发送、可验证且可报价的 GPU 真实客户试点包。

**Architecture:** 使用现有 CSV 契约和 Markdown 文档，不建设新应用。自动测试只验证模板字段和空白数据边界。

**Tech Stack:** CSV、Markdown、Python unittest。

**Spec:** `docs/superpowers/specs/2026-09-12-real-customer-pilot-pack-design.md`

## Global Constraints

- 不新增依赖或运行服务。
- 不在模板中放入真实或示例客户数据。
- 报价标记为价格实验。
- 不承诺节省或执行生产变更。

---

### Task 1: 客户数据模板

**Files:**
- Create: `customer-pilot-pack/templates/*.csv`
- Create: `tests/test_customer_pilot_pack.py`

- [x] 编写模板字段与空白数据测试并确认因模板缺失而失败。
- [x] 创建四张最小 CSV 模板。
- [x] 运行测试并确认通过。

### Task 2: 客户操作与审核材料

**Files:**
- Create: `customer-pilot-pack/README.md`
- Create: `customer-pilot-pack/脱敏说明.md`
- Create: `customer-pilot-pack/30分钟操作流程.md`
- Create: `customer-pilot-pack/结果审核清单.md`

- [x] 根据现有产品边界编写短文档。
- [x] 逐项检查数据、时间、停止条件和人工审批要求。

### Task 3: 实验报价与仓库入口

**Files:**
- Create: `customer-pilot-pack/试点报价.md`
- Modify: `README.md`
- Modify: `CURRENT_STATE.md`

- [x] 写入固定范围实验报价和排除项。
- [x] 增加仓库入口并更新当前状态。
- [x] 运行模板测试、三个产品测试和 diff 检查。
