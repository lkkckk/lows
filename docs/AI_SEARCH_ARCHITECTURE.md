# AI 智能问法：技术架构与工作流总结

## 1. 核心工作流 (Workflow)

整个"AI问法"功能基于 **RAG (检索增强生成)** 架构，结合了 **Function Calling** 和 **混合检索** 策略。

```mermaid
graph TD
    User[用户提问] --> LLM_Think[大模型思考 (DeepSeek)]
    LLM_Think -- "Function Calling" --> Tool[工具调用: search_legal_knowledge]
    
    subgraph "检索策略层 (LawService)"
        Tool --> Check{有无法律名称?}
        
        Check -- "有 (如: 治安管理处罚法)" --> TitleMatch[标题精确匹配]
        TitleMatch --> VerifyKey{有无具体行为关键词?}
        VerifyKey -- "有 (如: 吸毒)" --> VectorInLaw[限定范围向量搜索]
        VerifyKey -- "无" --> ReturnLaw[返回该法前N条]
        
        Check -- "无" --> VectorSearch[全局向量语义搜索]
        
        VectorSearch -- "未命中/超时" --> KeywordSearch[正则/全文关键词检索]
        VectorInLaw -- "未命中" --> KeywordSearch
    end
    
    VectorSearch & VectorInLaw & KeywordSearch & ReturnLaw --> Context[构建法律上下文]
    Context --> LLM_Gen[大模型生成回答]
    LLM_Gen --> User
```

## 2. 关键技术栈 (Tech Stack)

| 组件 | 技术/工具 | 说明 |
|------|-----------|------|
| **大语言模型** | DeepSeek V3 | 负责意图理解、工具调用、答案生成。通过 API 调用。 |
| **Embedding 模型** | **BAAI/bge-m3** | **核心差异点**。本地离线部署的向量模型，支持多语言、长文本，效果优异。 |
| **向量服务** | FastAPI + Uvicorn | 独立的微服务 (`embedding` 容器)，提供 HTTP 接口将文本转为 1024维向量。 |
| **向量存储** | **MongoDB** | 并没有引入专门的向量库 (如 Milvus/Chroma)，而是直接存储在 `law_articles` 表的 `embedding` 字段中。 |
| **相似度计算** | **NumPy** | 利用后端 Python 的 NumPy 库在内存中进行**余弦相似度 (Cosine Similarity)** 计算。由于法条总数较少 (<5000条)，纯内存计算极快 (<50ms)，无需复杂索引。 |
| **前端交互** | React + Vite | 支持流式输出打字机效果。 |

## 3. 部署与运维工具

为了适应**纯离线、生产环境**，我们构建了一套完整的工具链：

### A. 镜像构建 (开发机)
- **`download_model.py`**: 自动从 HuggingFace 镜像站下载 bge-m3 模型文件。
- **`EmbeddingDockerfile`**: 专用的 Dockerfile，打包了 Python 环境、PyTorch (CPU版) 和模型文件。
- **`prepare_offline_embedding.bat`**: 一键构建脚本，生成 `embedding.tar` 离线镜像包 (约 10GB)。

### B. 生产部署 (生产机)
- **`deploy_package/`**: 独立的部署目录，包含所有必要组件。
- **`deploy.bat`**: 生产环境一键部署脚本，自动加载后端、前端、数据库及向量服务镜像。
- **`init_embedding.bat`**: **关键脚本**。在生产机上运行，自动遍历 MongoDB 中的所有法条，调用本地向量服务生成向量并回写数据库。

### C. 容错与回滚
- **混合检索策略**: 代码中包含 `try/except` 块，如果向量服务超时或报错，自动无缝降级到传统的关键词正则搜索。
- **`VECTOR_SEARCH_ENABLED`**: 环境变量开关。设为 `false` 可完全关闭向量功能，快速回滚。

## 4. 目录结构说明

```
backend/
├── app/
│   ├── services/
│   │   ├── ai_service.py       # 核心检索逻辑，包含混合检索策略
│   │   ├── law_service.py      # 包含 vector_search_for_rag 具体实现
│   │   └── embedding_client.py # 调用 embedding 微服务的客户端
│   └── models/
│       └── bge-m3/             # (容器内) 模型权重文件
├── embedding_server.py         # 向量微服务入口文件
├── EmbeddingDockerfile         # 向量服务构建文件
└── scripts/
    ├── init_vectors.py         # 向量初始化脚本
    └── download_model.py       # 模型下载脚本
```
