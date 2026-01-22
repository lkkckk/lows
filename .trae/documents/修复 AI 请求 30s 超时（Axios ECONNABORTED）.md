## 核心问题分析
用户反馈“问了问题等半天不回答”，实际上是因为当前 AI 采用**非流式（一次性返回）**模式：
1.  **后端机制**：后端必须等 DeepSeek 把几百上千字完全生成完，才一次性发给前端。这通常需要 30~60 秒甚至更久。
2.  **前端体验**：在这几十秒内，前端界面没有任何变化（只有 Loading），用户会觉得“卡死”或“没反应”。
3.  **超时风险**：如果生成时间超过 30 秒（前端默认）或 60 秒（后端默认），请求就会直接断开报错。

## 解决方案：改为流式响应（Streaming）
将“等全部生成完再给”改为**“生成一个字给一个字”**（类似打字机效果）。
- **优势**：用户在 1-2 秒内就能看到第一个字，消除了“等半天”的焦虑；且连接保持活跃，不易超时。

## 实施计划

### 1. 后端改造（Python/FastAPI）
-   **修改 [ai_service.py](file:///d:/law-query-system/backend/app/services/ai_service.py)**：
    -   调用 DeepSeek API 时开启 `stream=True`。
    -   将 `chat_with_ai` 改为异步生成器（`async generator`），实时 `yield` AI 返回的文本块。
-   **修改 [ai.py](file:///d:/law-query-system/backend/app/api/ai.py)**：
    -   将接口响应类型改为 `StreamingResponse`（`text/event-stream`）。

### 2. 前端改造（React/JS）
-   **修改 [api.js](file:///d:/law-query-system/frontend/src/services/api.js)**：
    -   新增 `streamAiMessage` 方法。
    -   由于 Axios 对流式支持较弱，将使用原生 `fetch` 来读取流数据。
-   **修改 [AiConsult.jsx](file:///d:/law-query-system/frontend/src/pages/AiConsult.jsx)**：
    -   替换原来的发送逻辑。
    -   实现**增量渲染**：收到一个数据块就立即拼接到当前对话框中。
    -   优化 UI：移除全屏/整体 Loading，改为在对话气泡中显示光标闪烁。

### 3. 安全与配置优化（顺带修复）
-   将 DeepSeek API Key 移至环境变量，不再硬编码。
-   前端请求超时时间设为“无限制”或极长（仅针对流式读取过程）。

## 预期效果
用户点击发送后，**立刻**能在对话框看到 AI 开始打字，无需漫长等待。

请确认是否执行此改造方案？