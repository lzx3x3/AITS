# AITS MVP 构建任务清单

> 粒度：每个任务 10-30 分钟，1 次改动只解决 1 个问题。  
> 执行：严格按顺序，一次一个，完成后等待确认。  
> 依赖：`→` 后列出必须先完成的任务。

---

## 第一阶段：项目初始化

### T001 创建 Django 项目骨架
- **描述**：使用 `django-admin startproject config .` 在 `aits/` 目录下创建项目，生成 `manage.py` 与 `config/` 包。
- **依赖**：无
- **输入**：空目录 `aits/`
- **输出**：`manage.py`、`config/__init__.py`、`config/settings.py`、`config/urls.py`、`config/wsgi.py`、`config/asgi.py`
- **完成标准**：`python manage.py check` 无报错
- **测试方法**：执行 `python manage.py check`
- **相关文件**：`manage.py`、`config/`

### T002 拆分 settings 为 base/dev/prod
- **描述**：将单文件 `config/settings.py` 拆分为 `config/settings/__init__.py`、`base.py`、`dev.py`、`prod.py`。`dev.py` 使用 SQLite + DEBUG=True；`prod.py` 使用 PostgreSQL + DEBUG=False。
- **依赖**：→ T001
- **输入**：`config/settings.py`
- **输出**：`config/settings/base.py`、`config/settings/dev.py`、`config/settings/prod.py`
- **完成标准**：`python manage.py check --settings=config.settings.dev` 通过
- **测试方法**：分别以 dev 和 prod 设置运行 `check`（prod 可跳过 DB 连接）
- **相关文件**：`config/settings/`

### T003 创建 requirements 分层依赖文件
- **描述**：创建 `requirements/base.txt`（Django、DRF、Celery、LangChain 等核心依赖）、`dev.txt`（pytest、debugpy 等开发依赖，`-r base.txt`）、`prod.txt`（gunicorn、psycopg2 等，`-r base.txt`）。
- **依赖**：→ T001
- **输入**：architecture.md 技术栈清单
- **输出**：`requirements/base.txt`、`requirements/dev.txt`、`requirements/prod.txt`
- **完成标准**：`pip install -r requirements/dev.txt` 在干净虚拟环境中成功安装
- **测试方法**：新建 venv 后执行安装
- **相关文件**：`requirements/`

### T004 添加环境变量支持与 .env.example
- **描述**：在 `base.py` 中引入 `python-dotenv` 或 `django-environ`，从 `.env` 读取 `SECRET_KEY`、`DEBUG`、`DATABASE_URL`、`REDIS_URL`。提供 `.env.example` 模板和 `.gitignore`。
- **依赖**：→ T002
- **输入**：`config/settings/base.py`
- **输出**：`.env.example`、`.gitignore`、更新后的 `base.py`
- **完成标准**：复制 `.env.example` 为 `.env` 后 `python manage.py check` 通过；无硬编码密钥
- **测试方法**：删除 `.env` 后启动报明确错误信息（非崩溃）
- **相关文件**：`.env.example`、`.gitignore`、`config/settings/base.py`

### T005 创建全部 Django app 目录并注册
- **描述**：创建 `apps/common`、`apps/projects`、`apps/api_testing`、`apps/web_testing`、`apps/ai_core`、`apps/executions`、`apps/reports`、`apps/scheduler` 共 8 个 app（含 `__init__.py`、`apps.py`），并在 `INSTALLED_APPS` 中注册。
- **依赖**：→ T002
- **输入**：app 名称列表
- **输出**：8 个 app 目录 + 注册配置
- **完成标准**：`python manage.py check` 通过且无 app 配置警告
- **测试方法**：执行 `check`
- **相关文件**：`apps/*/apps.py`、`config/settings/base.py`

### T006 配置根路由与 API 版本前缀
- **描述**：在 `config/urls.py` 建立 `api/v1/` 入口，各 app 挂空的 `urls.py`（含空 `urlpatterns`）。
- **依赖**：→ T005
- **输入**：各 app urls.py 占位
- **输出**：`/api/v1/` 路由前缀就绪
- **完成标准**：`runserver` 后访问 `/api/v1/` 返回 JSON 响应（404 JSON 也算通过）
- **测试方法**：启动服务后 curl 或浏览器访问
- **相关文件**：`config/urls.py`、`apps/*/urls.py`

