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
