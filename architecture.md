# AITS MVP 架构设计文档

## 1. 项目整体结构说明

AITS（AI-empowered Intelligent Testing System）MVP 目标：**先打通“用 AI 生成测试 -> 执行测试 -> 查看报告”的完整闭环**，避免过度设计。

### 1.1 架构原则（MVP）

- 单体优先：采用 Django 单体应用 + 模块化 `apps`，降低早期复杂度
- 后端先行：先稳定 REST API，再逐步接入 Vue 前端
- 异步解耦：耗时任务（生成、执行、报告处理）全部走 Celery
- 可观测：每次执行都有状态、日志、结果可追踪
- 可扩展：MVP 先单项目，数据模型预留后续多项目/多租户演进空间

### 1.2 高层架构（逻辑分层）

1. **API 层（DRF）**  
   提供项目、测试用例、测试执行、报告查询等 RESTful 接口。
2. **应用层（Django apps）**  
   包含项目管理、API 测试、Web 测试、AI 编排、任务调度等领域逻辑。
3. **AI 服务层（LangChain + LangGraph）**  
   统一封装模型调用、Prompt 模板、工具链、工作流状态流转。
4. **执行引擎层**  
   - API: HttpRunner  
   - Web: Playwright
5. **异步任务层（Celery + Redis）**  
   执行测试、生成用例、报告聚合、定时调度触发。
6. **存储层**  
   - 业务数据：SQLite（MVP 开发），生产可迁移 PostgreSQL  
   - 向量数据：ChromaDB（RAG）
   - 报告产物：本地文件系统（MVP）

### 1.3 MVP 必需 vs 后续扩展

**MVP 必需**
- 单项目工作空间
- API 单端点用例生成与执行
- Web 基础自然语言脚本生成与执行
- 统一执行记录与结果查询
- Allure 报告访问入口
- Celery 异步任务 + 基础 Cron 调度

**后续扩展**
- 多租户与组织级权限
- API 场景链路（多步骤依赖、数据流转）
- Web 高级对象识别、自愈定位
- 复杂 RAG（多知识库、权限隔离）
- 分布式执行器、弹性伸缩

---

## 2. Django 应用模块划分

建议采用如下 app 划分（按领域拆分，职责清晰）：

- `apps/projects`：项目、环境、成员与角色
- `apps/api_testing`：OpenAPI 解析、API 用例、套件、执行编排
- `apps/web_testing`：Web 用例、Playwright 脚本、执行编排
- `apps/ai_core`：LLM 配置、Prompt 管理、LangGraph 工作流、RAG 服务
- `apps/scheduler`：定时任务定义与触发
- `apps/reports`：Allure 结果索引、报告聚合查询
- `apps/executions`：统一执行记录（跨 API/Web）
- `apps/common`：公共基类、枚举、异常、工具函数

> 说明：`reports` 与 `executions` 可在极简 MVP 合并进测试模块，但为了后续扩展和统一查询，建议单独 app。

---

## 3. 文件与文件夹结构

```text
aits/
├─ manage.py
├─ requirements/
│  ├─ base.txt
│  ├─ dev.txt
│  └─ prod.txt
├─ config/
│  ├─ __init__.py
│  ├─ settings/
│  │  ├─ __init__.py
│  │  ├─ base.py
│  │  ├─ dev.py
│  │  └─ prod.py
│  ├─ urls.py
│  ├─ asgi.py
│  ├─ wsgi.py
│  ├─ celery_app.py
│  └─ logging.py
├─ apps/
│  ├─ common/
│  │  ├─ models.py
│  │  ├─ enums.py
│  │  ├─ exceptions.py
│  │  └─ utils/
│  ├─ projects/
│  │  ├─ models.py
│  │  ├─ serializers.py
│  │  ├─ views.py
│  │  ├─ services.py
│  │  ├─ permissions.py
│  │  └─ urls.py
│  ├─ api_testing/
│  │  ├─ models.py
│  │  ├─ serializers.py
│  │  ├─ views.py
│  │  ├─ services/
│  │  │  ├─ openapi_parser.py
│  │  │  ├─ case_generator.py
│  │  │  └─ runner.py
│  │  ├─ tasks.py
│  │  └─ urls.py
│  ├─ web_testing/
│  │  ├─ models.py
│  │  ├─ serializers.py
│  │  ├─ views.py
│  │  ├─ services/
│  │  │  ├─ script_generator.py
│  │  │  └─ runner.py
│  │  ├─ tasks.py
│  │  └─ urls.py
│  ├─ ai_core/
│  │  ├─ models.py
│  │  ├─ services/
│  │  │  ├─ llm_provider.py
│  │  │  ├─ prompt_manager.py
│  │  │  ├─ graph_workflows.py
│  │  │  └─ rag_service.py
│  │  ├─ schemas.py
│  │  └─ urls.py
│  ├─ executions/
│  │  ├─ models.py
│  │  ├─ serializers.py
│  │  ├─ views.py
│  │  └─ urls.py
│  ├─ reports/
│  │  ├─ models.py
│  │  ├─ services.py
│  │  ├─ views.py
│  │  └─ urls.py
│  └─ scheduler/
│     ├─ models.py
│     ├─ services.py
│     ├─ tasks.py
│     └─ urls.py
├─ scripts/
│  ├─ run_worker.sh
│  └─ run_beat.sh
├─ storage/
│  ├─ allure-results/
│  ├─ allure-reports/
│  └─ artifacts/
└─ docs/
   └─ architecture.md
```