### T007 配置 Celery 应用与 Django 集成
- **描述**：创建 `config/celery_app.py`，在 `config/__init__.py` 中导入确保 app 加载。配置 Redis 作为 broker。
- **依赖**：→ T004
- **输入**：`REDIS_URL` 环境变量
- **输出**：`config/celery_app.py`、更新后的 `config/__init__.py`
- **完成标准**：`celery -A config inspect ping` 在 Redis 可用时返回 pong
- **测试方法**：启动 worker 后执行 ping
- **相关文件**：`config/celery_app.py`、`config/__init__.py`、`config/settings/base.py`

---

## 第二阶段：数据模型定义

### T008 定义公共抽象基类 TimeStampedModel
- **描述**：在 `apps/common/models.py` 创建 `TimeStampedModel`（`created_at`、`updated_at` 自动管理），供所有业务模型继承。
- **依赖**：→ T005
- **输入**：无
- **输出**：`apps/common/models.py` 中的抽象模型
- **完成标准**：`class Meta: abstract = True` 存在；子类继承后 `makemigrations` 不报错
- **测试方法**：创建临时子类执行 `makemigrations --dry-run`
- **相关文件**：`apps/common/models.py`

### T009 定义公共枚举类
- **描述**：在 `apps/common/enums.py` 定义项目中复用的枚举：`ProjectStatus`、`MemberRole`、`ExecutionStatus`、`ExecutionType`、`TriggerSource` 等（使用 `models.TextChoices`）。
- **依赖**：→ T005
- **输入**：architecture.md 中的状态/类型定义
- **输出**：`apps/common/enums.py`
- **完成标准**：所有枚举可被 import 且值唯一
- **测试方法**：`python -c "from apps.common.enums import ExecutionStatus; print(ExecutionStatus.choices)"`
- **相关文件**：`apps/common/enums.py`

### T010 定义 Project 模型
- **描述**：在 `apps/projects/models.py` 创建 `Project`（`name`、`description`、`status`），继承 `TimeStampedModel`。
- **依赖**：→ T008、T009
- **输入**：architecture.md §6.2
- **输出**：`Project` 模型
- **完成标准**：`makemigrations projects` 生成迁移文件
- **测试方法**：执行 `makemigrations --check`
- **相关文件**：`apps/projects/models.py`

### T011 定义 Environment 模型
- **描述**：创建 `Environment`（`project` FK、`name`、`base_url`、`variables` JSONField），继承 `TimeStampedModel`。
- **依赖**：→ T010
- **输入**：architecture.md §6.2
- **输出**：`Environment` 模型
- **完成标准**：FK 关联 Project 正确；`variables` 默认 `dict`
- **测试方法**：`makemigrations --check`
- **相关文件**：`apps/projects/models.py`

### T012 定义 ProjectMember 模型
- **描述**：创建 `ProjectMember`（`project` FK、`user` FK→auth.User、`role` 枚举），添加 `unique_together = [("project", "user")]`。
- **依赖**：→ T010、T009
- **输入**：MemberRole 枚举
- **输出**：`ProjectMember` 模型
- **完成标准**：唯一约束写入迁移
- **测试方法**：`makemigrations --check`
- **相关文件**：`apps/projects/models.py`

### T013 定义 ApiSchema 和 ApiEndpoint 模型
- **描述**：在 `apps/api_testing/models.py` 创建 `ApiSchema`（`project` FK、`name`、`source_type`、`raw_content` JSON、`version`）和 `ApiEndpoint`（`schema` FK、`path`、`method`、`summary`、`request_schema` JSON、`response_schema` JSON）。
- **依赖**：→ T010、T008
- **输入**：architecture.md §6.3
- **输出**：两个模型
- **完成标准**：`makemigrations api_testing` 通过
- **测试方法**：`makemigrations --check`
- **相关文件**：`apps/api_testing/models.py`

