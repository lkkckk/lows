import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { ArrowLeft, Search, FileText, Eye, FolderOpen } from 'lucide-react';
import { searchTranscripts } from '../services/api';
import '../styles/Transcript.css';

export default function TranscriptSearch() {
    const navigate = useNavigate();
    const [keyword, setKeyword] = useState('');
    const [typeFilter, setTypeFilter] = useState('');
    const [roleFilter, setRoleFilter] = useState('');
    const [caseTypeFilter, setCaseTypeFilter] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searched, setSearched] = useState(false);
    const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

    const doSearch = useCallback(async (page = 1) => {
        if (!keyword.trim()) {
            message.warning('请输入搜索关键词');
            return;
        }
        setLoading(true);
        setSearched(true);
        try {
            const params = {
                keyword: keyword.trim(),
                page,
                page_size: pagination.pageSize,
            };
            if (typeFilter) params.transcript_type = typeFilter;
            if (roleFilter) params.subject_role = roleFilter;
            if (caseTypeFilter) params.case_type = caseTypeFilter;

            const res = await searchTranscripts(params);
            if (res.success) {
                setResults(res.data || []);
                setPagination(prev => ({
                    ...prev,
                    current: page,
                    total: res.pagination?.total || 0,
                }));
            }
        } catch {
            message.error('搜索失败');
        } finally {
            setLoading(false);
        }
    }, [keyword, typeFilter, roleFilter, caseTypeFilter, pagination.pageSize]);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') doSearch(1);
    };

    const totalPages = Math.ceil(pagination.total / pagination.pageSize);

    return (
        <div>
            {/* Hero 搜索区 */}
            <div className="transcript-search-hero">
                <div className="container">
                    <button className="transcript-back" onClick={() => navigate('/cases')}>
                        <ArrowLeft size={16} /> 返回案件列表
                    </button>
                    <h1>笔录知识库检索</h1>
                    <div className="transcript-search-form">
                        <input
                            value={keyword}
                            onChange={e => setKeyword(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="输入关键词搜索历史笔录..."
                        />
                        <button onClick={() => doSearch(1)}>
                            <Search size={15} /> 搜索
                        </button>
                    </div>
                    <div className="transcript-search-filters">
                        <select className="filter-select" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
                            <option value="">全部笔录类型</option>
                            <option value="询问笔录">询问笔录</option>
                            <option value="讯问笔录">讯问笔录</option>
                            <option value="陈述笔录">陈述笔录</option>
                            <option value="辨认笔录">辨认笔录</option>
                        </select>
                        <select className="filter-select" value={roleFilter} onChange={e => setRoleFilter(e.target.value)}>
                            <option value="">全部角色</option>
                            <option value="嫌疑人">嫌疑人</option>
                            <option value="被害人">被害人</option>
                            <option value="证人">证人</option>
                            <option value="报案人">报案人</option>
                        </select>
                        <select className="filter-select" value={caseTypeFilter} onChange={e => setCaseTypeFilter(e.target.value)}>
                            <option value="">全部案件类型</option>
                            <option value="治安案件">治安案件</option>
                            <option value="刑事案件">刑事案件</option>
                            <option value="行政案件">行政案件</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* 搜索结果 */}
            <div className="transcript-search-main">
                {loading ? (
                    <div className="case-loading">
                        <div className="loading-spinner"><div className="spinner"></div></div>
                    </div>
                ) : searched && results.length === 0 ? (
                    <div className="case-empty">
                        <Search size={40} />
                        <p>未找到匹配的笔录</p>
                    </div>
                ) : results.length > 0 ? (
                    <>
                        <p style={{ color: '#64748b', fontSize: 14, marginBottom: 16 }}>
                            找到 {pagination.total} 条相关笔录
                        </p>
                        {results.map(r => (
                            <div key={r.transcript_id} className="search-result-card">
                                <div className="search-result-title">
                                    <FileText size={14} style={{ display: 'inline', marginRight: 6 }} />
                                    {r.title}
                                </div>
                                <div className="search-result-case">
                                    <FolderOpen size={12} style={{ display: 'inline', marginRight: 4 }} />
                                    {r.case_name} — {r.subject_name}（{r.subject_role}）| {r.type}
                                </div>
                                {r.match_snippet && (
                                    <div className="search-result-snippet">{r.match_snippet}</div>
                                )}
                                <div className="search-result-footer">
                                    <div className="result-laws">
                                        {(r.related_laws_display || []).map((l, i) => (
                                            <span key={i} className="transcript-law-tag">{l}</span>
                                        ))}
                                    </div>
                                    <div className="result-actions">
                                        <button onClick={() => navigate(`/cases/${r.case_id}/transcripts/${r.transcript_id}`)}>
                                            <Eye size={12} /> 查看笔录
                                        </button>
                                        <button onClick={() => navigate(`/cases/${r.case_id}`)}>
                                            <FolderOpen size={12} /> 查看案件
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                        {totalPages > 1 && (
                            <div className="case-pagination">
                                <button disabled={pagination.current <= 1}
                                    onClick={() => { doSearch(pagination.current - 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
                                    上一页
                                </button>
                                <span className="page-info">第 {pagination.current} / {totalPages} 页</span>
                                <button disabled={pagination.current >= totalPages}
                                    onClick={() => { doSearch(pagination.current + 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
                                    下一页
                                </button>
                            </div>
                        )}
                    </>
                ) : !searched ? (
                    <div className="case-empty">
                        <Search size={40} />
                        <p>输入关键词搜索历史笔录</p>
                    </div>
                ) : null}
            </div>
        </div>
    );
}
