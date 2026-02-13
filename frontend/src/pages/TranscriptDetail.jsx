import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { message } from 'antd';
import { ArrowLeft, RefreshCw, FileText, Users, Clock, MapPin, AlertTriangle, Scale, ClipboardCheck, ChevronDown, ChevronRight } from 'lucide-react';
import { getTranscriptDetail, triggerAnalysis } from '../services/api';
import '../styles/Transcript.css';

export default function TranscriptDetail() {
    const { caseId, transcriptId } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        try {
            const res = await getTranscriptDetail(caseId, transcriptId);
            if (res.success) {
                setData(res.data);
            }
        } catch {
            message.error('加载笔录详情失败');
        } finally {
            setLoading(false);
        }
    }, [caseId, transcriptId]);

    useEffect(() => {
        fetchData();
        // 分析中时轮询
        const interval = setInterval(async () => {
            if (data?.analysis_status === 'analyzing') {
                fetchData();
            }
        }, 5000);
        return () => clearInterval(interval);
    }, [fetchData, data?.analysis_status]);

    const handleReanalyze = async () => {
        try {
            await triggerAnalysis(caseId, transcriptId);
            message.success('分析任务已提交');
            setData(prev => prev ? { ...prev, analysis_status: 'analyzing' } : prev);
        } catch {
            message.error('触发分析失败');
        }
    };

    if (loading) {
        return <div className="case-loading" style={{ paddingTop: 100 }}><div className="loading-spinner"><div className="spinner"></div></div></div>;
    }

    if (!data) {
        return <div className="case-empty" style={{ paddingTop: 100 }}><p>笔录不存在</p></div>;
    }

    const analysis = data.analysis;
    const status = data.analysis_status;

    return (
        <div>
            {/* 头部 */}
            <div className="transcript-detail-header">
                <div className="container">
                    <button className="transcript-back" onClick={() => navigate(`/cases/${caseId}`)}>
                        <ArrowLeft size={16} /> 返回案件
                    </button>
                    <div className="transcript-title-row">
                        <div>
                            <h1>{data.title}</h1>
                            <div className="transcript-title-meta">
                                被询问人：{data.subject_name}（{data.subject_role}）| {data.type}
                            </div>
                        </div>
                        <div className="transcript-header-actions">
                            <button onClick={handleReanalyze}>
                                <RefreshCw size={14} /> 重新分析
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* 左右分栏 */}
            <div className="transcript-split">
                {/* 左栏 - 原文 */}
                <div className="transcript-left">
                    <div className="transcript-panel">
                        <div className="transcript-panel-header">
                            <FileText size={16} /> 笔录原文
                        </div>
                        <div className="transcript-content-body">
                            {data.content || '（无内容）'}
                        </div>
                    </div>
                </div>

                {/* 右栏 - 分析结果 */}
                <div className="transcript-right">
                    <div className="transcript-panel">
                        <div className="transcript-panel-header">
                            <Scale size={16} /> AI 分析结果
                        </div>

                        {status === 'analyzing' && (
                            <div className="analysis-loading">
                                <div className="spinner"></div>
                                <p>AI 正在分析笔录内容，请稍候...</p>
                            </div>
                        )}

                        {status === 'pending' && (
                            <div className="analysis-loading">
                                <Clock size={32} style={{ opacity: 0.4 }} />
                                <p>尚未分析，点击「重新分析」开始</p>
                            </div>
                        )}

                        {status === 'failed' && (
                            <div className="analysis-error">
                                <AlertTriangle size={32} />
                                <p>分析失败</p>
                                <button onClick={handleReanalyze}>重试</button>
                            </div>
                        )}

                        {status === 'analyzed' && analysis && (
                            <div className="analysis-body">
                                <AnalysisContent analysis={analysis} />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}


/* ==================== 分析结果展示组件 ==================== */
function AnalysisContent({ analysis }) {
    return (
        <>
            {/* 摘要 */}
            {analysis.summary && (
                <CollapsibleSection title="分析摘要" icon={<FileText size={14} />} defaultOpen>
                    <div className="analysis-summary">{analysis.summary}</div>
                </CollapsibleSection>
            )}

            {/* 涉及人员 */}
            {analysis.persons?.length > 0 && (
                <CollapsibleSection title="涉及人员" icon={<Users size={14} />} defaultOpen>
                    {analysis.persons.map((p, i) => (
                        <div key={i} className="person-card">
                            <span className="person-name">{p.name}</span>
                            <span className="person-role">{p.role}</span>
                            {(p.id_number || p.contact || p.description) && (
                                <div className="person-detail">
                                    {p.id_number && <div>身份证：{p.id_number}</div>}
                                    {p.contact && <div>联系方式：{p.contact}</div>}
                                    {p.description && <div>{p.description}</div>}
                                </div>
                            )}
                        </div>
                    ))}
                </CollapsibleSection>
            )}

            {/* 时间线 */}
            {analysis.timeline?.length > 0 && (
                <CollapsibleSection title="时间线" icon={<Clock size={14} />} defaultOpen>
                    {analysis.timeline.map((t, i) => (
                        <div key={i} className="timeline-item">
                            <span className="timeline-time">{t.time}</span>
                            <span className="timeline-event">{t.event}</span>
                        </div>
                    ))}
                </CollapsibleSection>
            )}

            {/* 地点 */}
            {analysis.locations?.length > 0 && (
                <CollapsibleSection title="地点" icon={<MapPin size={14} />}>
                    <div className="location-tags">
                        {analysis.locations.map((l, i) => (
                            <span key={i} className="location-tag">
                                {l.name}
                                {l.type && <span className="loc-type">（{l.type}）</span>}
                            </span>
                        ))}
                    </div>
                </CollapsibleSection>
            )}

            {/* 关键事实 */}
            {analysis.key_facts?.length > 0 && (
                <CollapsibleSection title="关键事实" icon={<AlertTriangle size={14} />} defaultOpen>
                    {analysis.key_facts.map((f, i) => (
                        <div key={i} className="fact-item">
                            {f.category && <div className="fact-category">{f.category}</div>}
                            <div className="fact-desc">{f.description}</div>
                            {f.source && <div className="fact-source">原文：{f.source}</div>}
                        </div>
                    ))}
                </CollapsibleSection>
            )}

            {/* 涉案物品/金额 */}
            {analysis.items_amounts?.length > 0 && (
                <CollapsibleSection title="涉案物品/金额" icon={<FileText size={14} />}>
                    {analysis.items_amounts.map((it, i) => (
                        <div key={i} className="item-amount">
                            {it.name}{it.quantity ? ` × ${it.quantity}` : ''}{it.value ? ` — 价值 ${it.value}` : ''}
                        </div>
                    ))}
                </CollapsibleSection>
            )}

            {/* 关联法条 */}
            {analysis.related_laws?.length > 0 && (
                <CollapsibleSection title="关联法条" icon={<Scale size={14} />} defaultOpen>
                    {analysis.related_laws.map((l, i) => {
                        const linkQuery = l.law_title && l.article_display
                            ? `《${l.law_title}》${l.article_display}`
                            : l.law_title || '';
                        return (
                            <div key={i} className="law-item">
                                <div className="law-item-title">
                                    {linkQuery ? (
                                        <Link to={`/search?q=${encodeURIComponent(linkQuery)}`}>
                                            《{l.law_title}》{l.article_display}
                                        </Link>
                                    ) : (
                                        <span>（未知法条）</span>
                                    )}
                                    <span className={`law-confidence confidence-${l.confidence || 'medium'}`}>
                                        {l.confidence === 'high' ? '高' : l.confidence === 'low' ? '低' : '中'}
                                    </span>
                                </div>
                                {l.relevance && <div className="law-item-relevance">{l.relevance}</div>}
                            </div>
                        );
                    })}
                </CollapsibleSection>
            )}

            {/* 规范性检查 */}
            {analysis.compliance_issues?.length > 0 && (
                <CollapsibleSection title="规范性检查" icon={<ClipboardCheck size={14} />} defaultOpen>
                    {analysis.compliance_issues.map((c, i) => {
                        const icon = c.status === 'pass' ? '✓' : c.status === 'warning' ? '⚠' : '✗';
                        const cls = c.status === 'pass' ? 'compliance-pass' : c.status === 'warning' ? 'compliance-warning' : 'compliance-fail';
                        return (
                            <div key={i} className="compliance-item">
                                <span className={`compliance-icon ${cls}`}>{icon}</span>
                                <span>{c.item}{c.detail ? ` — ${c.detail}` : ''}</span>
                            </div>
                        );
                    })}
                </CollapsibleSection>
            )}
        </>
    );
}


/* ==================== 可折叠区块 ==================== */
function CollapsibleSection({ title, icon, children, defaultOpen = false }) {
    const [open, setOpen] = useState(defaultOpen);

    return (
        <div className="analysis-section">
            <div className="analysis-section-title" onClick={() => setOpen(!open)}>
                {icon} {title}
                <span style={{ marginLeft: 'auto' }}>
                    {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </span>
            </div>
            {open && children}
        </div>
    );
}
