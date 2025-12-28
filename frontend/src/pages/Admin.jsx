/**
 * 后台管理页面 - 法规管理
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { Settings, Trash2, Edit3, Eye, AlertTriangle, ChevronLeft, X, Save, Bell, ToggleLeft, ToggleRight } from 'lucide-react';
import { getLawsList, updateLaw, deleteLaw, getLawCategories, getLawLevels, getPopupSettings, updatePopupSettings } from '../services/api';
import '../styles/Admin.css';

const STATUS_OPTIONS = [
    { value: '现行有效', label: '现行有效', color: '#10b981' },
    { value: '已失效', label: '已失效', color: '#ef4444' },
    { value: '尚未生效', label: '尚未生效', color: '#f59e0b' },
    { value: '已修订', label: '已修订', color: '#6b7280' },
];

const CATEGORY_OPTIONS = ['刑事法律', '行政法律', '程序规定'];
const LEVEL_OPTIONS = ['宪法', '法律', '行政法规', '地方性法规', '部门规章', '司法解释', '其他'];

export default function Admin() {
    const navigate = useNavigate();
    const [laws, setLaws] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingLaw, setEditingLaw] = useState(null);
    const [editForm, setEditForm] = useState({});
    const [deleteConfirm, setDeleteConfirm] = useState(null);
    const [saving, setSaving] = useState(false);

    // 首页弹窗配置
    const [popupSettings, setPopupSettings] = useState({
        enabled: false,
        title: '',
        content: '',
    });
    const [popupSaving, setPopupSaving] = useState(false);

    useEffect(() => {
        fetchLaws();
        fetchPopupSettings();
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

    const getStatusColor = (status) => {
        const option = STATUS_OPTIONS.find(o => o.value === status);
        return option ? option.color : '#6b7280';
    };

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
                    <span className="stat-item">
                        共 <strong>{laws.length}</strong> 部法规
                    </span>
                </div>
            </header>

            {/* 首页弹窗配置 */}
            <div className="popup-config-card">
                <div className="popup-config-header">
                    <Bell size={20} />
                    <h3>首页弹窗设置</h3>
                    <button
                        className={`toggle-switch ${popupSettings.enabled ? 'active' : ''}`}
                        onClick={() => handlePopupChange('enabled', !popupSettings.enabled)}
                    >
                        {popupSettings.enabled ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
                        <span>{popupSettings.enabled ? '已开启' : '已关闭'}</span>
                    </button>
                </div>
                <div className="popup-config-body">
                    <div className="form-group">
                        <label>弹窗标题</label>
                        <input
                            type="text"
                            placeholder="请输入弹窗标题..."
                            value={popupSettings.title}
                            onChange={(e) => handlePopupChange('title', e.target.value)}
                        />
                    </div>
                    <div className="form-group">
                        <label>弹窗正文</label>
                        <textarea
                            placeholder="请输入弹窗内容..."
                            value={popupSettings.content}
                            onChange={(e) => handlePopupChange('content', e.target.value)}
                            rows={4}
                        />
                    </div>
                    <button className="btn-primary" onClick={handleSavePopup} disabled={popupSaving}>
                        <Save size={16} />
                        {popupSaving ? '保存中...' : '保存设置'}
                    </button>
                </div>
            </div>

            {/* 法规列表 */}
            <div className="admin-content">
                <table className="admin-table">
                    <thead>
                        <tr>
                            <th style={{ width: '30%' }}>法规名称</th>
                            <th style={{ width: '10%' }}>制定机关</th>
                            <th style={{ width: '10%' }}>分类</th>
                            <th style={{ width: '10%' }}>层级</th>
                            <th style={{ width: '10%' }}>状态</th>
                            <th style={{ width: '10%' }}>实施日期</th>
                            <th style={{ width: '10%' }}>失效日期</th>
                            <th style={{ width: '10%' }}>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        {laws.map((law) => (
                            <tr key={law.law_id}>
                                <td className="law-title-cell">
                                    <span className="law-title" onClick={() => navigate(`/laws/${law.law_id}`)}>
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
                                <td>{law.expire_date || '-'}</td>
                                <td className="actions-cell">
                                    <button
                                        className="action-btn view-btn"
                                        onClick={() => navigate(`/laws/${law.law_id}`)}
                                        title="查看"
                                    >
                                        <Eye size={16} />
                                    </button>
                                    <button
                                        className="action-btn edit-btn"
                                        onClick={() => openEditModal(law)}
                                        title="编辑"
                                    >
                                        <Edit3 size={16} />
                                    </button>
                                    <button
                                        className="action-btn delete-btn"
                                        onClick={() => setDeleteConfirm(law)}
                                        title="删除"
                                    >
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

                                <div className="form-group" style={{ gridColumn: 'span 2' }}>
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
