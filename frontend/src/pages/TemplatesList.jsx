import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { FileText, Plus, Edit, Trash2, ChevronRight } from 'lucide-react';
import { getTemplatesList, deleteTemplate } from '../services/api';

export default function TemplatesList() {
    const navigate = useNavigate();
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(false);
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 20,
        total: 0,
    });

    const fetchTemplates = async () => {
        setLoading(true);
        try {
            const response = await getTemplatesList({
                page: pagination.current,
                page_size: pagination.pageSize,
            });
            setTemplates(response.data || []);
            setPagination(prev => ({ ...prev, total: response.pagination?.total || 0 }));
        } catch (error) {
            message.error('加载模板失败');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTemplates();
    }, [pagination.current]);

    const handleDelete = async (template) => {
        if (!window.confirm(`确定删除模板 "${template.name}" 吗？`)) return;
        try {
            await deleteTemplate(template.template_id);
            message.success('删除成功');
            fetchTemplates();
        } catch (error) {
            message.error('删除失败');
        }
    };

    return (
        <div style={{ paddingBottom: '3rem' }}>
            <section className="hero-section" style={{ paddingBottom: '5rem' }}>
                <div className="container" style={{ textAlign: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', marginBottom: '1.5rem' }}>
                        <FileText size={32} color="#a855f7" />
                        <h2 className="hero-title" style={{ margin: 0 }}>法律文书生成</h2>
                    </div>
                    <p style={{ color: '#94a3b8', marginBottom: '2rem' }}>选择文书模板，填写要素，自动生成规范法律文书</p>
                    <button
                        className="search-button"
                        style={{ position: 'static', transform: 'none', padding: '0.75rem 2rem', fontSize: '1rem', borderRadius: '12px' }}
                        onClick={() => message.info('新建功能开发中')}
                    >
                        <Plus size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                        新建模板
                    </button>
                </div>
            </section>

            <div className="main-content" style={{ marginTop: '-3rem' }}>
                <div className="content-card" style={{ display: 'block', padding: '2rem' }}>
                    <header className="section-header" style={{ marginBottom: '2rem' }}>
                        <h3 className="section-title">模板列表 <span className="section-count">({pagination.total})</span></h3>
                    </header>

                    {loading ? (
                        <div className="loading-spinner"><div className="spinner"></div></div>
                    ) : templates.length > 0 ? (
                        <>
                            <div className="card-grid">
                                {templates.map(template => (
                                    <div key={template.template_id} className="law-card" style={{ borderLeft: '4px solid #a855f7' }}>
                                        <div className="card-header">
                                            <span className="tag" style={{ background: '#f3e8ff', color: '#7e22ce' }}>{template.category || '未分类'}</span>
                                            <div style={{ display: 'flex', gap: '8px' }}>
                                                <button className="star-button" style={{ color: '#94a3b8' }} onClick={() => navigate(`/templates/${template.template_id}`)}><Edit size={16} /></button>
                                                <button className="star-button" style={{ color: '#f87171' }} onClick={() => handleDelete(template)}><Trash2 size={16} /></button>
                                            </div>
                                        </div>
                                        <h3 className="card-title" onClick={() => navigate(`/templates/${template.template_id}`)}>{template.name}</h3>
                                        <p className="card-description">包含 {template.fields?.length || 0} 个表单填写项</p>
                                        <div className="card-footer">
                                            <span>创建时间: {new Date(template.created_at).toLocaleDateString()}</span>
                                            <div className="footer-action" onClick={() => navigate(`/templates/${template.template_id}`)}>使用模板 <ChevronRight size={14} /></div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    ) : (
                        <div className="empty-state">
                            <FileText size={48} className="empty-icon" />
                            <p>暂无文书模板</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