---

## 4. 模块职责与核心模型

## 4.1 `apps/projects`

**职责**
- 管理项目基础信息（MVP 默认仅 1 项目，也保留多项目结构）
- 管理环境配置（dev/test/staging）
- 管理项目成员与角色（owner/editor/viewer）

**核心模型（MVP）**
- `Project`
- `Environment`
- `ProjectMember`

**后续扩展**
- 项目级 API 凭据加密管理
- 组织/团队层资源隔离

## 4.2 `apps/api_testing`

**职责**
- OpenAPI 文档导入与解析
- 单端点 AI 用例生成
- API 用例管理、执行与结果持久化

**核心模型（MVP）**
- `ApiSchema`（OpenAPI 文档快照）
- `ApiEndpoint`（解析后的端点定义）
- `ApiTestCase`
- `ApiTestSuite`

**后续扩展**
- 多步骤场景用例（链路测试）
- 参数化、数据驱动测试

## 4.3 `apps/web_testing`

**职责**
- 自然语言需求转 Playwright 脚本
- Web 用例管理与执行

**核心模型（MVP）**
- `WebTestCase`
- `WebTestSuite`
- `WebPageObject`（可选，MVP 可简化）

**后续扩展**
- 页面对象自动抽取
- 脚本自愈与定位纠错

## 4.4 `apps/ai_core`

**职责**
- 管理 LLM 模型配置与路由
- 管理 Prompt 模板
- 编排 LangGraph 工作流（生成、审查、修正）
- 提供 RAG 检索接口

**核心模型（MVP）**
- `LLMProviderConfig`
- `PromptTemplate`
- `KnowledgeDocument`
- `KnowledgeChunk`

**后续扩展**
- 多模型策略（成本/延迟/效果自动路由）
- 评测闭环（prompt/模型 A-B 测试）

## 4.5 `apps/executions`

**职责**
- 统一记录执行任务（API/Web）
- 追踪状态机（PENDING/RUNNING/SUCCESS/FAILED）
- 汇总执行日志、产物路径、耗时

**核心模型（MVP）**
- `TestExecution`
- `ExecutionStepLog`

## 4.6 `apps/reports`

**职责**
- 索引 Allure 结果
- 对外提供报告查询和跳转信息

**核心模型（MVP）**
- `TestReport`

## 4.7 `apps/scheduler`

**职责**
- 维护 Cron 任务定义
- 触发套件执行（调度 -> Celery）

**核心模型（MVP）**
- `ScheduledJob`

---

## 5. API 接口设计（RESTful）

统一前缀：`/api/v1/`

### 5.1 项目与环境

- `GET /projects/current`：获取当前项目（MVP 单项目）
- `GET /environments`：环境列表
- `POST /environments`：新增环境
- `PUT /environments/{id}`：更新环境

### 5.2 API 测试

- `POST /api-testing/schemas/import`：导入 OpenAPI 文档（URL/JSON）
- `GET /api-testing/endpoints`：端点列表
- `POST /api-testing/test-cases/ai-generate`：按端点生成测试用例（MVP 核心）
- `GET /api-testing/test-cases`：用例列表
- `POST /api-testing/test-cases/{id}/run`：执行单用例
- `POST /api-testing/test-suites/{id}/run`：执行套件

### 5.3 Web 测试

- `POST /web-testing/test-cases/ai-generate`：自然语言生成 Playwright 脚本
- `GET /web-testing/test-cases`：用例列表
- `POST /web-testing/test-cases/{id}/run`：执行单用例
- `POST /web-testing/test-suites/{id}/run`：执行套件

### 5.4 执行与报告

