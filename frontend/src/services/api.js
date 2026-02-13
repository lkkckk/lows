/**
 * API 服务模块 - 统一封装后端接口调用
 */
import axios from 'axios';

// 创建 axios 实例
const apiClient = axios.create({
    baseURL: '/api',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// 请求拦截器 - 注入管理凭证
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('adminToken');
        if (token) {
            config.headers['X-Admin-Token'] = token;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 响应拦截器 - 统一处理错误
apiClient.interceptors.response.use(
    (response) => response.data,
    (error) => {
        console.error('API 请求错误:', error);
        // 如果后端返回 401，说明密码不正确或过期，清除本地状态并可能需要跳转
        if (error.response && error.response.status === 401) {
            localStorage.removeItem('adminToken');
            // 可以在这里派发跳转登录页的逻辑，或者让组件自行处理
        }
        return Promise.reject(error);
    }
);

// ==================== 法规相关 API ====================

/**
 * 获取法规列表
 */
export const getLawsList = (params) => {
    return apiClient.get('/laws/', { params });
};

/**
 * 获取法规详情
 */
export const getLawDetail = (lawId) => {
    return apiClient.get(`/laws/${lawId}`);
};

/**
 * 获取法规条文列表
 */
export const getLawArticles = (lawId, params) => {
    return apiClient.get(`/laws/${lawId}/articles`, { params });
};

/**
 * 根据条号获取条文
 */
export const getArticleByNumber = (lawId, articleNum) => {
    return apiClient.get(`/laws/${lawId}/articles/${articleNum}`);
};

/**
 * 在单个法规内搜索
 */
export const searchInLaw = (lawId, data) => {
    return apiClient.post(`/laws/${lawId}/search`, data);
};

/**
 * 全库搜索
 */
export const searchGlobal = (data) => {
    return apiClient.post('/laws/search', data);
};

/**
 * 获取法规分类列表
 */
export const getLawCategories = () => {
    return apiClient.get('/laws/meta/categories');
};

/**
 * 获取效力层级列表
 */
export const getLawLevels = () => {
    return apiClient.get('/laws/meta/levels');
};

/**
 * 获取今日浏览统计
 */
export const getTodayViews = () => {
    return apiClient.get('/laws/stats/today-views');
};

/**
 * Get total views stats.
 */
export const getTotalViews = () => {
    return apiClient.get('/laws/stats/total-views');
};

/**
 * 更新法规信息（管理功能）
 */
export const updateLaw = (lawId, data) => {
    return apiClient.patch(`/laws/${lawId}`, data);
};

/**
 * 删除法规（管理功能）
 */
export const deleteLaw = (lawId) => {
    return apiClient.delete(`/laws/${lawId}`);
};

// ==================== 文书模板相关 API ====================

/**
 * 获取模板列表
 */
export const getTemplatesList = (params) => {
    return apiClient.get('/templates/', { params });
};

/**
 * 获取模板详情
 */
export const getTemplateDetail = (templateId) => {
    return apiClient.get(`/templates/${templateId}`);
};

/**
 * 创建模板
 */
export const createTemplate = (data) => {
    return apiClient.post('/templates/', data);
};

/**
 * 更新模板
 */
export const updateTemplate = (templateId, data) => {
    return apiClient.put(`/templates/${templateId}`, data);
};

/**
 * 删除模板
 */
export const deleteTemplate = (templateId) => {
    return apiClient.delete(`/templates/${templateId}`);
};

/**
 * 渲染模板（预览）
 */
export const renderTemplate = (templateId, fieldValues) => {
    return apiClient.post(`/templates/${templateId}/render`, fieldValues);
};

/**
 * 导出为 PDF
 */
export const exportToPDF = (templateId, fieldValues) => {
    return apiClient.post(`/templates/${templateId}/export/pdf`, fieldValues, {
        responseType: 'blob',
    });
};

/**
 * 导出为 DOCX
 */
export const exportToDOCX = (templateId, fieldValues) => {
    return apiClient.post(`/templates/${templateId}/export/docx`, fieldValues, {
        responseType: 'blob',
    });
};

/**
 * 获取模板分类列表
 */
export const getTemplateCategories = () => {
    return apiClient.get('/templates/meta/categories');
};

// ==================== 系统设置相关 API ====================

/**
 * 获取首页弹窗设置
 */
export const getPopupSettings = () => {
    return apiClient.get('/settings/popup');
};

/**
 * 更新首页弹窗设置
 */
export const updatePopupSettings = (data) => {
    return apiClient.put('/settings/popup', data);
};

// ==================== 简易鉴权相关 API ====================

/**
 * 管理员登录
 */
export const adminLogin = (password) => {
    return apiClient.post('/auth/login', { password });
};

// ==================== AI 问法相关 API ====================

/**
 * 发送消息给 AI 法律助手
 * @param {string} message - 用户消息
 * @param {Array} history - 对话历史（可选）
 */
export const sendAiMessage = (message, history = null) => {
    return apiClient.post('/ai/chat', { message, history });
};

/**
 * 提交 AI 回答反馈（好/坏）
 * @param {string} question - 用户问题
 * @param {string} answer - AI 回答
 * @param {boolean} isGood - 是否是好答案
 * @param {Array} sources - 引用来源（可选）
 */
export const submitAiFeedback = (question, answer, isGood, sources = null) => {
    return apiClient.post('/ai/feedback', {
        question,
        answer,
        is_good: isGood,
        sources,
    });
};

/**
 * 获取 AI 模型配置
 */
export const getAiSettings = () => {
    return apiClient.get('/settings/ai');
};

/**
 * 获取 AI 预设模型列表
 */
export const getAiPresets = () => {
    return apiClient.get('/settings/ai/presets');
};

/**
 * 更新 AI 模型配置
 */
export const updateAiSettings = (data) => {
    return apiClient.put('/settings/ai', data);
};

/**
 * 获取 AI Token 累计使用量
 */
export const getAiTokenUsage = () => {
    return apiClient.get('/settings/ai/token-usage');
};

// ==================== IP 访问控制相关 API ====================

/**
 * 获取 IP 访问控制配置
 */
export const getIpAccessSettings = () => {
    return apiClient.get('/settings/ip-access');
};

/**
 * 更新 IP 访问控制配置
 */
export const updateIpAccessSettings = (data) => {
    return apiClient.put('/settings/ip-access', data);
};

// ==================== 内部规章相关 API ====================

/**
 * 检查是否有内部规章数据
 */
export const checkInternalDocs = () => {
    return apiClient.get('/laws/internal-docs/check');
};

/**
 * 获取内部规章列表
 */
export const getInternalDocsList = (page = 1, pageSize = 20) => {
    return apiClient.get(`/laws/internal-docs/list?page=${page}&page_size=${pageSize}`);
};

// ==================== 案件管理相关 API ====================

/**
 * 创建案件
 */
export const createCase = (data) => {
    return apiClient.post('/cases/', data);
};

/**
 * 获取案件列表
 */
export const getCasesList = (params) => {
    return apiClient.get('/cases/', { params });
};

/**
 * 获取案件详情（含笔录摘要）
 */
export const getCaseDetail = (caseId) => {
    return apiClient.get(`/cases/${caseId}`);
};

/**
 * 更新案件
 */
export const updateCase = (caseId, data) => {
    return apiClient.put(`/cases/${caseId}`, data);
};

/**
 * 归档/取消归档案件
 */
export const archiveCase = (caseId, archive = true) => {
    return apiClient.put(`/cases/${caseId}/archive?archive=${archive}`);
};

/**
 * 删除案件
 */
export const deleteCase = (caseId) => {
    return apiClient.delete(`/cases/${caseId}`);
};

// ==================== 笔录管理相关 API ====================

/**
 * 添加笔录（文本方式）
 */
export const createTranscript = (caseId, data) => {
    return apiClient.post(`/cases/${caseId}/transcripts`, data);
};

/**
 * 上传笔录文件
 */
export const uploadTranscript = (caseId, file, meta) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', meta.title);
    formData.append('type', meta.type);
    formData.append('subject_name', meta.subject_name);
    formData.append('subject_role', meta.subject_role);
    formData.append('auto_analyze', String(meta.auto_analyze));
    // postForm 自动处理 multipart Content-Type 和 boundary
    return apiClient.postForm(`/cases/${caseId}/transcripts/upload`, formData, {
        timeout: 60000,
    });
};

/**
 * 获取案件下笔录列表
 */
export const getTranscriptList = (caseId) => {
    return apiClient.get(`/cases/${caseId}/transcripts`);
};

/**
 * 获取笔录详情
 */
export const getTranscriptDetail = (caseId, transcriptId) => {
    return apiClient.get(`/cases/${caseId}/transcripts/${transcriptId}`);
};

/**
 * 删除笔录
 */
export const deleteTranscript = (caseId, transcriptId) => {
    return apiClient.delete(`/cases/${caseId}/transcripts/${transcriptId}`);
};

/**
 * 触发 AI 分析
 */
export const triggerAnalysis = (caseId, transcriptId) => {
    return apiClient.post(`/cases/${caseId}/transcripts/${transcriptId}/analyze`);
};

/**
 * 查询分析状态
 */
export const getAnalysisStatus = (caseId, transcriptId) => {
    return apiClient.get(`/cases/${caseId}/transcripts/${transcriptId}/status`);
};

/**
 * 全局搜索笔录知识库
 */
export const searchTranscripts = (params) => {
    return apiClient.get('/cases/search-transcripts', { params });
};

// ==================== 交叉分析相关 API ====================

/**
 * 触发交叉分析
 */
export const triggerCrossAnalysis = (caseId) => {
    return apiClient.post(`/cases/${caseId}/cross-analyze`);
};

/**
 * 获取交叉分析结果
 */
export const getCrossAnalysis = (caseId) => {
    return apiClient.get(`/cases/${caseId}/cross-analysis`);
};