### T014 定义 ApiTestCase 和 ApiTestSuite 模型
- **描述**：创建 `ApiTestCase`（`project` FK、`endpoint` FK、`title`、`description`、`request_data` JSON、`assertions` JSON、`generated_by_ai` bool）和 `ApiTestSuite`（`project` FK、`name`、`description`、`test_cases` M2M）。
- **依赖**：→ T013
- **输入**：architecture.md §6.3
- **输出**：两个模型
- **完成标准**：M2M 关系正确建立
- **测试方法**：`makemigrations --check`
- **相关文件**：`apps/api_testing/models.py`

### T015 定义 WebTestCase 和 WebTestSuite 模型
- **描述**：在 `apps/web_testing/models.py` 创建 `WebTestCase`（`project` FK、`title`、`requirement_text`、`playwright_script` TextField、`generated_by_ai` bool）和 `WebTestSuite`（`project` FK、`name`、`description`、`test_cases` M2M）。
- **依赖**：→ T010、T008
- **输入**：architecture.md §6.4
- **输出**：两个模型
- **完成标准**：`makemigrations web_testing` 通过
- **测试方法**：`makemigrations --check`
- **相关文件**：`apps/web_testing/models.py`

### T016 定义 LLMProviderConfig 和 PromptTemplate 模型
- **描述**：在 `apps/ai_core/models.py` 创建 `LLMProviderConfig`（`name`、`provider`、`model_name`、`api_base`、`api_key_encrypted`、`is_active` bool）和 `PromptTemplate`（`scene`、`version`、`template_text`、`is_default` bool）。
- **依赖**：→ T008
- **输入**：architecture.md §6.6
- **输出**：两个模型
- **完成标准**：`makemigrations ai_core` 通过
- **测试方法**：`makemigrations --check`
- **相关文件**：`apps/ai_core/models.py`

### T017 定义 TestExecution 和 ExecutionStepLog 模型
- **描述**：在 `apps/executions/models.py` 创建 `TestExecution`（`project` FK、`execution_type`、`target_type`、`target_id`、`status`、`trigger_source`、`started_at`、`finished_at`、`result_summary` JSON、`log_path`、`artifact_path`）和 `ExecutionStepLog`（`execution` FK、`step_name`、`status`、`message`、`timestamp`）。
- **依赖**：→ T010、T009、T008
- **输入**：architecture.md §6.5 + ExecutionStatus 枚举
- **输出**：两个模型
- **完成标准**：状态字段使用 `ExecutionStatus` choices
- **测试方法**：`makemigrations --check`
- **相关文件**：`apps/executions/models.py`

### T018 定义 TestReport 模型
- **描述**：在 `apps/reports/models.py` 创建 `TestReport`（`execution` OneToOneField、`report_type`、`report_path`、`report_url`、`metrics` JSON）。
- **依赖**：→ T017
- **输入**：architecture.md §6.5
- **输出**：一个模型
- **完成标准**：OneToOne 关联正确
- **测试方法**：`makemigrations --check`
- **相关文件**：`apps/reports/models.py`

### T019 定义 ScheduledJob 模型
- **描述**：在 `apps/scheduler/models.py` 创建 `ScheduledJob`（`project` FK、`name`、`job_type`、`target_id`、`cron_expr`、`is_enabled`、`last_run_at`、`next_run_at`）。
- **依赖**：→ T010、T008
- **输入**：architecture.md §6.7
- **输出**：一个模型
- **完成标准**：`makemigrations scheduler` 通过
- **测试方法**：`makemigrations --check`
- **相关文件**：`apps/scheduler/models.py`

### T020 执行全量数据库迁移
- **描述**：对全部 app 执行 `makemigrations` 和 `migrate`，确保无循环依赖。
- **依赖**：→ T010-T019
- **输入**：全部模型定义
- **输出**：迁移文件 + SQLite 数据库
- **完成标准**：`migrate` 零错误；`python manage.py check` 通过
- **测试方法**：执行 `migrate` 和 `showmigrations`
- **相关文件**：`apps/*/migrations/`

---

## 第三阶段：项目管理模块（CRUD）

### T021 实现 Project Serializer
- **描述**：创建 `ProjectListSerializer`（只读，含 id/name/status/created_at）和 `ProjectCreateSerializer`（可写，name/description 必填）。
- **依赖**：→ T020
- **输入**：Project 模型
- **输出**：`apps/projects/serializers.py`
- **完成标准**：必填字段校验生效；非法输入返回错误
- **测试方法**：`pytest` 单测 serializer 的 `is_valid()` 正例/反例
- **相关文件**：`apps/projects/serializers.py`