- `GET /executions`：执行记录列表（可按类型/状态过滤）
- `GET /executions/{id}`：执行详情（日志、耗时、结果）
- `GET /reports/{execution_id}`：报告元信息
- `GET /reports/{execution_id}/allure-url`：Allure 报告访问地址

### 5.5 调度任务

- `GET /scheduler/jobs`：定时任务列表
- `POST /scheduler/jobs`：创建定时任务
- `PUT /scheduler/jobs/{id}`：更新 Cron/状态
- `POST /scheduler/jobs/{id}/trigger`：手动触发一次

### 5.6 API 设计约定

- 使用 DRF ViewSet + Router（标准 CRUD）+ Action（运行、生成等动词）
- 错误响应统一格式：
  - `code`（业务错误码）
  - `message`（可读信息）
  - `details`（字段级错误）
- 长任务接口返回 `execution_id`，前端轮询执行状态

---

## 6. 数据模型设计（Django Models）

以下为 MVP 推荐核心字段（示意级，便于快速落地）：

### 6.1 公共基类

- `TimeStampedModel`
  - `created_at`
  - `updated_at`
- `SoftDeleteModel`（MVP 可选）
  - `is_deleted`

### 6.2 项目域

- `Project`
  - `name`
  - `description`
  - `status`
- `Environment`
  - `project` (FK)
  - `name`（dev/test/staging）
  - `base_url`
  - `variables` (JSONField)
- `ProjectMember`
  - `project` (FK)
  - `user` (FK)
  - `role`（owner/editor/viewer）

### 6.3 API 测试域

- `ApiSchema`
  - `project` (FK)
  - `name`
  - `source_type`（url/json）
  - `raw_content` (JSONField)
  - `version`
- `ApiEndpoint`
  - `schema` (FK)
  - `path`
  - `method`
  - `summary`
  - `request_schema` (JSONField)
  - `response_schema` (JSONField)
- `ApiTestCase`
  - `project` (FK)
  - `endpoint` (FK)
  - `title`
  - `description`
  - `request_data` (JSONField)
  - `assertions` (JSONField)
  - `generated_by_ai` (bool)
- `ApiTestSuite`
  - `project` (FK)
  - `name`
  - `description`
  - `test_cases` (M2M)

### 6.4 Web 测试域

- `WebTestCase`
  - `project` (FK)
  - `title`
  - `requirement_text`
  - `playwright_script` (TextField)
  - `generated_by_ai` (bool)
- `WebTestSuite`
  - `project` (FK)
  - `name`
  - `description`
  - `test_cases` (M2M)

### 6.5 执行与报告域

- `TestExecution`
  - `project` (FK)
  - `execution_type`（api/web）
  - `target_type`（case/suite）
  - `target_id`
  - `status`（PENDING/RUNNING/SUCCESS/FAILED）
  - `trigger_source`（manual/scheduler）
  - `started_at`
  - `finished_at`
  - `result_summary` (JSONField)
  - `log_path`
  - `artifact_path`
- `ExecutionStepLog`
  - `execution` (FK)
  - `step_name`
  - `status`
  - `message`
  - `timestamp`
- `TestReport`
  - `execution` (OneToOne)
  - `report_type`（allure）
  - `report_path`
  - `report_url`
  - `metrics` (JSONField)

### 6.6 AI 核心域

- `LLMProviderConfig`
  - `name`
  - `provider`（openai/anthropic/azure/...）
  - `model_name`
  - `api_base`
  - `api_key_encrypted`
  - `is_active`
- `PromptTemplate`
  - `scene`（api_case_gen/web_script_gen/...）
  - `version`
  - `template_text`
  - `is_default`
- `KnowledgeDocument`
  - `project` (FK)
  - `title`
  - `doc_type`
  - `content`
- `KnowledgeChunk`
  - `document` (FK)
  - `chunk_text`
  - `embedding_id`
  - `metadata` (JSONField)

### 6.7 调度域

- `ScheduledJob`
  - `project` (FK)
  - `name`
  - `job_type`（api_suite/web_suite）
  - `target_id`
  - `cron_expr`
  - `is_enabled`
  - `last_run_at`
  - `next_run_at`

---

## 7. AI 服务层设计（LangChain / LangGraph）

## 7.1 设计目标（MVP）

- 封装统一 AI 服务入口，避免业务层直接依赖模型 SDK
- 固化最小工作流：输入规范化 -> 上下文检索 -> 生成 -> 基础校验 -> 结构化输出
- 支持后续切换模型与 Prompt 版本

## 7.2 服务分层建议

