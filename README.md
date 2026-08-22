# Knowledge Base

一个面向 RAG（检索增强生成）场景的知识库管理系统。支持用户上传多种格式文档，自动完成**解析 → 清洗 → 分段 → 向量化 → 向量入库**的全流程索引，并提供基于 JWT 的用户体系、知识库/文件管理、以及向量检索接口。后端采用 FastAPI + FastStream 事件驱动架构，通过 Kafka + Transactional Outbox 模式解耦「同步业务事务」与「异步向量索引」，保证消息可靠投递与最终一致性。

---

## 目录

- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [项目结构](#项目结构)
- [后端模块详解（api）](#后端模块详解api)
  - [应用入口与初始化](#应用入口与初始化)
  - [路由层 router/v1](#路由层-routerv1)
  - [服务层 service](#服务层-service)
  - [中间件 middleware](#中间件-middleware)
  - [数据模型 models](#数据模型-models)
  - [核心引擎 core](#核心引擎-core)
  - [扩展 extensions](#扩展-extensions)
  - [公共组件 common](#公共组件-common)
  - [配置 config](#配置-config)
- [异步 Workers（FastStream + Kafka）](#异步-workersfaststream--kafka)
- [前端模块（web）](#前端模块web)
- [核心数据流](#核心数据流)
  - [文档摄取流程](#文档摄取流程)
  - [知识库删除流程](#知识库删除流程)
  - [用户认证流程](#用户认证流程)
- [服务间通信](#服务间通信)
- [环境变量](#环境变量)
- [本地运行](#本地运行)
- [API 概览](#api-概览)
- [部署说明](#部署说明)
- [工程约定与注意事项](#工程约定与注意事项)

---

## 核心特性

- **多格式文档解析**：支持 Markdown、HTML、纯文本、CSV、Excel 等格式（见 [core/extractor](#核心引擎-core)）。
- **灵活分段策略**：通用分段（自定义分隔符/最大 token/重叠）与父子分段（parent-child）模式，支持 QA 模式由 LLM 生成问答对。
- **多嵌入模型适配**：通过工厂模式接入通义千问、火山引擎等 Embedding 供应商。
- **向量库可插拔**：抽象 [vectordb](file:///d:/knowledge/api/core/vectordb) 接口，已实现 Milvus（主）与 Chroma（备）。
- **事件驱动索引**：API 仅写库 + 投递 Kafka 消息，重计算（解析、向量化、删除）由 FastStream Workers 异步消费，主链路低延迟。
- **Transactional Outbox**：业务事务与 Outbox 消息同事务写入，后台 poller 轮询投递到 Kafka，避免「先发消息后回滚」或「先回滚后丢消息」的一致性问题。
- **JWT 认证 + 单点登录踢人**：基于 Redis 维护当前有效 token，新设备登录会使旧 token 失效。
- **速率限制**：注册等敏感接口基于 Redis 固定窗口限流。
- **全局异常处理 + 规范化响应**：统一 `SuccessResponse` / `ErrorResponse`，Swagger 集成 Bearer 鉴权。

---

## 技术栈

### 后端（api）

| 类别 | 选型 | 说明 |
| --- | --- | --- |
| Web 框架 | FastAPI ≥ 0.136 | 异步 API，自带 OpenAPI 文档 |
| ASGI 服务器 | Uvicorn ≥ 0.49 | |
| 消息驱动框架 | FastStream[cli,kafka] ≥ 0.7.2 | Kafka 消费者 + after_startup hook |
| 消息队列 | Kafka（单节点） | 三个 topic：`extract` / `embed` / `delete-dataset` |
| 关系型数据库 | MySQL + asyncmy ≥ 0.2.11 | SQLAlchemy 2.x 异步 ORM |
| 向量数据库 | Milvus 3.x（pymilvus == 3.0.0） | 备选 Chroma |
| 缓存 / 会话 | Redis ≥ 8.0（hiredis） | 登录态、速率限制 |
| 对象存储 | 阿里云 OSS（alibabacloud-oss-v2） | 原始文件存储 |
| LLM SDK | OpenAI ≥ 2.43、火山引擎 ark ≥ 5.0.35 | Embedding + QA 生成 |
| 工具 | jieba、tiktoken、openpyxl、chardet、loguru、python-jose、jwt | 分词/计数/Excel/编码识别/日志/JWT |
| Python | ≥ 3.12 | |
| 代码风格 | Ruff（line-length=120, target py312） | |

### 前端（web）

| 类别 | 选型 |
| --- | --- |
| 框架 | Vue 3 |
| 构建工具 | Vite 5 |
| 路由 | Vue Router 4（hash 模式） |
| UI 库 | Element Plus + @element-plus/icons-vue |
| HTTP 客户端 | Axios |

---

## 系统架构

```
┌──────────────┐      HTTP /api/v1       ┌──────────────────────────────────┐
│   Vue 前端   │  ─────────────────────► │        FastAPI 主应用             │
│  (Vite SSR)  │  ◄── Vite Proxy ────── │  (main.py → init_app)             │
└──────────────┘                         │                                  │
                                         │  Middleware: CORS → Auth → DB     │
                                         │  Router: user/knowledge/file/search│
                                         │  Service: 业务编排               │
                                         └───────────┬───────────┬──────────┘
                                                     │           │
                          ┌──────────────────────────┘           │ 同事务写
                          │  send_broker_message / outbox         │ Outbox 表
                          ▼                                       ▼
                  ┌──────────────────┐  轮询 pending   ┌──────────────────┐
                  │   Kafka Broker    │ ◄──────────── │  Outbox Poller    │
                  │ extract/embed/    │               │ (FastStream 后台)  │
                  │ delete-dataset    │               └──────────────────┘
                  └─────────┬──────────┘
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│ extract worker│    │  embed worker │    │ shard worker     │
│ 解析+分段     │    │  向量化入库   │    │ 删除 dataset     │
│ 投递 embed    │    │  更新状态     │    │ 软删+drop collection│
└──────┬───────┘    └──────┬───────┘    └──────────┬───────┘
       │                   │                       │
       ▼                   ▼                       ▼
  ┌──────────┐       ┌──────────┐            ┌──────────┐
  │  MySQL   │       │  Milvus  │            │  Redis   │
  │ 业务/分段 │       │ 向量索引 │            │ 会话/限流 │
  └──────────┘       └──────────┘            └──────────┘
       ▲                   ▲                       
       │  阿里云 OSS 文件下载  │                       
       └───────────────────┘                       
```

---

## 项目结构

```
knowledge/
├── api/                         # 后端（FastAPI + FastStream）
│   ├── main.py                  # FastAPI 应用入口
│   ├── pyproject.toml           # 依赖与 Ruff 配置
│   ├── env/                     # .env.dev / .env.prod
│   ├── config/                  # settings.py / path_config.py
│   ├── common/                  # 公共组件（jwt/response/enum/...）
│   ├── extensions/              # db / redis / storage / log 扩展
│   ├── middleware/              # auth / db_context / rate_limit
│   ├── models/                  # SQLAlchemy ORM 模型
│   ├── router/v1/               # 路由层 + entites（请求 DTO）
│   ├── schemas/                 # Pydantic 响应/输入 schema
│   ├── service/                 # 业务编排层
│   ├── core/                    # 文档处理核心引擎
│   │   ├── extractor/           # 多格式解析器
│   │   ├── splitter/            # 文本分段
│   │   ├── cleaner/             # 数据清洗
│   │   ├── embeddings/          # Embedding 模型适配
│   │   ├── vectordb/            # 向量库抽象 + Milvus/Chroma
│   │   ├── index_processor/     # 索引处理器工厂（paragraph/parent_child/qa）
│   │   ├── llm_generator/       # LLM 生成 QA
│   │   ├── model_runtime/       # 模型运行时实体
│   │   ├── utils/               # 分页等工具
│   │   └── model_manager.py     # 模型管理
│   ├── workers/                 # FastStream Kafka 消费者
│   │   ├── app.py               # broker + after_startup + send_broker_message
│   │   ├── extract.py           # 解析分段
│   │   ├── embed.py             # 向量化入库
│   │   ├── shard.py             # 删除 dataset
│   │   ├── outbox_poller.py     # Outbox 轮询
│   │   └── entites.py           # 消息体 Pydantic 模型
│   ├── scripts/                 # init_app.py（应用装配）
│   ├── tests/
│   └── logs/
├── web/                         # 前端（Vue 3 + Vite）
│   ├── package.json
│   └── src/
│       ├── router/index.js      # 路由 + 导航守卫
│       ├── layout/MainLayout.vue
│       ├── views/
│       │   ├── Login.vue / Register.vue / Profile.vue
│       │   └── knowledge/{List.vue,FileList.vue}
│       └── components/
├── docs/                        # 文档
├── openspec/                    # OpenSpec 变更管理
│   └── changes/{jwt-auth,user-registration,web-login-register}
└── .gitignore
```

---

## 后端模块详解（api）

### 应用入口与初始化

- [main.py](file:///d:/knowledge/api/main.py)：`create_app()` 创建 FastAPI 实例，加载 `settings.FASTAPI_CONFIG`（`root_path=/api/v1`、Swagger 持久化 Token）。
- [scripts/init_app.py](file:///d:/knowledge/api/scripts/init_app.py)：完成应用装配，依次：
  - `register_exception_handler`：注册 `CustomException` / `HTTPException` / `RequestValidationError` / `ResponseValidationError` / 兜底 `Exception` 处理器，统一返回 `ErrorResponse`。
  - `register_router`：挂载 `knowledge_router` / `search_router` / `user_router` / `file_router`。
  - `register_middleware`：按顺序添加 CORS → AuthMiddleware → DBContextMiddleware（Starlette 中间件为 LIFO 执行，Auth 在 CORS 之后处理真实请求，OPTIONS 直接放行）。
  - `_custom_openapi`：注入全局 Bearer 安全方案，使 Swagger UI 「Authorize」按钮自动附加 `Authorization: Bearer <token>`，并对免登录路径关闭 security 要求。
  - `startup`：连接 Kafka broker；`shutdown`：停止 broker 并关闭 Redis 连接池。

### 路由层 router/v1

| 路由文件 | 前缀 | 主要接口 |
| --- | --- | --- |
| [user.py](file:///d:/knowledge/api/router/v1/user.py) | `/user` | `GET /profile`（需鉴权）、`POST /register`（限流）、`POST /login`、`POST /upload_avator`、`POST /change_password`、`POST /logout` |
| [knowledge.py](file:///d:/knowledge/api/router/v1/knowledge.py) | `/knowledge` | `POST /create`、`POST /upload_file`（→ OSS）、`GET /list`、`GET /get_embedding_models`、`DELETE /{knowledge_id}/detail`、`GET /{knowledge_id}/detail` |
| [file.py](file:///d:/knowledge/api/router/v1/file.py) | `/file` | `GET /{knowledge_id}/list`、`POST /create`（携带分段规则，触发解析流程） |
| [search.py](file:///d:/knowledge/api/router/v1/search.py) | `/search` | `POST /vector`（向量检索，当前为 mock 实现） |

请求 DTO 位于 [router/v1/entites/](file:///d:/knowledge/api/router/v1/entites)（如 `CreateDatasetRequest`、`CreateKnowledgeFileRequest`）。

### 服务层 service

| 服务 | 职责 |
| --- | --- |
| [KnowledgeService](file:///d:/knowledge/api/service/knowledge.py) | 知识库 CRUD、上传文件到 OSS（SHA256 去重 + 临时文件）、删除知识库（软删 Dataset + 同事务写 Outbox 或直发 broker）、获取嵌入模型列表 |
| [UserService](file:///d:/knowledge/api/service/user_service.py) | 注册（密码强度校验 + 弱密码黑名单）、登录（写 Redis 登录态）、登出、修改密码、上传头像 |
| [FileService](file:///d:/knowledge/api/service/file.py) | 文件列表分页、创建文件（落 `KbFile` + `ProcessRule`，并投递 `extract` 消息） |
| [model_service.py](file:///d:/knowledge/api/service/model_service.py) | 模型相关查询 |

### 中间件 middleware

| 中间件 | 文件 | 作用 |
| --- | --- | --- |
| AuthMiddleware | [auth.py](file:///d:/knowledge/api/middleware/auth.py) | OPTIONS 直接放行；非白名单路径校验 `Authorization: Bearer <jwt>`，解析后查 Redis 校验是否当前有效 token，重复登录则踢掉前一个客户端。`get_current_user` 作为依赖注入供路由使用 |
| DBContextMiddleware | [db_context.py](file:///d:/knowledge/api/middleware/db_context.py) | 基于请求上下文创建 / 提交 / 回滚 AsyncSession，无异常提交、有异常回滚，自动关闭 |
| RateLimiter | [rate_limit.py](file:///d:/knowledge/api/middleware/rate_limit.py) | 基于 Redis 固定窗口的限流器，Redis 不可用时 fail-open |

### 数据模型 models

ORM 基类 [base.py](file:///d:/knowledge/api/models/base.py)，软删除采用 `deleted` 字段（`0` 表示未删，删除时写入时间戳）。

| 模型 | 表 | 文件 | 说明 |
| --- | --- | --- | --- |
| `Dataset` | `datasets` | [dataset.py](file:///d:/knowledge/api/models/dataset.py) | 知识库（含 collection_name、embedding_model/provider） |
| `ProcessRule` | `process_rules` | [dataset.py](file:///d:/knowledge/api/models/dataset.py) | 分段规则（通用 + 父子模式参数） |
| `KbFile` | `kb_files` | [document.py](file:///d:/knowledge/api/models/document.py) | 知识库文件（状态机：waiting→processing→indexing→success/failed） |
| `FileSegments` | `file_segments` | [document.py](file:///d:/knowledge/api/models/document.py) | 父分段，含 `point_id` 关联向量库主键 |
| `ChildSegment` | `child_segments` | [document.py](file:///d:/knowledge/api/models/document.py) | 子分段（parent-child 模式） |
| `UploadFile` | `upload_files` | [document.py](file:///d:/knowledge/api/models/document.py) | 已上传原始文件元信息（哈希、size、ext） |
| `OutboxMessage` | `outbox_messages` | [outbox.py](file:///d:/knowledge/api/models/outbox.py) | Outbox 消息（topic、payload、status、retry_count、next_retry_at） |
| `User` | `users` | [user.py](file:///d:/knowledge/api/models/user.py) | 用户 |

### 核心引擎 core

| 子模块 | 关键文件 | 职责 |
| --- | --- | --- |
| `extractor/` | [extract_processor.py](file:///d:/knowledge/api/core/extractor/extract_processor.py) | 文档解析调度，按扩展名路由到具体解析器 |
| | `text_extractor.py` / `markdown_extractor.py` / `html_extractor.py` / `csv_extractor.py` / `excel_extractor.py` | 各格式解析实现，均继承 `extractor_base.py` |
| `splitter/` | `text_splitter.py` / `fixed_text_splitter.py` | 按 separator / max_tokens / overlap 切片 |
| `cleaner/` | `clean_processor.py` / `cleaner_base.py` | 预处理规则（去 URL/邮箱、去多余空白等） |
| `embeddings/` | [factory.py](file:///d:/knowledge/api/core/embeddings/factory.py) | Embedding 工厂，接入 `tongyi.py`（通义）/`volcengine.py`（火山） |
| `vectordb/` | [factory.py](file:///d:/knowledge/api/core/vectordb/factory.py) | 向量库抽象工厂；`milvus.py` 主实现，`chroma.py` 备选；`entites.py` 为 Filter/Vector 等数据结构 |
| `index_processor/` | [index_processor_factory.py](file:///d:/knowledge/api/core/index_processor/index_processor_factory.py) | 按 `segment_mode` 选择处理器：`paragraph_index_processor.py`、`parent_child_index_processor.py`、`qa_index_processor.py`；常量见 `constant/index_type.py` |
| `llm_generator/` | `llm_generator.py` + `prompts.py` | QA 模式下由 LLM 生成问答对 |
| `model_runtime/` | `message_entities.py` | 模型运行时消息实体 |
| `model_manager.py` | | 模型实例管理 |
| `utils/page.py` | | 通用分页工具（`paginate` / `Page` / `PaginationInput`） |

### 扩展 extensions

| 扩展 | 文件 | 作用 |
| --- | --- | --- |
| `ext_db` | [ext_db.py](file:///d:/knowledge/api/extensions/ext_db.py) | `FastapiDB`：基于 `ContextVar` 管理请求级 AsyncSession；`async_session_factory` 供 workers 独立使用 |
| `ext_redis` | [ext_redis.py](file:///d:/knowledge/api/extensions/ext_redis.py) | `FastapiRedis`：连接池 + `incr/expire/lock/get/set/delete` 封装 |
| `ext_storage` | [ext_storage.py](file:///d:/knowledge/api/extensions/ext_storage.py) | `AliYunOSS`：异步 `put_object` / `download_file`，同步 `get_signed_url` 签名下载 |
| `ext_log` | [ext_log.py](file:///d:/knowledge/api/extensions/ext_log.py) | loguru 日志封装 |

### 公共组件 common

[common/](file:///d:/knowledge/api/common) 提供：`jwt.py`（token 编解码）、`password.py`（哈希/校验）、`weak_passwords.py`（弱密码黑名单）、`response.py`（`SuccessResponse`/`ErrorResponse`）、`code.py`（响应码枚举）、`enum.py`（`FileStatus`/`SegmentStatus`/`OutBoxStatus` 等）、`entites.py`（`ModelConfig`/`Document`/`ExtractSetting`/`ProcessRule` 等 DTO）、`decorators.py`（`retry_until_success`）、`error.py`（`CustomException`）、`const.py`（Redis key 模板）、`async_pool.py`（异步线程池）。

### 配置 config

- [settings.py](file:///d:/knowledge/api/config/settings.py)：`Settings(BaseSettings)` 从 `env/.env.{ENV}` 加载（默认 `dev`）。集中管理 MySQL/Redis/Milvus/Kafka/JWT/OSS/模型列表/分段参数等配置，并提供 `DATABASE_URL`、`REDIS_URL`、`MILVUS_URL`、`FASTAPI_CONFIG` 派生属性。`MODELS` 字段支持 JSON 字符串自动解析为 `list[ModelConfig]`。
- `path_config.py`：路径常量（`ENV_DIR` 等）。

---

## 异步 Workers（FastStream + Kafka）

入口 [workers/app.py](file:///d:/knowledge/api/workers/app.py)：

- 创建 `KafkaBroker(settings.BROKER_URL)` 与 `FastStream` app。
- `@app.after_startup` 启动 `poll_outbox()` 后台任务（受 `START_BROKER_OUTBOX` 开关控制）。
- `send_broker_message(topic, message)`：带 `retry_until_success` 装饰器的发布助手，供 API/Worker 复用。
- **显式导入** `embed` / `extract` / `shard` 三个订阅者模块，使 `@broker.subscribe` 装饰器生效。

| Worker | 文件 | 订阅 topic | 流程 |
| --- | --- | --- | --- |
| `extract` | [extract.py](file:///d:/knowledge/api/workers/extract.py) | `extract` | 查 `KbFile` + `ProcessRule` → 置文件为 `processing` → `IndexProcessorFactory` 按 `segment_mode` 解析 + transform → 落 `FileSegments`/`ChildSegment` → 按 `EMBDED_BATCH_SIZE` 分批投递 `embed` 消息；失败置 `failed` 并写 `failed_reason` |
| `embed` | [embed.py](file:///d:/knowledge/api/workers/embed.py) | `embed` | 查 `Dataset`/`KbFile`/`ProcessRule` → `index_processor.load` 写入 Milvus（父子模式分别处理）→ 回写 segment `point_id` 与状态 → 汇总更新文件状态（`indexing`/`success`/`failed`） |
| `delete_dataset`（shard） | [shard.py](file:///d:/knowledge/api/workers/shard.py) | `delete-dataset` | 软删 `FileSegments`/`ChildSegment` → `VectorFactory(dataset).drop_collection()`；`AckPolicy.NACK_ON_ERROR` 保证失败重投，处理幂等 |
| outbox poller | [outbox_poller.py](file:///d:/knowledge/api/workers/outbox_poller.py) | — | 每 5s 轮询 `pending` 消息，`SELECT ... FOR UPDATE SKIP LOCKED` 防并发抢占；发送成功标 `sent`，失败指数退避（`retry_count` 达 10 标 `failed`） |

消息体定义见 [workers/entites.py](file:///d:/knowledge/api/workers/entites.py)：`ExtracMessage` / `EmbedMessage` / `DeleteDatasetMessage`。

---

## 前端模块（web）

- [router/index.js](file:///d:/knowledge/web/src/router/index.js)：Hash 模式路由。导航守卫：无 `access_token` 跳转登录；已登录用户访问登录/注册页自动重定向到知识库列表。
- 路由表：
  - `/login`、`/register`（`meta.guest`，登录态访问会跳走）
  - `/`（`MainLayout`）→ 重定向 `/knowledge`，子路由：`/knowledge`、`/knowledge/:knowledgeId/files`、`/profile`
- 页面：
  - [Login.vue](file:///d:/knowledge/web/src/views/Login.vue) / [Register.vue](file:///d:/knowledge/web/src/views/Register.vue)
  - [Profile.vue](file:///d:/knowledge/web/src/views/Profile.vue)
  - [knowledge/List.vue](file:///d:/knowledge/web/src/views/knowledge/List.vue)（知识库列表）
  - [knowledge/FileList.vue](file:///d:/knowledge/web/src/views/knowledge/FileList.vue)（知识库文件列表）
- [layout/MainLayout.vue](file:///d:/knowledge/web/src/layout/MainLayout.vue)：主框架布局。
- HTTP：Axios 使用相对 baseURL `/api/v1`，开发环境由 Vite dev server 代理转发至后端。

---

## 核心数据流

### 文档摄取流程

```
1. 前端 POST /api/v1/knowledge/upload_file  (multipart)
   └─ KnowledgeService.upload_file
        ├─ 暂存临时文件 + SHA256
        ├─ storage.put_object → 阿里云 OSS
        └─ 写 upload_files 表

2. 前端 POST /api/v1/file/create  (file_key + 分段规则)
   └─ FileService.create_file
        ├─ 写 kb_files (status=waiting) + process_rules
        └─ 投递 extract 消息到 Kafka (或经 Outbox)

3. extract worker (Kafka: extract)
   ├─ 置 kb_files.status = processing
   ├─ IndexProcessorFactory.extract → OSS 下载 → 解析
   ├─ transform → 清洗 + 分段 (父子模式生成 child_docs)
   ├─ 写 file_segments / child_segments
   └─ 按 EMBDED_BATCH_SIZE 分批投递 embed 消息

4. embed worker (Kafka: embed)
   ├─ index_processor.load → 调用 Embedding → 写入 Milvus
   ├─ 回写 segments.point_id + status=completed
   ├─ 父子模式：等所有 child 完成后置 parent=completed
   └─ 汇总更新 kb_files.status (indexing/success/failed)
```

### 知识库删除流程

```
前端 DELETE /api/v1/knowledge/{id}/detail
└─ KnowledgeService.delete_knowledge
   ├─ 校验存在 + 归属
   ├─ 软删 datasets (deleted=timestamp)
   └─ 若 START_BROKER_OUTBOX:
        同事务写 outbox_messages(topic=delete-dataset)
        → outbox_poller 轮询投递到 Kafka
      否则:
        直接 send_broker_message 投递 delete-dataset

shard worker (Kafka: delete-dataset, NACK_ON_ERROR)
├─ 软删 file_segments / child_segments
├─ VectorFactory(dataset).drop_collection() → Milvus 删集合
└─ 失败重投，处理幂等
```

> 关键一致性约束：**先软删 MySQL，后 drop Milvus collection**；Outbox 消息与业务数据在**同一事务**提交，避免消息丢失或孤儿向量数据。

### 用户认证流程

```
登录: POST /user/login
└─ UserService.login
   ├─ 校验密码 (password.py)
   ├─ 签发 access_token (python-jose, HS256)
   └─ Redis 写 USER_LOGIN_CACHE_KEY / USER_HAS_LOGIN_CACHE_KEY

鉴权: AuthMiddleware
├─ OPTIONS 直接放行 (避免 CORS 预检失败)
├─ 白名单 (/user/login, /user/register, /docs, /openapi.json ...) 跳过
├─ 解析 Bearer JWT → 取 user_id
├─ Redis 校验当前 token 是否为最新 (单点登录踢人)
└─ 失败返回 401 JSONResponse

登出: POST /user/logout → 删除 Redis 登录态
```

---

## 服务间通信

| 通信路径 | 方式 | 说明 |
| --- | --- | --- |
| 前端 ↔ API | HTTP REST（`/api/v1`） | 开发：Vite proxy；生产：Nginx 反代 |
| API → Kafka | `send_broker_message` 或 Outbox | Outbox 模式保证事务一致性 |
| Workers ← Kafka | `@broker.subscriber`（FastStream） | 消费者组 `knowledge-worker`，`auto_offset_reset` 可配 |
| Workers → MySQL | SQLAlchemy async + asyncmy | 独立 session（`async_session_factory`），需显式 commit |
| Workers → Milvus | pymilvus | 通过 `VectorFactory` |
| API/Workers → Redis | redis.asyncio + hiredis | 登录态、限流、Outbox 无关 |
| API → 阿里云 OSS | alibabacloud-oss-v2（async） | 文件上传/下载/签名 URL |
| LLM 调用 | OpenAI SDK / 火山引擎 ark | Embedding 与 QA 生成 |

---

## 环境变量

完整定义见 [config/settings.py](file:///d:/knowledge/api/config/settings.py)，配置文件位于 [env/.env.dev](file:///d:/knowledge/api/env/.env.dev) 与 `env/.env.prod`，通过环境变量 `ENV` 切换（默认 `dev`）。

| 变量 | 说明 |
| --- | --- |
| `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` | MySQL 连接 |
| `MYSQL_POOL_SIZE` / `MYSQL_MAX_OVERFLOW_SIZE` / `MYSQL_POOL_RECYCLE` | 连接池参数 |
| `REDIS_HOST/PORT/PASSWORD/DB/USERNAME` | Redis 连接 |
| `JWT_SECRET_KEY` / `JWT_ALGORITHM` / `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` / `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | JWT 配置（生产务必替换密钥） |
| `MILVUS_HOST/PORT/USERNAME/PASSWORD/DB` | Milvus 连接（默认 DB=`knowledge`） |
| `MODELS` | JSON 字符串，模型配置列表（type/provider/name/config） |
| `ALIYUN_OSS_ACCESS_KEY/SECRET/BUCKET/REGION/ENDPOINT` | 阿里云 OSS |
| `INDEXING_MAX_SEGMENTATION_TOKENS_LENGTH` / `CHILD_CHUNKS_PREVIEW_NUMBER` / `QA_MODEL_NAME` | 索引参数 |
| `BROKER_URL` | Kafka 地址 |
| `BROKER_AUTO_OFFSET_RESET` | 消费位移策略（`latest`/`earliest`） |
| `BROKER_GROUP_ID` | 消费者组（默认 `knowledge-worker`） |
| `BROKER_MAX_PULL_RECORDS` | 单次最大拉取数 |
| `EXTRACTOR_TOPIC` / `EXTRACT_MAX_WORKERS` | 解析 topic 与并发 |
| `EMBED_TOPIC` / `EMBED_MAX_WORKERS` / `EMBDED_BATCH_SIZE` | 嵌入 topic、并发、批量 |
| `DELETE_DATASET_TOPIC` / `DELETE_DATASET_MAX_WORKERS` | 删除 topic 与并发 |
| `START_BROKER_OUTBOX` | 是否启用 Outbox 模式（true 时消息经 outbox 表投递） |

---

## 本地运行

### 前置依赖

- Python ≥ 3.12（推荐 [uv](https://github.com/astral-sh/uv) 管理依赖）
- Node.js（用于前端）
- MySQL、Redis、Kafka（单节点）、Milvus

### 后端

```bash
cd api

# 1. 安装依赖
uv sync                  # 或 pip install -e .

# 2. 配置环境变量
cp env/.env.dev env/.env.dev.local   # 按需修改
export ENV=dev                       # Windows PowerShell: $env:ENV="dev"

# 3. 启动 FastAPI
uvicorn main:app --reload --port 5000

# 4. 启动 FastStream Workers（另开终端）
faststream run workers.app:app
```

Swagger 文档：`http://localhost:5000/api/v1/docs`（root_path 为 `/api/v1`）。

### 前端

```bash
cd web
npm install
npm run dev
```

前端开发服务器通过 Vite proxy 将 `/api` 转发至后端，访问前端后即可走通整条链路。

---

## API 概览

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| GET | `/user/profile` | 是 | 当前用户信息 |
| POST | `/user/register` | 否（限流） | 注册 |
| POST | `/user/login` | 否 | 登录，返回 `access_token` |
| POST | `/user/upload_avator` | 是 | 上传头像 |
| POST | `/user/change_password` | 是 | 修改密码 |
| POST | `/user/logout` | 是 | 登出 |
| POST | `/knowledge/create` | 是 | 创建知识库 |
| POST | `/knowledge/upload_file` | 是 | 上传文件到 OSS |
| GET | `/knowledge/list` | 是 | 知识库分页列表 |
| GET | `/knowledge/get_embedding_models` | 否 | 可用嵌入模型 |
| GET | `/knowledge/{id}/detail` | 否 | 知识详情 |
| DELETE | `/knowledge/{id}/detail` | 是 | 删除知识库（异步） |
| GET | `/file/{knowledge_id}/list` | 是 | 知识库文件列表 |
| POST | `/file/create` | 是 | 创建文件（触发解析流程） |
| POST | `/search/vector` | 否 | 向量搜索（mock） |

---

## 部署说明

- **生产前端**：`npm run build` 后由 Nginx 托管静态资源，并反代 `/api` 至后端。
- **生产后端**：使用 `env/.env.prod`，`ENV=prod` 启动；uvicorn 多 worker 部署。
- **Workers**：必须以独立进程运行 `faststream run workers.app:app`，否则 Kafka 消费者不会注册。
- **基础设施**：
  - MySQL：建库后由 SQLAlchemy 模型建表（或迁移脚本）。
  - Milvus：单机可用官方 `standalone_embed.sh` 启动；Windows/WSL2 下若遇权限问题，可加 `--user 0:0` 以 root 运行并清理残留 volumes。
  - Kafka：单节点需将 `offsets.topic.replication.factor=1`，并保证 `__consumer_offsets` topic 存在（1 分区、副本数 1），否则触发 `Group CoordinatorNotAvailableError`。
  - Redis、阿里云 OSS：按 `.env.prod` 配置。

---

## 工程约定与注意事项

- **中间件顺序**：Starlette/FastAPI 中间件 LIFO 执行。必须 CORS 先于 Auth 注册，Auth 中对 `OPTIONS` 预检直接放行，避免 CORS 失败。
- **Workers 显式导入**：`extract.py` / `embed.py` / `shard.py` 必须在 [workers/app.py](file:///d:/knowledge/api/workers/app.py) 末尾显式 import，`@broker.subscribe` 才会被注册。
- **Worker session 生命周期**：Workers 不经过 `DBContextMiddleware`，需用 `async_session_factory()` 自行管理 session，且 `execute()` 后必须显式 `commit()` 才能持久化。
- **删除一致性**：先软删 MySQL、后 drop Milvus collection；Kafka 删除消息在 MySQL 事务提交前写入（或经 Outbox 同事务），防止产生孤儿向量数据。
- **消费位移**：`auto_offset_reset=latest` 会跳过 worker 启动前发送的消息；首次启动或消费历史消息需用 `earliest`。
- **FastStream after_startup**：hook 必须是**无参 async 函数**，否则 Pydantic 校验失败。
- **MySQL 软删除**：`deleted` 字段用时间戳（`0` 表示未删），非 0/1 布尔。
- **代码风格**：Ruff（`target-version=py312`、`line-length=120`），import 排序已知首方包为 `config/extensions/models/router`。

---

## OpenSpec 变更管理

[openspec/changes/](file:///d:/knowledge/openspec/changes) 目录记录了项目的演进式变更提案：

- [jwt-auth](file:///d:/knowledge/openspec/changes/jwt-auth/proposal.md)：JWT 登录、Auth 中间件、token 刷新、受保护的 profile 路由。
- [user-registration](file:///d:/knowledge/openspec/changes/user-registration/proposal.md)：用户注册能力、密码哈希与强度校验、注册接口限流。
- [web-login-register](file:///d:/knowledge/openspec/changes/web-login-register/proposal.md)：前端登录/注册 UI 改造、动画、主题与后端鉴权接口集成。