### T022 实现 Project ViewSet
- **描述**：实现 `ProjectViewSet`（list/retrieve/update），挂载到 `api/v1/projects/`。MVP 单项目模式下 list 返回唯一项目，不提供 create/delete。
- **依赖**：→ T021、T006
- **输入**：Project serializers
- **输出**：项目 CRUD API
- **完成标准**：`GET /api/v1/projects/` 返回 200 + JSON 列表
- **测试方法**：`pytest` 使用 `APIClient` 断言 status_code 和数据结构
- **相关文件**：`apps/projects/views.py`、`apps/projects/urls.py`

### T023 实现 Environment Serializer 与 ViewSet
- **描述**：创建 Environment 的读写 Serializer 和完整 CRUD ViewSet（list/create/retrieve/update/destroy），挂载到 `api/v1/environments/`。`base_url` 做 URL 格式校验。
- **依赖**：→ T020、T006
- **输入**：Environment 模型
- **输出**：环境 CRUD API
- **完成标准**：4 种操作均可用；非法 URL 被拒绝
- **测试方法**：`pytest` 覆盖 CRUD + 无效 URL 校验
- **相关文件**：`apps/projects/serializers.py`、`apps/projects/views.py`、`apps/projects/urls.py`

### T024 实现 ProjectMember 只读接口
- **描述**：提供 `GET /api/v1/project-members/`（可按 project 过滤），只读。
- **依赖**：→ T020、T006
- **输入**：ProjectMember 模型
- **输出**：成员列表 API
- **完成标准**：返回成员列表含 user 信息和 role
- **测试方法**：`pytest` 创建成员后查询断言
- **相关文件**：`apps/projects/serializers.py`、`apps/projects/views.py`

### T025 实现统一异常处理器
- **描述**：在 `apps/common/exceptions.py` 创建 DRF 全局异常处理函数，统一返回 `{"code": "...", "message": "...", "details": {...}}`，在 `base.py` 中注册 `EXCEPTION_HANDLER`。
- **依赖**：→ T006
- **输入**：DRF 原生异常
- **输出**：标准化错误响应
- **完成标准**：400/404/500 均返回统一格式 JSON
- **测试方法**：`pytest` 触发校验错误和 404，断言响应格式
- **相关文件**：`apps/common/exceptions.py`、`config/settings/base.py`

---

## 第四阶段：AI 核心服务

### T026 实现 LLMClientFactory
- **描述**：在 `apps/ai_core/services/llm_provider.py` 实现工厂类，读取 `LLMProviderConfig`（`is_active=True`）返回 LangChain `BaseChatModel` 实例。支持 OpenAI 和 Anthropic 两种 provider。
- **依赖**：→ T016、T003
- **输入**：数据库中的 provider 配置
- **输出**：LangChain ChatModel 实例
- **完成标准**：无 active 配置时抛出明确异常
- **测试方法**：`pytest` mock DB 记录，断言返回正确 client 类型
- **相关文件**：`apps/ai_core/services/llm_provider.py`

### T027 实现 PromptManager
- **描述**：在 `apps/ai_core/services/prompt_manager.py` 实现按 `scene` 获取 Prompt 模板的服务。无指定 version 时返回 `is_default=True` 的模板。
- **依赖**：→ T016
- **输入**：scene 名称 + 可选 version
- **输出**：模板字符串
- **完成标准**：无默认模板时抛出 `PromptNotFoundError`
- **测试方法**：`pytest` 覆盖默认/指定版本/不存在三种场景
- **相关文件**：`apps/ai_core/services/prompt_manager.py`

### T028 实现 LLMProviderConfig CRUD API
- **描述**：为 `LLMProviderConfig` 提供完整 CRUD ViewSet，挂载到 `api/v1/ai/providers/`。
- **依赖**：→ T016、T006
- **输入**：provider 配置参数
- **输出**：模型管理 API
- **完成标准**：可新增、切换 `is_active` 状态、删除
- **测试方法**：`pytest` APIClient 覆盖 CRUD
- **相关文件**：`apps/ai_core/serializers.py`、`apps/ai_core/views.py`、`apps/ai_core/urls.py`