- `LLMClientFactory`  
  根据 `LLMProviderConfig` 返回对应 LangChain ChatModel 实例。

- `PromptService`  
  按场景加载 `PromptTemplate`，支持版本控制。

- `RAGService`  
  文档切片、向量写入 ChromaDB、按 query 检索上下文。

- `WorkflowService`（LangGraph）  
  维护图节点与状态对象，输出标准化结果（JSON）。

## 7.3 MVP 工作流（建议）

### A. API 用例生成工作流
1. 输入：端点定义 + 请求/响应 schema + 测试目标
2. （可选）RAG：检索历史缺陷/接口规范
3. 生成：输出结构化测试用例（request/assertions）
4. 校验：字段完整性与 JSON schema 校验
5. 落库：写入 `ApiTestCase`

### B. Web 脚本生成工作流
1. 输入：自然语言测试需求
2. 生成：Playwright 脚本（MVP 先 Python 或 TS 固定一种）
3. 基础静态校验：关键步骤存在（打开页面、操作、断言）
4. 落库：写入 `WebTestCase.playwright_script`

## 7.4 结构化输出约束（必须）

为降低幻觉和解析成本，AI 输出统一要求 JSON：

- API 用例生成输出：`title`、`request_data`、`assertions`
- Web 脚本生成输出：`title`、`script`、`notes`

业务层只接收 schema 校验通过后的结果，失败则进入重试或人工修改流程。

---

## 8. 异步任务设计（Celery）

## 8.1 队列规划（MVP）

- `ai_generation`：AI 生成任务（API/Web）
- `test_execution`：测试执行任务（HttpRunner/Playwright）
- `reporting`：报告聚合任务（Allure 索引）
- `scheduler`：定时触发任务

## 8.2 核心任务清单

- `generate_api_test_case_task(endpoint_id, user_input)`
  - 调用 LangGraph 生成 API 用例并落库
- `run_api_test_case_task(case_id, env_id)`
  - 调用 HttpRunner 执行并写入 `TestExecution`
- `generate_web_test_case_task(requirement_text, project_id)`
  - 生成 Playwright 脚本并落库
- `run_web_test_case_task(case_id, env_id)`
  - 调用 Playwright 执行并写入 `TestExecution`
- `build_allure_report_task(execution_id)`
  - 生成/刷新报告并更新 `TestReport`
- `trigger_scheduled_job_task(job_id)`
  - 调度器触发统一执行入口

## 8.3 执行状态机（建议）

`PENDING -> RUNNING -> SUCCESS | FAILED | CANCELLED`

每个 Celery 任务都要：
- 写入 execution 状态
- 捕获异常并落日志
- 支持幂等（重复触发不产生脏数据）

## 8.4 调度实现建议（MVP）

- 方案 A（更快）：`django-celery-beat` 管理 Cron（推荐）
- 方案 B：自定义 `ScheduledJob` + 周期扫描任务

MVP 推荐优先方案 A，减少自研调度复杂度。

---

## 9. 开发落地顺序（MVP 实施路线）

### Phase 1：基础骨架（必需）
- 初始化 Django + DRF + Celery + Redis
- 建立 `projects/api_testing/web_testing/executions` 核心模型与迁移
- 打通执行记录查询接口

### Phase 2：API 测试闭环（必需）
- OpenAPI 导入解析
- AI 生成单端点用例
- HttpRunner 执行 + Allure 报告输出

### Phase 3：Web 测试闭环（必需）
- 自然语言生成基础 Playwright 脚本
- 执行与报告接入统一 execution 流程

### Phase 4：调度与 AI 增强（可选增强）
- Cron 定时运行套件
- 接入 RAG 检索优化生成质量
- 引入 Prompt 版本管理与模型路由策略

---

## 10. Django 最佳实践建议（MVP 重点）

- 业务逻辑放 `services.py`，View 层只做请求编排和鉴权
- Serializer 分为读写 serializer，避免字段污染
- 所有耗时操作走 Celery，接口返回 `202 Accepted` + `execution_id`
- 配置分层（`base/dev/prod`），密钥走环境变量
- 为关键流程加最小自动化测试：
  - 模型测试（约束、状态机）
  - API 流程测试（生成 -> 执行 -> 报告）
  - Celery 任务测试（失败重试、状态一致性）

---

## 11. 结论

这份架构以 **“最小可用闭环”** 为核心，优先保障 AITS 在 MVP 阶段可快速上线验证价值：

- 用户可生成测试（API/Web）
- 可执行并查看报告
- 可通过异步与调度实现稳定运行
- 为后续多项目、多模型、多租户扩展保留清晰演进路径
