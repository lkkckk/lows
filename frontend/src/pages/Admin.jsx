/**
 * 后台管理页面 - 模块化重构版
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import {
    Settings, Trash2, Edit3, Eye, AlertTriangle, ChevronLeft, X, Save,
    Bell, ToggleLeft, ToggleRight, LogOut, LayoutDashboard, BookOpen,
    PieChart, TrendingUp, FileText, Bot, Shield, Network, Sparkles
} from 'lucide-react';
import { getLawsList, updateLaw, deleteLaw, getLawCategories, getLawLevels, getPopupSettings, updatePopupSettings, getTodayViews, getTotalViews, getAiSettings, getAiPresets, updateAiSettings, getIpAccessSettings, updateIpAccessSettings, getAiTokenUsage } from '../services/api';
import '../styles/Admin.css';

const STATUS_OPTIONS = [
    { value: '现行有效', label: '现行有效', color: '#10b981' },
    { value: '已废止', label: '已废止', color: '#ef4444' },
    { value: '尚未生效', label: '尚未生效', color: '#f59e0b' },
    { value: '已修订', label: '已修订', color: '#6b7280' },
];

// 分类和层级选项将从 API 动态获取
const DEFAULT_CATEGORY_OPTIONS = ['刑事法律', '行政法律', '民事法律', '程序规定', '司法解释', '内部规章', '部门条例', '地方条例', '实施办法', '其他'];
const DEFAULT_LEVEL_OPTIONS = ['宪法', '法律', '行政法规', '地方性法规', '部门规章', '司法解释', '其他'];

// ==================== 仪表盘模块 ====================
const DashboardModule = ({ laws, todayViews, totalViews, tokenUsage }) => {
    // 计算分类统计
    const categoryStats = useMemo(() => {
        const stats = {};
        laws.forEach(law => {
            const cat = law.category || '未分类';
            stats[cat] = (stats[cat] || 0) + 1;
        });
        return Object.entries(stats).sort((a, b) => b[1] - a[1]);
    }, [laws]);

    // 计算层级统计
    const levelStats = useMemo(() => {
        const stats = {};
        laws.forEach(law => {
            const lvl = law.level || '未分类';
            stats[lvl] = (stats[lvl] || 0) + 1;
        });
        return Object.entries(stats).sort((a, b) => b[1] - a[1]);
    }, [laws]);

    // 计算状态统计
    const statusStats = useMemo(() => {
        const stats = {};
        laws.forEach(law => {
            const st = law.status || '未知';
            stats[st] = (stats[st] || 0) + 1;
        });
        return Object.entries(stats);
    }, [laws]);

    return (
        <div className="dashboard-module">
            {/* 概览卡片 */}
            <div className="stats-cards">
                <div className="stat-card primary">
                    <div className="stat-icon"><BookOpen size={28} /></div>
                    <div className="stat-info">
                        <span className="stat-value">{laws.length}</span>
                        <span className="stat-label">法规总数</span>
                    </div>
                </div>
                <div className="stat-card success">
                    <div className="stat-icon"><FileText size={28} /></div>
                    <div className="stat-info">
                        <span className="stat-value">{categoryStats.length}</span>
                        <span className="stat-label">分类数量</span>
                    </div>
                </div>
                <div className="stat-card info">
                    <div className="stat-icon"><Eye size={28} /></div>
                    <div className="stat-info">
                        <span className="stat-value">{totalViews}</span>
                        <span className="stat-label">总浏览量</span>
                    </div>
                </div>
                <div className="stat-card warning">
                    <div className="stat-icon"><TrendingUp size={28} /></div>
                    <div className="stat-info">
                        <span className="stat-value">{todayViews}</span>
                        <span className="stat-label">今日浏览</span>
                    </div>
                </div>
                <div className="stat-card" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)' }}>
                    <div className="stat-icon" style={{ background: 'rgba(255,255,255,0.2)' }}><Sparkles size={28} /></div>
                    <div className="stat-info">
                        <span className="stat-value">{tokenUsage.total_tokens?.toLocaleString() || 0}</span>
                        <span className="stat-label">AI Token 用量</span>
                    </div>
                </div>
            </div>

            {/* 分类与层级分布 */}
            <div className="chart-row">
                <div className="chart-card">
                    <h4><PieChart size={18} /> 分类分布</h4>
                    <div className="bar-chart">
                        {categoryStats.map(([cat, count]) => (
                            <div key={cat} className="bar-item">
                                <span className="bar-label">{cat}</span>
                                <div className="bar-track">
                                    <div
                                        className="bar-fill"
                                        style={{ width: `${(count / laws.length) * 100}%` }}
                                    />
                                </div>
                                <span className="bar-value">{count}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="chart-card">
                    <h4><PieChart size={18} /> 效力层级</h4>
                    <div className="bar-chart">
                        {levelStats.slice(0, 5).map(([lvl, count]) => (
                            <div key={lvl} className="bar-item">
                                <span className="bar-label">{lvl}</span>
                                <div className="bar-track">
                                    <div
                                        className="bar-fill secondary"
                                        style={{ width: `${(count / laws.length) * 100}%` }}
                                    />
                                </div>
                                <span className="bar-value">{count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* 状态统计 */}
            <div className="status-summary">
                <h4>效力状态统计</h4>
                <div className="status-tags">
                    {statusStats.map(([st, count]) => {
                        const opt = STATUS_OPTIONS.find(o => o.value === st);
                        return (
                            <span
                                key={st}
                                className="status-tag"
                                style={{ borderColor: opt?.color || '#6b7280', color: opt?.color || '#6b7280' }}
                            >
                                {st}: {count}
                            </span>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

// ==================== 法规管理模块 ====================
const LawsModule = ({ laws, onEdit, onDelete, onView }) => {
    const getStatusColor = (status) => {
        const option = STATUS_OPTIONS.find(o => o.value === status);
        return option ? option.color : '#6b7280';
    };

    return (
        <div className="laws-module">
            <table className="admin-table">
                <thead>
                    <tr>
                        <th style={{ width: '30%' }}>法规名称</th>
                        <th style={{ width: '10%' }}>制定机关</th>
                        <th style={{ width: '10%' }}>分类</th>
                        <th style={{ width: '10%' }}>层级</th>
                        <th style={{ width: '10%' }}>状态</th>
                        <th style={{ width: '10%' }}>实施日期</th>
                        <th style={{ width: '10%' }}>公布日期</th>
                        <th style={{ width: '10%' }}>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {laws.map((law) => (
                        <tr key={law.law_id}>
                            <td className="law-title-cell">
                                <span className="law-title" onClick={() => onView(law.law_id)}>
                                    {law.title}
                                </span>
                            </td>
                            <td>{law.issue_org || '-'}</td>
                            <td>{law.category}</td>
                            <td>{law.level}</td>
                            <td>
                                <span
                                    className="status-badge"
                                    style={{ borderColor: getStatusColor(law.status), color: getStatusColor(law.status) }}
                                >
                                    {law.status}
                                </span>
                            </td>
                            <td>{law.effect_date || law.issue_date || '-'}</td>
                            <td>{law.issue_date || '-'}</td>
                            <td className="actions-cell">
                                <button className="action-btn view-btn" onClick={() => onView(law.law_id)} title="查看">
                                    <Eye size={16} />
                                </button>
                                <button className="action-btn edit-btn" onClick={() => onEdit(law)} title="编辑">
                                    <Edit3 size={16} />
                                </button>
                                <button className="action-btn delete-btn" onClick={() => onDelete(law)} title="删除">
                                    <Trash2 size={16} />
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {laws.length === 0 && (
                <div className="empty-state">
                    <p>暂无法规数据</p>
                </div>
            )}
        </div>
    );
};

// ==================== 系统设置模块 ====================
// ==================== 系统设置模块 ====================
const SettingsModule = ({ popupSettings, onPopupChange, onPopupSave, popupSaving, aiSettings, aiPresets, onAiChange, onAiPresetChange, onAiSave, aiSaving, ipAccessSettings, onIpAccessChange, onIpWhitelistChange, onIpAccessSave, ipAccessSaving }) => {
    const [activeTab, setActiveTab] = useState('ai'); // 'ai' | 'ip' | 'popup'

    return (
        <div className="settings-module">
            {/* 标签导航栏 */}
            <div className="settings-tabs-header">
                <button
                    className={`tab-btn ${activeTab === 'ai' ? 'active' : ''}`}
                    onClick={() => setActiveTab('ai')}
                >
                    <Bot size={18} />
                    <span>AI 模型</span>
                </button>
                <button
                    className={`tab-btn ${activeTab === 'ip' ? 'active' : ''}`}
                    onClick={() => setActiveTab('ip')}
                >
                    <Network size={18} />
                    <span>IP 访问控制</span>
                </button>
                <button
                    className={`tab-btn ${activeTab === 'popup' ? 'active' : ''}`}
                    onClick={() => setActiveTab('popup')}
                >
                    <Bell size={18} />
                    <span>首页弹窗</span>
                </button>
            </div>

            {/* AI 模型配置内容 */}
            {activeTab === 'ai' && (
                <div className="settings-tab-content">
                    <div className="settings-card">
                        <div className="section-header">
                            <Bot size={20} />
                            <h3>AI 模型配置</h3>
                        </div>
                        <div className="section-body">
                            <div className="form-group">
                                <label>选择模型</label>
                                <div className="radio-group">
                                    {Object.entries(aiPresets).map(([key, preset]) => (
                                        <label key={key} className="radio-label">
                                            <input
                                                type="radio"
                                                name="ai_provider"
                                                value={key}
                                                checked={aiSettings.provider === key}
                                                onChange={() => onAiPresetChange(key)}
                                            />
                                            <span>{preset.name}</span>
                                        </label>
                                    ))}
                                    <label className="radio-label">
                                        <input
                                            type="radio"
                                            name="ai_provider"
                                            value="custom"
                                            checked={aiSettings.provider === 'custom'}
                                            onChange={() => onAiChange('provider', 'custom')}
                                        />
                                        <span>自定义</span>
                                    </label>
                                </div>
                            </div>
                            <div className="form-group">
                                <label>API URL</label>
                                <input
                                    type="text"
                                    placeholder="例如：https://api.deepseek.com/v1/chat/completions"
                                    value={aiSettings.api_url}
                                    onChange={(e) => onAiChange('api_url', e.target.value)}
                                />
                            </div>
                            <div className="form-group">
                                <label>API Key</label>
                                <input
                                    type="password"
                                    placeholder="输入 API Key"
                                    value={aiSettings.api_key}
                                    onChange={(e) => onAiChange('api_key', e.target.value)}
                                />
                            </div>
                            <div className="form-group">
                                <label>模型名称</label>
                                <input
                                    type="text"
                                    placeholder="例如：deepseek-chat"
                                    value={aiSettings.model_name}
                                    onChange={(e) => onAiChange('model_name', e.target.value)}
                                />
                            </div>
                            <div className="form-group checkbox-group">
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={aiSettings.skip_ssl_verify}
                                        onChange={(e) => onAiChange('skip_ssl_verify', e.target.checked)}
                                    />
                                    <Shield size={16} />
                                    <span>忽略 SSL 证书验证（内网自建模型可能需要）</span>
                                </label>
                            </div>
                            <div className="card-footer">
                                <button className="btn-primary full-width" onClick={onAiSave} disabled={aiSaving}>
                                    <Save size={16} />
                                    {aiSaving ? '保存中...' : '保存 AI 配置'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* IP 访问控制内容 */}
            {activeTab === 'ip' && (
                <div className="settings-tab-content">
                    <div className="settings-card">
                        <div className="section-header">
                            <Network size={20} />
                            <h3>IP 访问控制</h3>
                        </div>
                        <div className="section-body">
                            {/* AI 问法 IP 限制 */}
                            <div className="ip-control-group">
                                <div className="ip-control-header">
                                    <span className="ip-control-title">AI 问法</span>
                                    <button
                                        className={`toggle-switch small ${ipAccessSettings.ai_enabled ? 'active' : ''}`}
                                        onClick={() => onIpAccessChange('ai_enabled', !ipAccessSettings.ai_enabled)}
                                    >
                                        {ipAccessSettings.ai_enabled ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
                                        <span>{ipAccessSettings.ai_enabled ? '已开启' : '已关闭'}</span>
                                    </button>
                                </div>
                                {ipAccessSettings.ai_enabled && (
                                    <div className="form-group">
                                        <label>IP 白名单（CIDR 格式，每行一个）</label>
                                        <textarea
                                            placeholder="例如：192.168.1.0/24&#10;10.0.0.0/8"
                                            value={ipAccessSettings.ai_whitelist?.join('\n') || ''}
                                            onChange={(e) => onIpWhitelistChange('ai_whitelist', e.target.value)}
                                            rows={3}
                                        />
                                    </div>
                                )}
                            </div>

                            {/* 内部规章 IP 限制 */}
                            <div className="ip-control-group">
                                <div className="ip-control-header">
                                    <span className="ip-control-title">内部规章</span>
                                    <button
                                        className={`toggle-switch small ${ipAccessSettings.internal_docs_enabled ? 'active' : ''}`}
                                        onClick={() => onIpAccessChange('internal_docs_enabled', !ipAccessSettings.internal_docs_enabled)}
                                    >
                                        {ipAccessSettings.internal_docs_enabled ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
                                        <span>{ipAccessSettings.internal_docs_enabled ? '已开启' : '已关闭'}</span>
                                    </button>
                                </div>
                                {ipAccessSettings.internal_docs_enabled && (
                                    <div className="form-group">
                                        <label>IP 白名单（CIDR 格式，每行一个）</label>
                                        <textarea
                                            placeholder="例如：192.168.1.0/24&#10;10.0.0.0/8"
                                            value={ipAccessSettings.internal_docs_whitelist?.join('\n') || ''}
                                            onChange={(e) => onIpWhitelistChange('internal_docs_whitelist', e.target.value)}
                                            rows={3}
                                        />
                                    </div>
                                )}
                            </div>

                            <div className="card-footer">
                                <button className="btn-primary full-width" onClick={onIpAccessSave} disabled={ipAccessSaving}>
                                    <Save size={16} />
                                    {ipAccessSaving ? '保存中...' : '保存 IP 配置'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 首页弹窗设置内容 */}
            {activeTab === 'popup' && (
                <div className="settings-tab-content">
                    <div className="settings-card">
                        <div className="section-header">
                            <Bell size={20} />
                            <h3>首页弹窗设置</h3>
                            <button
                                className={`toggle-switch ${popupSettings.enabled ? 'active' : ''}`}
                                onClick={() => onPopupChange('enabled', !popupSettings.enabled)}
                            >
                                {popupSettings.enabled ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
                                <span>{popupSettings.enabled ? '已开启' : '已关闭'}</span>
                            </button>
                        </div>
                        <div className="section-body">
                            <div className="form-group">
                                <label>弹窗标题</label>
                                <input
                                    type="text"
                                    placeholder="请输入弹窗标题..."
                                    value={popupSettings.title}
                                    onChange={(e) => onPopupChange('title', e.target.value)}
                                />
                            </div>
                            <div className="form-group">
                                <label>弹窗正文</label>
                                <textarea
                                    placeholder="请输入弹窗内容..."
                                    value={popupSettings.content}
                                    onChange={(e) => onPopupChange('content', e.target.value)}
                                    rows={4}
                                />
                            </div>
                            <div className="card-footer">
                                <button className="btn-primary full-width" onClick={onPopupSave} disabled={popupSaving}>
                                    <Save size={16} />
                                    {popupSaving ? '保存中...' : '保存设置'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

// ==================== 主组件 ====================
export default function Admin() {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('dashboard');
    const [laws, setLaws] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingLaw, setEditingLaw] = useState(null);
    const [editForm, setEditForm] = useState({});
    const [deleteConfirm, setDeleteConfirm] = useState(null);
    const [saving, setSaving] = useState(false);
    const [todayViews, setTodayViews] = useState(0);
    const [totalViews, setTotalViews] = useState(0);

    const [popupSettings, setPopupSettings] = useState({
        enabled: false,
        title: '',
        content: '',
    });
    const [popupSaving, setPopupSaving] = useState(false);

    // AI 配置状态
    const [aiSettings, setAiSettings] = useState({
        provider: 'deepseek',
        api_url: '',
        api_key: '',
        model_name: '',
        skip_ssl_verify: false,
    });
    const [aiPresets, setAiPresets] = useState({});
    const [aiSaving, setAiSaving] = useState(false);

    // IP 访问控制配置状态
    const [ipAccessSettings, setIpAccessSettings] = useState({
        ai_enabled: false,
        ai_whitelist: [],
        internal_docs_enabled: false,
        internal_docs_whitelist: [],
    });
    const [ipAccessSaving, setIpAccessSaving] = useState(false);

    // AI Token 用量统计
    const [tokenUsage, setTokenUsage] = useState({
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0,
        call_count: 0,
    });

    // 动态分类和层级选项
    const [categoryOptions, setCategoryOptions] = useState(DEFAULT_CATEGORY_OPTIONS);
    const [levelOptions, setLevelOptions] = useState(DEFAULT_LEVEL_OPTIONS);

    useEffect(() => {
        fetchLaws();
        fetchPopupSettings();
        fetchTodayViews();
        fetchTotalViews();
        fetchAiSettings();
        fetchIpAccessSettings();
        fetchTokenUsage();
        fetchCategoriesAndLevels();
    }, []);

    const fetchLaws = async () => {
        setLoading(true);
        try {
            const response = await getLawsList({ page: 1, page_size: 100 });
            setLaws(response.data || []);
        } catch (error) {
            message.error('加载法规列表失败');
        } finally {
            setLoading(false);
        }
    };

    const fetchCategoriesAndLevels = async () => {
        try {
            const [catRes, levelRes] = await Promise.all([
                getLawCategories(),
                getLawLevels()
            ]);
            if (catRes.success && catRes.data?.length > 0) {
                // 合并默认选项和API返回的选项，去重
                const merged = [...new Set([...DEFAULT_CATEGORY_OPTIONS, ...catRes.data])];
                setCategoryOptions(merged.filter(c => c));
            }
            if (levelRes.success && levelRes.data?.length > 0) {
                const merged = [...new Set([...DEFAULT_LEVEL_OPTIONS, ...levelRes.data])];
                setLevelOptions(merged.filter(l => l));
            }
        } catch (error) {
            console.error('加载分类/层级选项失败:', error);
        }
    };

    const fetchPopupSettings = async () => {
        try {
            const response = await getPopupSettings();
            setPopupSettings(response);
        } catch (error) {
            console.error('加载弹窗设置失败:', error);
        }
    };

    const fetchTodayViews = async () => {
        try {
            const response = await getTodayViews();
            if (response.success) {
                setTodayViews(response.data?.today_views || 0);
            }
        } catch (error) {
            console.error('加载今日浏览失败:', error);
        }
    };

    const fetchTotalViews = async () => {
        try {
            const response = await getTotalViews();
            if (response.success) {
                setTotalViews(response.data?.total_views || 0);
            }
        } catch (error) {
            console.error('Failed to load total views:', error);
        }
    };

    const handlePopupChange = (field, value) => {
        setPopupSettings(prev => ({ ...prev, [field]: value }));
    };

    const handleSavePopup = async () => {
        setPopupSaving(true);
        try {
            await updatePopupSettings(popupSettings);
            message.success('弹窗设置已保存');
        } catch (error) {
            message.error('保存失败');
        } finally {
            setPopupSaving(false);
        }
    };

    // AI 配置相关函数
    const fetchAiSettings = async () => {
        try {
            const [settingsRes, presetsRes] = await Promise.all([
                getAiSettings(),
                getAiPresets()
            ]);
            setAiSettings(settingsRes);
            setAiPresets(presetsRes);
        } catch (error) {
            console.error('加载 AI 配置失败:', error);
        }
    };

    const handleAiChange = (field, value) => {
        setAiSettings(prev => ({ ...prev, [field]: value }));
    };

    const handleAiPresetChange = (presetKey) => {
        const preset = aiPresets[presetKey];
        if (preset) {
            setAiSettings(prev => ({
                ...prev,
                provider: presetKey,
                api_url: preset.api_url,
                model_name: preset.model_name,
                skip_ssl_verify: preset.skip_ssl_verify,
            }));
        }
    };

    const handleSaveAi = async () => {
        if (!aiSettings.api_key) {
            message.warning('请输入 API Key');
            return;
        }
        setAiSaving(true);
        try {
            await updateAiSettings(aiSettings);
            message.success('AI 配置已保存');
        } catch (error) {
            message.error('保存失败');
        } finally {
            setAiSaving(false);
        }
    };

    // IP 访问控制相关函数
    const fetchIpAccessSettings = async () => {
        try {
            const settings = await getIpAccessSettings();
            setIpAccessSettings(settings);
        } catch (error) {
            console.error('加载 IP 访问控制配置失败:', error);
        }
    };

    // AI Token 用量统计
    const fetchTokenUsage = async () => {
        try {
            const data = await getAiTokenUsage();
            setTokenUsage(data);
        } catch (error) {
            console.error('加载 AI Token 用量失败:', error);
        }
    };

    const handleIpAccessChange = (field, value) => {
        setIpAccessSettings(prev => ({ ...prev, [field]: value }));
    };

    const handleIpWhitelistChange = (field, value) => {
        // 将逗号或换行分隔的字符串转换为数组
        const list = value.split(/[,\n]/).map(ip => ip.trim()).filter(ip => ip);
        setIpAccessSettings(prev => ({ ...prev, [field]: list }));
    };

    const handleSaveIpAccess = async () => {
        const hasAiWhitelist = ipAccessSettings.ai_whitelist && ipAccessSettings.ai_whitelist.length > 0;
        const hasInternalWhitelist = ipAccessSettings.internal_docs_whitelist && ipAccessSettings.internal_docs_whitelist.length > 0;
        if ((ipAccessSettings.ai_enabled && !hasAiWhitelist) || (ipAccessSettings.internal_docs_enabled && !hasInternalWhitelist)) {
            message.error('开启访问控制时必须配置 IP 白名单');
            return;
        }
        setIpAccessSaving(true);
        try {
            await updateIpAccessSettings(ipAccessSettings);
            message.success('IP 访问控制配置已保存');
        } catch (error) {
            message.error('保存失败');
        } finally {
            setIpAccessSaving(false);
        }
    };

    const openEditModal = (law) => {
        setEditingLaw(law);
        setEditForm({
            status: law.status || '现行有效',
            category: law.category || '',
            level: law.level || '',
            issue_org: law.issue_org || '',
            issue_date: law.issue_date || '',
            effect_date: law.effect_date || '',
            expire_date: law.expire_date || '',
        });
    };

    const handleEditChange = (field, value) => {
        setEditForm(prev => ({ ...prev, [field]: value }));
    };

    const handleSaveEdit = async () => {
        if (!editingLaw) return;
        setSaving(true);
        try {
            await updateLaw(editingLaw.law_id, editForm);
            message.success('保存成功');
            setEditingLaw(null);
            fetchLaws();
        } catch (error) {
            message.error('保存失败');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (lawId) => {
        try {
            await deleteLaw(lawId);
            message.success('删除成功');
            setDeleteConfirm(null);
            fetchLaws();
        } catch (error) {
            message.error('删除失败');
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('adminToken');
        message.success('已退出登录');
        navigate('/admin/login');
    };

    const TABS = [
        { id: 'dashboard', label: '仪表盘', icon: LayoutDashboard },
        { id: 'laws', label: '法规管理', icon: BookOpen },
        { id: 'settings', label: '系统设置', icon: Settings },
    ];

    if (loading) {
        return (
            <div className="admin-loading">
                <div className="spinner"></div>
                <p>加载中...</p>
            </div>
        );
    }

    return (
        <div className="admin-container">
            {/* Header */}
            <header className="admin-header">
                <div className="admin-header-left">
                    <button className="back-button" onClick={() => navigate('/')}>
                        <ChevronLeft size={20} />
                        返回首页
                    </button>
                    <div className="admin-title">
                        <Settings size={28} />
                        <h1>后台管理</h1>
                    </div>
                </div>
                <div className="admin-stats">
                    <button className="logout-button" onClick={handleLogout} title="退出登录">
                        <LogOut size={18} />
                        退出
                    </button>
                </div>
            </header>

            {/* 主布局：侧边栏 + 内容 */}
            <div className="admin-layout">
                {/* 侧边栏 */}
                <aside className="admin-sidebar">
                    {TABS.map(tab => (
                        <button
                            key={tab.id}
                            className={`sidebar-item ${activeTab === tab.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            <tab.icon size={20} />
                            <span>{tab.label}</span>
                        </button>
                    ))}
                </aside>

                {/* 内容区 */}
                <main className="admin-main">
                    {activeTab === 'dashboard' && <DashboardModule laws={laws} todayViews={todayViews} totalViews={totalViews} tokenUsage={tokenUsage} />}
                    {activeTab === 'laws' && (
                        <LawsModule
                            laws={laws}
                            onEdit={openEditModal}
                            onDelete={setDeleteConfirm}
                            onView={(id) => navigate(`/laws/${id}`)}
                        />
                    )}
                    {activeTab === 'settings' && (
                        <SettingsModule
                            popupSettings={popupSettings}
                            onPopupChange={handlePopupChange}
                            onPopupSave={handleSavePopup}
                            popupSaving={popupSaving}
                            aiSettings={aiSettings}
                            aiPresets={aiPresets}
                            onAiChange={handleAiChange}
                            onAiPresetChange={handleAiPresetChange}
                            onAiSave={handleSaveAi}
                            aiSaving={aiSaving}
                            ipAccessSettings={ipAccessSettings}
                            onIpAccessChange={handleIpAccessChange}
                            onIpWhitelistChange={handleIpWhitelistChange}
                            onIpAccessSave={handleSaveIpAccess}
                            ipAccessSaving={ipAccessSaving}
                        />
                    )}
                </main>
            </div>

            {/* 编辑弹窗 */}
            {editingLaw && (
                <div className="modal-overlay" onClick={() => setEditingLaw(null)}>
                    <div className="modal-content edit-modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>编辑法规信息</h3>
                            <button className="close-btn" onClick={() => setEditingLaw(null)}>
                                <X size={20} />
                            </button>
                        </div>
                        <div className="modal-body">
                            <div className="edit-law-title">{editingLaw.title}</div>
                            <div className="form-grid">
                                <div className="form-group">
                                    <label>效力状态</label>
                                    <select
                                        value={editForm.status}
                                        onChange={(e) => handleEditChange('status', e.target.value)}
                                    >
                                        {STATUS_OPTIONS.map(opt => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                                    <label>制定机关</label>
                                    <input
                                        type="text"
                                        placeholder="例如：公安部"
                                        value={editForm.issue_org}
                                        onChange={(e) => handleEditChange('issue_org', e.target.value)}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>法规分类</label>
                                    <select
                                        value={editForm.category}
                                        onChange={(e) => handleEditChange('category', e.target.value)}
                                    >
                                        <option value="">请选择</option>
                                        {categoryOptions.map(cat => (
                                            <option key={cat} value={cat}>{cat}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>效力层级</label>
                                    <select
                                        value={editForm.level}
                                        onChange={(e) => handleEditChange('level', e.target.value)}
                                    >
                                        <option value="">请选择</option>
                                        {levelOptions.map(lvl => (
                                            <option key={lvl} value={lvl}>{lvl}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>公布日期</label>
                                    <input
                                        type="date"
                                        value={editForm.issue_date}
                                        onChange={(e) => handleEditChange('issue_date', e.target.value)}
                                    />
                                </div>
                                <div className="form-group">
                                    <label>实施日期</label>
                                    <input
                                        type="date"
                                        value={editForm.effect_date}
                                        onChange={(e) => handleEditChange('effect_date', e.target.value)}
                                    />
                                </div>
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-cancel" onClick={() => setEditingLaw(null)}>
                                取消
                            </button>
                            <button className="btn-primary" onClick={handleSaveEdit} disabled={saving}>
                                <Save size={16} />
                                {saving ? '保存中...' : '保存修改'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* 删除确认弹窗 */}
            {deleteConfirm && (
                <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div className="modal-icon">
                            <AlertTriangle size={48} color="#ef4444" />
                        </div>
                        <h3>确认删除</h3>
                        <p>确定要删除 <strong>{deleteConfirm.title}</strong> 吗？</p>
                        <p className="warning-text">此操作将同时删除该法规的所有条文，且无法恢复！</p>
                        <div className="modal-actions">
                            <button className="btn-cancel" onClick={() => setDeleteConfirm(null)}>
                                取消
                            </button>
                            <button className="btn-danger" onClick={() => handleDelete(deleteConfirm.law_id)}>
                                确认删除
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