### T029 实现 PromptTemplate CRUD API
- **描述**：为 `PromptTemplate` 提供 CRUD ViewSet，挂载到 `api/v1/ai/prompts/`。支持按 `scene` 过滤。
- **依赖**：→ T016、T006
- **输入**：scene/version/template_text
- **输出**：Prompt 管理 API
- **完成标准**：同 scene 可存储多个版本
- **测试方法**：`pytest` 创建同 scene 两版本并按 scene 过滤
- **相关文件**：`apps/ai_core/serializers.py`、`apps/ai_core/views.py`

### T030 实现 API 用例生成 LangGraph 工作流
- **描述**：在 `apps/ai_core/services/graph_workflows.py` 实现 `api_case_gen_workflow`，定义 `ApiCaseGenState`（TypedDict）。节点：normalize_input → generate → validate_output。输出结构：`{"title", "request_data", "assertions"}`。
- **依赖**：→ T026、T027
- **输入**：endpoint schema + 用户 prompt
- **输出**：结构化测试用例 JSON（经 schema 校验）
- **完成标准**：校验失败时 state.error 有信息；正常时 validated_cases 非空
- **测试方法**：`pytest` mock LLM 返回固定 JSON，验证输出通过 schema 校验
- **相关文件**：`apps/ai_core/services/graph_workflows.py`

### T031 实现 Web 脚本生成 LangGraph 工作流
- **描述**：实现 `web_script_gen_workflow`，定义 `WebScriptGenState`。节点：normalize_input → generate → basic_check。输出结构：`{"title", "script", "notes"}`。
- **依赖**：→ T026、T027
- **输入**：自然语言测试需求
- **输出**：`title` + Playwright 脚本 + notes
- **完成标准**：脚本中包含基本关键词（page.goto / expect）
- **测试方法**：`pytest` mock LLM 输出，断言结构完整
- **相关文件**：`apps/ai_core/services/graph_workflows.py`

### T032 实现 RAGService 占位
- **描述**：在 `apps/ai_core/services/rag_service.py` 实现最小 RAG 接口：`query(text) -> list[str]`。MVP 阶段直接返回空列表，预留 ChromaDB 接入点。
- **依赖**：→ T005
- **输入**：查询文本
- **输出**：上下文片段列表（MVP 为空）
- **完成标准**：调用不报错，返回 `[]`
- **测试方法**：`pytest` 直接调用断言返回空列表
- **相关文件**：`apps/ai_core/services/rag_service.py`

---

## 第五阶段：API 测试模块

### T033 实现 OpenAPI 文档导入服务
- **描述**：在 `apps/api_testing/services/openapi_parser.py` 实现 `import_schema(source, content_or_url)` → 创建 `ApiSchema` 记录。校验 JSON 为合法 OpenAPI 3.x。
- **依赖**：→ T013、T020
- **输入**：OpenAPI JSON 字符串或 URL
- **输出**：`ApiSchema` 记录
- **完成标准**：非法文档返回明确 `ValidationError`
- **测试方法**：`pytest` 用最小合法/非法 OpenAPI JSON 测试
- **相关文件**：`apps/api_testing/services/openapi_parser.py`

### T034 实现 endpoint 解析服务
- **描述**：在 `openapi_parser.py` 中实现 `parse_endpoints(schema_id)` → 遍历 paths 创建 `ApiEndpoint` 批量记录。
- **依赖**：→ T033
- **输入**：`ApiSchema` 记录
- **输出**：`ApiEndpoint` 记录（批量）
- **完成标准**：示例 OpenAPI 文档至少解析出 1 个 endpoint
- **测试方法**：`pytest` 用 Petstore 最小示例验证
- **相关文件**：`apps/api_testing/services/openapi_parser.py`

### T035 实现 API 用例生成服务
- **描述**：在 `apps/api_testing/services/case_generator.py` 封装 `generate_cases(endpoint_id, prompt)`，调用 T030 的 workflow，将结果写入 `ApiTestCase`（`generated_by_ai=True`）。
- **依赖**：→ T030、T014
- **输入**：endpoint_id + 用户 prompt
- **输出**：`ApiTestCase` 记录
- **完成标准**：落库的用例 `generated_by_ai=True` 且 `request_data` 非空
- **测试方法**：`pytest` mock workflow 返回值后断言 DB 记录
- **相关文件**：`apps/api_testing/services/case_generator.py`

