/**
 * 后台管理页面 - 模块化重构版
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import {
    Settings, Trash2, Edit3, Eye, AlertTriangle, ChevronLeft, X, Save,
    Bell, ToggleLeft, ToggleRight, LogOut, LayoutDashboard, BookOpen,
    PieChart, TrendingUp, FileText
} from 'lucide-react';
import { getLawsList, updateLaw, deleteLaw, getLawCategories, getLawLevels, getPopupSettings, updatePopupSettings, getTodayViews } from '../services/api';
import '../styles/Admin.css';

const STATUS_OPTIONS = [
    { value: '现行有效', label: '现行有效', color: '#10b981' },
    { value: '已废止', label: '已废止', color: '#ef4444' },
    { value: '尚未生效', label: '尚未生效', color: '#f59e0b' },
    { value: '已修订', label: '已修订', color: '#6b7280' },
];

const CATEGORY_OPTIONS = ['刑事法律', '行政法律', '民事法律', '程序规定', '司法解释', '其他'];
const LEVEL_OPTIONS = ['宪法', '法律', '行政法规', '地方性法规', '部门规章', '司法解释', '其他'];

// ==================== 仪表盘模块 ====================
const DashboardModule = ({ laws, todayViews }) => {
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
                <div className="stat-card warning">
                    <div className="stat-icon"><TrendingUp size={28} /></div>
                    <div className="stat-info">
                        <span className="stat-value">{todayViews}</span>
                        <span className="stat-label">今日浏览</span>
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
const SettingsModule = ({ popupSettings, onChange, onSave, saving }) => (
    <div className="settings-module">
        <div className="settings-section">
            <div className="section-header">
                <Bell size={20} />
                <h3>首页弹窗设置</h3>
                <button
                    className={`toggle-switch ${popupSettings.enabled ? 'active' : ''}`}
                    onClick={() => onChange('enabled', !popupSettings.enabled)}
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
                        onChange={(e) => onChange('title', e.target.value)}
                    />
                </div>
                <div className="form-group">
                    <label>弹窗正文</label>
                    <textarea
                        placeholder="请输入弹窗内容..."
                        value={popupSettings.content}
                        onChange={(e) => onChange('content', e.target.value)}
                        rows={4}
                    />
                </div>
                <button className="btn-primary" onClick={onSave} disabled={saving}>
                    <Save size={16} />
                    {saving ? '保存中...' : '保存设置'}
                </button>
            </div>
        </div>
    </div>
);

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

    const [popupSettings, setPopupSettings] = useState({
        enabled: false,
        title: '',
        content: '',
    });
    const [popupSaving, setPopupSaving] = useState(false);

    useEffect(() => {
        fetchLaws();
        fetchPopupSettings();
        fetchTodayViews();
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
                    {activeTab === 'dashboard' && <DashboardModule laws={laws} todayViews={todayViews} />}
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
                            onChange={handlePopupChange}
                            onSave={handleSavePopup}
                            saving={popupSaving}
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
                                        {CATEGORY_OPTIONS.map(cat => (
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
                                        {LEVEL_OPTIONS.map(lvl => (
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
