import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { FolderOpen, Plus, Search, Archive, Clock, FileText } from 'lucide-react';
import { getCasesList, archiveCase } from '../services/api';
import '../styles/Case.css';

export default function CaseList() {
    const navigate = useNavigate();
    const [cases, setCases] = useState([]);
    const [loading, setLoading] = useState(false);
    const [keyword, setKeyword] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [typeFilter, setTypeFilter] = useState('');
    const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

    const fetchCases = useCallback(async () => {
        setLoading(true);
        try {
            const params = {
                page: pagination.current,
                page_size: pagination.pageSize,
            };
            if (keyword) params.keyword = keyword;
            if (statusFilter) params.status = statusFilter;
            if (typeFilter) params.case_type = typeFilter;

            const res = await getCasesList(params);
            if (res.success) {
                setCases(res.data || []);
                setPagination(prev => ({
                    ...prev,
                    total: res.pagination?.total || 0,
                }));
            }
        } catch (error) {
            message.error('加载案件列表失败');
        } finally {
            setLoading(false);
        }
    }, [pagination.current, keyword, statusFilter, typeFilter]);

    useEffect(() => {
        fetchCases();
    }, [fetchCases]);

    const handleSearch = (e) => {
        if (e.key === 'Enter' || e.type === 'click') {
            setPagination(prev => ({ ...prev, current: 1 }));
        }
    };

    const handleArchive = async (e, caseId, currentStatus) => {
        e.stopPropagation();
        const isArchive = currentStatus !== 'archived';
        try {
            await archiveCase(caseId, isArchive);
            message.success(isArchive ? '已归档' : '已取消归档');
            fetchCases();
        } catch {
            message.error('操作失败');
        }
    };

    const totalPages = Math.ceil(pagination.total / pagination.pageSize);

    return (
        <div>
            {/* Hero */}
            <div className="case-hero">
                <div className="container">
                    <div className="case-hero-header">
                        <h1 className="case-hero-title">笔录分析</h1>
                        <div className="case-hero-actions">
                            <button className="btn-secondary" onClick={() => navigate('/cases/search')}>
                                <Search size={15} /> 搜索笔录知识库
                            </button>
                            <button className="btn-primary" onClick={() => navigate('/cases/create')}>
                                <Plus size={15} /> 新建案件
                            </button>
                        </div>
                    </div>
                    <div className="case-filters">
                        <div className="case-search-wrapper">
                            <Search size={14} className="search-icon" />
                            <input
                                className="case-search-input"
                                placeholder="搜索案件名称 / 编号 / 标签..."
                                value={keyword}
                                onChange={e => setKeyword(e.target.value)}
                                onKeyDown={handleSearch}
                            />
                        </div>
                        <select className="filter-select" value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPagination(p => ({ ...p, current: 1 })); }}>
                            <option value="">全部类型</option>
                            <option value="治安案件">治安案件</option>
                            <option value="刑事案件">刑事案件</option>
                            <option value="行政案件">行政案件</option>
                        </select>
                        <select className="filter-select" value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPagination(p => ({ ...p, current: 1 })); }}>
                            <option value="">全部状态</option>
                            <option value="active">进行中</option>
                            <option value="archived">已归档</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* 列表 */}
            <div className="case-main">
                {loading ? (
                    <div className="case-loading">
                        <div className="loading-spinner"><div className="spinner"></div></div>
                    </div>
                ) : cases.length > 0 ? (
                    <>
                        {cases.map(c => (
                            <div
                                key={c.case_id}
                                className={`case-card ${c.status === 'archived' ? 'archived' : ''}`}
                                onClick={() => navigate(`/cases/${c.case_id}`)}
                            >
                                <div className="case-card-header">
                                    <div className="case-card-title">
                                        <FolderOpen size={18} />
                                        {c.case_name}
                                        {c.status === 'archived' && (
                                            <span className="case-card-badge badge-archived">已归档</span>
                                        )}
                                    </div>
                                </div>
                                <div className="case-card-meta">
                                    {c.case_number && <span>编号：{c.case_number}</span>}
                                    <span>类型：{c.case_type}</span>
                                    <span><FileText size={13} /> 笔录：{c.transcript_count || 0} 份</span>
                                    <span><Clock size={13} /> {c.created_at ? new Date(c.created_at).toLocaleDateString() : ''}</span>
                                </div>
                                {c.tags && c.tags.length > 0 && (
                                    <div className="case-card-tags">
                                        {c.tags.map((tag, i) => (
                                            <span key={i} className="case-tag">{tag}</span>
                                        ))}
                                    </div>
                                )}
                                <div className="case-card-actions">
                                    <button onClick={e => { e.stopPropagation(); navigate(`/cases/${c.case_id}`); }}>
                                        查看详情
                                    </button>
                                    <button onClick={e => handleArchive(e, c.case_id, c.status)}>
                                        <Archive size={13} /> {c.status === 'archived' ? '取消归档' : '归档'}
                                    </button>
                                </div>
                            </div>
                        ))}
                        {totalPages > 1 && (
                            <div className="case-pagination">
                                <button disabled={pagination.current <= 1}
                                    onClick={() => { setPagination(p => ({ ...p, current: p.current - 1 })); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
                                    上一页
                                </button>
                                <span className="page-info">第 {pagination.current} / {totalPages} 页</span>
                                <button disabled={pagination.current >= totalPages}
                                    onClick={() => { setPagination(p => ({ ...p, current: p.current + 1 })); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
                                    下一页
                                </button>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="case-empty">
                        <FolderOpen size={48} />
                        <p>暂无案件，点击「新建案件」开始</p>
                    </div>
                )}
            </div>
        </div>
    );
}