### T036 实现 HttpRunner 执行服务占位
- **描述**：在 `apps/api_testing/services/runner.py` 实现 `run_api_case(case_id, env_id)` → 返回标准结果 dict `{"status", "duration_ms", "response_data", "error"}`。MVP 先 mock 执行逻辑，用 `requests` 发实际 HTTP 请求。
- **依赖**：→ T014、T011
- **输入**：case_id + env_id
- **输出**：执行结果 dict
- **完成标准**：正常路径返回 status=success；请求异常返回 status=failed + error 信息
- **测试方法**：`pytest` mock `requests.request` 测正常/异常两条路径
- **相关文件**：`apps/api_testing/services/runner.py`

### T037 实现 OpenAPI 导入 API 接口
- **描述**：提供 `POST /api/v1/api-testing/schemas/import`，接收 `source_type` + `content`（或 `url`），调用导入 + 解析服务。
- **依赖**：→ T034、T006
- **输入**：请求体 JSON
- **输出**：`{"schema_id", "endpoint_count"}`
- **完成标准**：成功后 DB 中存在 schema 和 endpoints
- **测试方法**：`pytest` APIClient 提交示例 OpenAPI
- **相关文件**：`apps/api_testing/serializers.py`、`apps/api_testing/views.py`、`apps/api_testing/urls.py`

### T038 实现 ApiEndpoint 列表接口
- **描述**：提供 `GET /api/v1/api-testing/endpoints/`，支持按 `schema_id` 过滤。
- **依赖**：→ T013、T006
- **输入**：查询参数 `schema_id`（可选）
- **输出**：分页 endpoint 列表
- **完成标准**：返回 path/method/summary 字段
- **测试方法**：`pytest` 创建 endpoint 后查询断言
- **相关文件**：`apps/api_testing/serializers.py`、`apps/api_testing/views.py`

### T039 实现 API 用例 AI 生成接口
- **描述**：提供 `POST /api/v1/api-testing/test-cases/ai-generate`，接收 `endpoint_id` + `prompt`。MVP 同步调用生成服务后返回用例。
- **依赖**：→ T035、T006
- **输入**：`{"endpoint_id", "prompt"}`
- **输出**：新建的 `ApiTestCase` 基础信息
- **完成标准**：返回 201 + 用例 ID 且数据库中有记录
- **测试方法**：`pytest` mock AI 服务后调接口断言
- **相关文件**：`apps/api_testing/views.py`、`apps/api_testing/serializers.py`

### T040 实现 ApiTestCase 列表与详情接口
- **描述**：提供 `GET /api/v1/api-testing/test-cases/`（支持 endpoint/project 过滤）和 `GET .../test-cases/{id}/`。
- **依赖**：→ T014、T006
- **输入**：查询参数
- **输出**：用例列表/详情 JSON
- **完成标准**：详情包含完整 `request_data` 和 `assertions`
- **测试方法**：`pytest` CRUD 断言
- **相关文件**：`apps/api_testing/serializers.py`、`apps/api_testing/views.py`

---

## 第六阶段：Web 测试模块

### T041 实现 Web 脚本生成服务
- **描述**：在 `apps/web_testing/services/script_generator.py` 封装 `generate_script(project_id, requirement_text)`，调用 T031 workflow 后写入 `WebTestCase`。
- **依赖**：→ T031、T015
- **输入**：project_id + 自然语言需求
- **输出**：`WebTestCase` 记录（含 `playwright_script`）
- **完成标准**：脚本字段非空且 `generated_by_ai=True`
- **测试方法**：`pytest` mock workflow 后断言落库
- **相关文件**：`apps/web_testing/services/script_generator.py`

### T042 实现 Playwright 执行服务占位
- **描述**：在 `apps/web_testing/services/runner.py` 实现 `run_web_case(case_id, base_url)` → 标准结果 dict。MVP 先写脚本到临时文件 + subprocess 调 pytest，解析退出码。
- **依赖**：→ T015
- **输入**：case_id + base_url
- **输出**：执行结果 dict `{"status", "duration_ms", "stdout", "error"}`
- **完成标准**：脚本执行失败时 status=failed 且有 error 信息
- **测试方法**：`pytest` mock subprocess 正常/异常
- **相关文件**：`apps/web_testing/services/runner.py`

### T043 实现 Web 用例 AI 生成接口
- **描述**：提供 `POST /api/v1/web-testing/test-cases/ai-generate`，接收 `requirement_text`。
- **依赖**：→ T041、T006
- **输入**：`{"requirement_text"}`
- **输出**：新建 `WebTestCase` 信息
- **完成标准**：返回 201 + 包含脚本字段
- **测试方法**：`pytest` mock AI 后调接口
- **相关文件**：`apps/web_testing/serializers.py`、`apps/web_testing/views.py`、`apps/web_testing/urls.py`

### T044 实现 WebTestCase 列表与详情接口
- **描述**：提供 `GET /api/v1/web-testing/test-cases/` 和详情接口。
- **依赖**：→ T015、T006
- **输入**：查询参数
- **输出**：用例列表/详情（含完整 playwright_script）
- **完成标准**：脚本文本不截断
- **测试方法**：`pytest` 验证返回内容完整
- **相关文件**：`apps/web_testing/serializers.py`、`apps/web_testing/views.py`

---

## 第七阶段：执行与报告接口

### T045 实现 TestExecution 列表与详情接口
- **描述**：提供 `GET /api/v1/executions/`（支持按 `execution_type`/`status` 过滤）和 `GET .../executions/{id}/`（含关联 step logs）。
- **依赖**：→ T017、T006
- **输入**：过滤参数
- **输出**：执行记录 + 步骤日志
- **完成标准**：详情接口包含嵌套 step logs 列表
- **测试方法**：`pytest` 创建 execution + steps 后查询验证嵌套
- **相关文件**：`apps/executions/serializers.py`、`apps/executions/views.py`、`apps/executions/urls.py`

### T046 实现 TestReport 查询接口
- **描述**：提供 `GET /api/v1/reports/{execution_id}/`（报告元信息）。
- **依赖**：→ T018、T006
- **输入**：execution_id
- **输出**：报告路径 + metrics JSON
- **完成标准**：无报告时返回 404 + 标准错误格式
- **测试方法**：`pytest` 覆盖有报告/无报告两种场景
- **相关文件**：`apps/reports/serializers.py`、`apps/reports/views.py`、`apps/reports/urls.py`

### T047 实现 ScheduledJob CRUD 接口
- **描述**：提供 `api/v1/scheduler/jobs/` 的 list/create/retrieve/update ViewSet。
- **依赖**：→ T019、T006
- **输入**：cron_expr/job_type/target_id
- **输出**：定时任务 CRUD API
- **完成标准**：可创建、启停（`is_enabled` 切换）、更新 cron
- **测试方法**：`pytest` 覆盖 CRUD + enable/disable
- **相关文件**：`apps/scheduler/serializers.py`、`apps/scheduler/views.py`、`apps/scheduler/urls.py`

---

## 第八阶段：异步任务（Celery）

### T048 定义 API 用例生成 Celery 任务
- **描述**：在 `apps/api_testing/tasks.py` 封装 `generate_api_test_case_task(endpoint_id, prompt)`，内部调用 `case_generator.generate_cases()`。
- **依赖**：→ T035、T007
- **输入**：endpoint_id + prompt
- **输出**：test_case_id
- **完成标准**：`task.delay()` 后查询 DB 有新用例
- **测试方法**：`pytest` 使用 `CELERY_ALWAYS_EAGER=True` 同步执行后断言
- **相关文件**：`apps/api_testing/tasks.py`

### T049 定义 API 用例执行 Celery 任务
- **描述**：封装 `run_api_test_case_task(execution_id)`，创建/更新 `TestExecution` 状态机（`PENDING→RUNNING→SUCCESS|FAILED`），调用 runner 后写结果。
- **依赖**：→ T036、T017、T007
- **输入**：execution_id（调用方预创建）
- **输出**：execution 状态变更 + result_summary
- **完成标准**：成功时 status=SUCCESS；runner 异常时 status=FAILED 且 error 写入 step log
- **测试方法**：`pytest` mock runner 成功/失败两条路径
- **相关文件**：`apps/api_testing/tasks.py`

### T050 定义 Web 用例生成 Celery 任务
- **描述**：在 `apps/web_testing/tasks.py` 封装 `generate_web_test_case_task(project_id, requirement_text)`。
- **依赖**：→ T041、T007
- **输入**：project_id + requirement_text
- **输出**：web_test_case_id
- **完成标准**：异步执行后 DB 有脚本记录
- **测试方法**：`pytest` EAGER 模式断言
- **相关文件**：`apps/web_testing/tasks.py`

### T051 定义 Web 用例执行 Celery 任务
- **描述**：封装 `run_web_test_case_task(execution_id)`，状态机逻辑同 T049。
- **依赖**：→ T042、T017、T007
- **输入**：execution_id
- **输出**：execution 状态变更
- **完成标准**：成功/失败路径状态正确
- **测试方法**：`pytest` mock runner 两条路径
- **相关文件**：`apps/web_testing/tasks.py`

### T052 定义 Allure 报告构建 Celery 任务
- **描述**：在 `apps/reports/tasks.py` 封装 `build_allure_report_task(execution_id)`，调用 allure CLI 生成报告后创建 `TestReport` 记录。
- **依赖**：→ T018、T007
- **输入**：execution_id
- **输出**：`TestReport` 记录（含 report_path）
- **完成标准**：report 记录被创建且 path 非空
- **测试方法**：`pytest` mock allure 命令后断言 DB
- **相关文件**：`apps/reports/tasks.py`、`apps/reports/services.py`

### T053 改造执行接口为异步（返回 202）
- **描述**：将 `POST .../test-cases/{id}/run` 和 `POST .../test-suites/{id}/run`（API/Web 共 4 个）改为：创建 `TestExecution`（PENDING）→ 投递 Celery 任务 → 返回 `202 + {"execution_id"}`。
- **依赖**：→ T049、T051、T040、T044
- **输入**：case_id/suite_id + env_id
- **输出**：`202 Accepted` + execution_id
- **完成标准**：接口立即返回；mock `delay()` 验证任务被调度
- **测试方法**：`pytest` mock `task.delay` 断言返回 202 + DB 有 PENDING execution
- **相关文件**：`apps/api_testing/views.py`、`apps/web_testing/views.py`

### T054 实现定时任务手动触发接口
- **描述**：提供 `POST /api/v1/scheduler/jobs/{id}/trigger`，找到 job → 根据 `job_type` 创建 execution → 投递对应 Celery 任务。
- **依赖**：→ T047、T053
- **输入**：job_id
- **输出**：`202 + {"execution_id"}`
- **完成标准**：触发后 DB 有新 execution 且 Celery 任务被调度
- **测试方法**：`pytest` mock delay 后验证
- **相关文件**：`apps/scheduler/views.py`、`apps/scheduler/services.py`

---

## 执行批次总览

| 批次 | 任务范围 | 目标 |
|------|---------|------|
| A - 项目可运行 | T001-T007 | Django + Celery 骨架跑通 |
| B - 数据可落库 | T008-T020 | 全部模型定义 + 迁移完成 |
| C - 基础业务 API | T021-T025 | 项目管理 CRUD + 统一异常 |
| D - AI 能生成 | T026-T032 | LLM 工厂 + Prompt + LangGraph 工作流 |
| E - API 测试闭环 | T033-T040 | OpenAPI 导入 → AI 生成 → 用例管理 |
| F - Web 测试闭环 | T041-T044 | 自然语言 → 脚本生成 → 用例管理 |
| G - 执行与报告 | T045-T047 | 执行记录 + 报告 + 调度 CRUD |
| H - 异步闭环 | T048-T054 | Celery 任务 + 202 异步接口 + 触发 |

## MVP 最小验收标准

以下 6 项全部通过即达到 MVP 可演示状态：

1. 可导入 OpenAPI 文档并解析出端点（T037）
2. 可对单端点 AI 生成 API 测试用例（T039）
3. 可用自然语言生成 Web UI 测试脚本（T043）
4. 可异步执行 API/Web 用例并追踪状态（T053 + T045）
5. 可查看执行报告信息（T046 + T052）
6. 可创建定时任务并手动触发（T047 + T054）
