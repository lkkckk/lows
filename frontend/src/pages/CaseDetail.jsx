import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { ArrowLeft, Plus, Upload, FileText, RefreshCw, Trash2, Eye, Clock, CheckCircle, AlertCircle, Loader, GitCompareArrows, AlertTriangle, Activity, Package, FileSearch, Edit3 } from 'lucide-react';
import { getCaseDetail, createTranscript, uploadTranscript, triggerAnalysis, deleteTranscript, getAnalysisStatus, triggerCrossAnalysis, getCrossAnalysis, updateCase, deleteCase } from '../services/api';
import '../styles/Transcript.css';

export default function CaseDetail() {
    const { caseId } = useParams();
    const navigate = useNavigate();
    const [caseData, setCaseData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showTextModal, setShowTextModal] = useState(false);
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [crossAnalysis, setCrossAnalysis] = useState(null);
    const [crossLoading, setCrossLoading] = useState(false);
    const pollingRef = useRef(null);
    const crossPollingRef = useRef(null);

    const fetchDetail = useCallback(async () => {
        try {
            const res = await getCaseDetail(caseId);
            if (res.success) {
                setCaseData(res.data);
            }
        } catch {
            message.error('加载案件详情失败');
        } finally {
            setLoading(false);
        }
    }, [caseId]);

    const fetchCrossAnalysis = useCallback(async () => {
        try {
            const res = await getCrossAnalysis(caseId);
            if (res.success) {
                setCrossAnalysis(res.data);
            }
        } catch { /* ignore */ }
    }, [caseId]);

    useEffect(() => {
        fetchDetail();
        fetchCrossAnalysis();
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
            if (crossPollingRef.current) clearInterval(crossPollingRef.current);
        };
    }, [fetchDetail, fetchCrossAnalysis]);

    // 轮询分析中的笔录状态
    useEffect(() => {
        if (!caseData) return;
        const analyzing = (caseData.transcripts || []).filter(t => t.analysis_status === 'analyzing');
        if (analyzing.length > 0) {
            pollingRef.current = setInterval(async () => {
                let anyChanged = false;
                for (const t of analyzing) {
                    try {
                        const res = await getAnalysisStatus(caseId, t.transcript_id);
                        if (res.success && res.data.analysis_status !== 'analyzing') {
                            anyChanged = true;
                        }
                    } catch { /* ignore */ }
                }
                if (anyChanged) {
                    fetchDetail();
                }
            }, 5000);
        }
        return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
    }, [caseData, caseId, fetchDetail]);

    // 轮询交叉分析状态
    useEffect(() => {
        if (crossAnalysis && crossAnalysis.analysis_status === 'analyzing') {
            crossPollingRef.current = setInterval(async () => {
                try {
                    const res = await getCrossAnalysis(caseId);
                    if (res.success && res.data && res.data.analysis_status !== 'analyzing') {
                        setCrossAnalysis(res.data);
                        clearInterval(crossPollingRef.current);
                    }
                } catch { /* ignore */ }
            }, 5000);
        }
        return () => { if (crossPollingRef.current) clearInterval(crossPollingRef.current); };
    }, [crossAnalysis, caseId]);

    const handleCrossAnalyze = async () => {
        setCrossLoading(true);
        try {
            const res = await triggerCrossAnalysis(caseId);
            if (res.success) {
                message.success('交叉分析任务已提交');
                setCrossAnalysis({ analysis_status: 'analyzing' });
            } else {
                message.error(res.error || '触发失败');
            }
        } catch (err) {
            message.error(err?.response?.data?.detail || '触发交叉分析失败');
        } finally {
            setCrossLoading(false);
        }
    };

    const handleDeleteCase = async () => {
        if (!window.confirm('确定删除该案件及所有关联笔录？此操作不可撤销。')) return;
        try {
            await deleteCase(caseId);
            message.success('案件已删除');
            navigate('/cases');
        } catch (err) {
            message.error(err?.response?.data?.detail || '删除案件失败');
        }
    };

    const handleReanalyze = async (e, transcriptId) => {
        e.stopPropagation();
        try {
            await triggerAnalysis(caseId, transcriptId);
            message.success('分析任务已提交');
            fetchDetail();
        } catch {
            message.error('触发分析失败');
        }
    };

    const handleDelete = async (e, transcriptId) => {
        e.stopPropagation();
        if (!window.confirm('确定删除该笔录？')) return;
        try {
            await deleteTranscript(caseId, transcriptId);
            message.success('已删除');
            fetchDetail();
        } catch {
            message.error('删除失败');
        }
    };

    const getStatusBadge = (status) => {
        const map = {
            pending: { label: '待分析', cls: 'status-pending', icon: <Clock size={12} /> },
            analyzing: { label: '分析中...', cls: 'status-analyzing', icon: <Loader size={12} /> },
            analyzed: { label: '已分析', cls: 'status-analyzed', icon: <CheckCircle size={12} /> },
            failed: { label: '分析失败', cls: 'status-failed', icon: <AlertCircle size={12} /> },
        };
        const info = map[status] || map.pending;
        return <span className={`status-badge ${info.cls}`}>{info.icon} {info.label}</span>;
    };

    if (loading) {
        return <div className="case-loading" style={{ paddingTop: 100 }}><div className="loading-spinner"><div className="spinner"></div></div></div>;
    }

    if (!caseData) {
        return <div className="case-empty" style={{ paddingTop: 100 }}><p>案件不存在</p></div>;
    }

    const transcripts = caseData.transcripts || [];

    return (
        <div>
            {/* Hero */}
            <div className="case-detail-hero">
                <div className="container">
                    <button className="transcript-back" onClick={() => navigate('/cases')}>
                        <ArrowLeft size={16} /> 返回案件列表
                    </button>
                    <div className="case-detail-title-row">
                        <h1>{caseData.case_name}</h1>
                        <div className="case-detail-title-actions">
                            <button className="btn-icon" title="编辑案件" onClick={() => setShowEditModal(true)}>
                                <Edit3 size={16} />
                            </button>
                            <button className="btn-icon btn-danger" title="删除案件" onClick={handleDeleteCase}>
                                <Trash2 size={16} />
                            </button>
                        </div>
                    </div>
                    <div className="case-detail-meta">
                        {caseData.case_number && <span>编号：{caseData.case_number}</span>}
                        <span>{caseData.case_type}</span>
                        <span>{caseData.created_at ? new Date(caseData.created_at).toLocaleDateString() : ''}</span>
                    </div>
                    {caseData.description && <div className="case-detail-desc">{caseData.description}</div>}
                    {caseData.tags?.length > 0 && (
                        <div className="case-detail-tags">
                            {caseData.tags.map((t, i) => <span key={i}>{t}</span>)}
                        </div>
                    )}
                </div>
            </div>

            {/* 笔录列表 */}
            <div className="case-detail-main">
                <div className="detail-section">
                    <div className="detail-section-header">
                        <span className="detail-section-title">笔录列表（{transcripts.length} 份）</span>
                        <div className="detail-section-actions">
                            <button onClick={() => setShowTextModal(true)}>
                                <Plus size={14} /> 粘贴文本添加
                            </button>
                            <button onClick={() => setShowUploadModal(true)}>
                                <Upload size={14} /> 上传文件
                            </button>
                        </div>
                    </div>

                    {transcripts.length === 0 ? (
                        <div className="case-empty">
                            <FileText size={40} />
                            <p>暂无笔录，点击上方按钮添加</p>
                        </div>
                    ) : (
                        transcripts.map(t => (
                            <div key={t.transcript_id} className="transcript-card"
                                onClick={() => navigate(`/cases/${caseId}/transcripts/${t.transcript_id}`)}>
                                <div className="transcript-card-header">
                                    <span className="transcript-card-title">
                                        <FileText size={15} /> {t.title}
                                    </span>
                                    {getStatusBadge(t.analysis_status)}
                                </div>
                                <div className="transcript-card-meta">
                                    被询问人：{t.subject_name}（{t.subject_role}）| {t.type}
                                </div>
                                {t.summary && (
                                    <div className="transcript-card-summary">摘要：{t.summary}</div>
                                )}
                                {t.related_laws_display?.length > 0 && (
                                    <div className="transcript-card-laws">
                                        {t.related_laws_display.map((l, i) => (
                                            <span key={i} className="transcript-law-tag">{l}</span>
                                        ))}
                                    </div>
                                )}
                                <div className="transcript-card-actions">
                                    <button onClick={e => { e.stopPropagation(); navigate(`/cases/${caseId}/transcripts/${t.transcript_id}`); }}>
                                        <Eye size={12} /> 查看详情
                                    </button>
                                    {(t.analysis_status === 'analyzed' || t.analysis_status === 'failed') && (
                                        <button onClick={e => handleReanalyze(e, t.transcript_id)}>
                                            <RefreshCw size={12} /> 重新分析
                                        </button>
                                    )}
                                    <button onClick={e => handleDelete(e, t.transcript_id)}>
                                        <Trash2 size={12} /> 删除
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* 交叉分析区域 */}
                <CrossAnalysisSection
                    transcripts={transcripts}
                    crossAnalysis={crossAnalysis}
                    crossLoading={crossLoading}
                    onCrossAnalyze={handleCrossAnalyze}
                />
            </div>

            {/* 粘贴文本 Modal */}
            {showTextModal && (
                <AddTextModal
                    caseId={caseId}
                    onClose={() => setShowTextModal(false)}
                    onSuccess={() => { setShowTextModal(false); fetchDetail(); }}
                />
            )}

            {/* 上传文件 Modal */}
            {showEditModal && (
                <EditCaseModal
                    caseData={caseData}
                    onClose={() => setShowEditModal(false)}
                    onSuccess={() => { setShowEditModal(false); fetchDetail(); }}
                />
            )}

            {showUploadModal && (
                <UploadFileModal
                    caseId={caseId}
                    onClose={() => setShowUploadModal(false)}
                    onSuccess={() => { setShowUploadModal(false); fetchDetail(); }}
                />
            )}
        </div>
    );
}


/* ==================== 粘贴文本 Modal 组件 ==================== */
function AddTextModal({ caseId, onClose, onSuccess }) {
    const [form, setForm] = useState({
        title: '',
        type: '询问笔录',
        subject_name: '',
        subject_role: '嫌疑人',
        content: '',
        auto_analyze: true,
    });
    const [submitting, setSubmitting] = useState(false);

    const handleChange = (field, value) => {
        setForm(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = async () => {
        if (!form.title.trim() || !form.subject_name.trim() || !form.content.trim()) {
            message.warning('请填写标题、被询问人和笔录内容');
            return;
        }
        setSubmitting(true);
        try {
            const res = await createTranscript(caseId, form);
            if (res.success) {
                message.success('笔录添加成功');
                onSuccess();
            } else {
                message.error(res.error || '添加失败');
            }
        } catch {
            message.error('添加笔录失败');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <h3>添加笔录</h3>

                <div className="form-group">
                    <label>笔录标题 <span className="required">*</span></label>
                    <input value={form.title} onChange={e => handleChange('title', e.target.value)}
                        placeholder="如：张某第一次询问笔录" />
                </div>
                <div style={{ display: 'flex', gap: 12 }}>
                    <div className="form-group" style={{ flex: 1 }}>
                        <label>笔录类型 <span className="required">*</span></label>
                        <select value={form.type} onChange={e => handleChange('type', e.target.value)}>
                            <option value="询问笔录">询问笔录</option>
                            <option value="讯问笔录">讯问笔录</option>
                            <option value="陈述笔录">陈述笔录</option>
                            <option value="辨认笔录">辨认笔录</option>
                        </select>
                    </div>
                    <div className="form-group" style={{ flex: 1 }}>
                        <label>角色 <span className="required">*</span></label>
                        <select value={form.subject_role} onChange={e => handleChange('subject_role', e.target.value)}>
                            <option value="嫌疑人">嫌疑人</option>
                            <option value="被害人">被害人</option>
                            <option value="证人">证人</option>
                            <option value="报案人">报案人</option>
                        </select>
                    </div>
                </div>
                <div className="form-group">
                    <label>被询问人 <span className="required">*</span></label>
                    <input value={form.subject_name} onChange={e => handleChange('subject_name', e.target.value)}
                        placeholder="被询问/讯问人姓名" />
                </div>
                <div className="form-group">
                    <label>笔录内容 <span className="required">*</span></label>
                    <textarea className="modal-textarea" value={form.content}
                        onChange={e => handleChange('content', e.target.value)}
                        placeholder="在此粘贴笔录全文..." />
                </div>
                <div className="modal-checkbox">
                    <input type="checkbox" checked={form.auto_analyze}
                        onChange={e => handleChange('auto_analyze', e.target.checked)} />
                    提交后自动触发 AI 分析
                </div>
                <div className="form-actions">
                    <button className="btn-cancel" onClick={onClose}>取消</button>
                    <button className="btn-submit" onClick={handleSubmit} disabled={submitting}>
                        {submitting ? '提交中...' : '提交'}
                    </button>
                </div>
            </div>
        </div>
    );
}


/* ==================== 编辑案件 Modal 组件 ==================== */
function EditCaseModal({ caseData, onClose, onSuccess }) {
    const [form, setForm] = useState({
        case_name: caseData.case_name || '',
        case_number: caseData.case_number || '',
        case_type: caseData.case_type || '治安案件',
        description: caseData.description || '',
    });
    const [submitting, setSubmitting] = useState(false);

    const handleChange = (field, value) => {
        setForm(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = async () => {
        if (!form.case_name.trim()) {
            message.warning('案件名称不能为空');
            return;
        }
        setSubmitting(true);
        try {
            const res = await updateCase(caseData.case_id, form);
            if (res.success) {
                message.success('案件信息已更新');
                onSuccess();
            } else {
                message.error(res.error || '更新失败');
            }
        } catch (err) {
            message.error(err?.response?.data?.detail || '更新案件失败');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <h3>编辑案件信息</h3>
                <div className="modal-form">
                    <label>案件名称 *</label>
                    <input value={form.case_name} onChange={e => handleChange('case_name', e.target.value)} placeholder="请输入案件名称" />
                    <label>案件编号</label>
                    <input value={form.case_number} onChange={e => handleChange('case_number', e.target.value)} placeholder="选填" />
                    <label>案件类型</label>
                    <select value={form.case_type} onChange={e => handleChange('case_type', e.target.value)}>
                        <option value="治安案件">治安案件</option>
                        <option value="刑事案件">刑事案件</option>
                        <option value="行政案件">行政案件</option>
                        <option value="其他">其他</option>
                    </select>
                    <label>案件描述</label>
                    <textarea value={form.description} onChange={e => handleChange('description', e.target.value)} placeholder="选填" rows={3} />
                </div>
                <div className="modal-footer">
                    <button className="btn-cancel" onClick={onClose}>取消</button>
                    <button className="btn-primary" onClick={handleSubmit} disabled={submitting}>
                        {submitting ? '保存中...' : '保存'}
                    </button>
                </div>
            </div>
        </div>
    );
}


/* ==================== 上传文件 Modal 组件 ==================== */
function UploadFileModal({ caseId, onClose, onSuccess }) {
    const [file, setFile] = useState(null);
    const [form, setForm] = useState({
        title: '',
        type: '询问笔录',
        subject_name: '',
        subject_role: '嫌疑人',
        auto_analyze: true,
    });
    const [submitting, setSubmitting] = useState(false);
    const [dragging, setDragging] = useState(false);
    const fileInputRef = useRef(null);

    const handleChange = (field, value) => {
        setForm(prev => ({ ...prev, [field]: value }));
    };

    const handleFile = (f) => {
        if (f) {
            const ext = f.name.rsplit ? '' : f.name.split('.').pop().toLowerCase();
            if (!['doc', 'docx', 'txt'].includes(ext)) {
                message.error('仅支持 .doc、.docx 和 .txt 文件');
                return;
            }
            if (f.size > 10 * 1024 * 1024) {
                message.error('文件大小不能超过 10MB');
                return;
            }
            setFile(f);
            if (!form.title) {
                handleChange('title', f.name.replace(/\.(doc|docx|txt)$/i, ''));
            }
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragging(false);
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleSubmit = async () => {
        if (!file) {
            message.warning('请选择文件');
            return;
        }
        if (!form.title.trim() || !form.subject_name.trim()) {
            message.warning('请填写标题和被询问人');
            return;
        }
        setSubmitting(true);
        try {
            const res = await uploadTranscript(caseId, file, form);
            if (res.success) {
                message.success('笔录上传成功');
                onSuccess();
            } else {
                message.error(res.error || '上传失败');
            }
        } catch (err) {
            const detail = err.response?.data?.detail || err.message || '上传笔录失败';
            message.error(detail);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <h3>上传笔录文件</h3>

                {!file ? (
                    <div
                        className={`upload-zone ${dragging ? 'dragging' : ''}`}
                        onClick={() => fileInputRef.current?.click()}
                        onDragOver={e => { e.preventDefault(); setDragging(true); }}
                        onDragLeave={() => setDragging(false)}
                        onDrop={handleDrop}
                    >
                        <Upload size={32} />
                        <p>点击或拖拽文件到此处上传</p>
                        <p>支持 .doc / .docx / .txt，最大 10MB</p>
                        <input ref={fileInputRef} type="file" accept=".doc,.docx,.txt" hidden
                            onChange={e => e.target.files[0] && handleFile(e.target.files[0])} />
                    </div>
                ) : (
                    <div className="upload-file-info">
                        <FileText size={16} /> {file.name} ✓
                    </div>
                )}

                <div className="form-group">
                    <label>笔录标题 <span className="required">*</span></label>
                    <input value={form.title} onChange={e => handleChange('title', e.target.value)} />
                </div>
                <div style={{ display: 'flex', gap: 12 }}>
                    <div className="form-group" style={{ flex: 1 }}>
                        <label>笔录类型 <span className="required">*</span></label>
                        <select value={form.type} onChange={e => handleChange('type', e.target.value)}>
                            <option value="询问笔录">询问笔录</option>
                            <option value="讯问笔录">讯问笔录</option>
                            <option value="陈述笔录">陈述笔录</option>
                            <option value="辨认笔录">辨认笔录</option>
                        </select>
                    </div>
                    <div className="form-group" style={{ flex: 1 }}>
                        <label>角色 <span className="required">*</span></label>
                        <select value={form.subject_role} onChange={e => handleChange('subject_role', e.target.value)}>
                            <option value="嫌疑人">嫌疑人</option>
                            <option value="被害人">被害人</option>
                            <option value="证人">证人</option>
                            <option value="报案人">报案人</option>
                        </select>
                    </div>
                </div>
                <div className="form-group">
                    <label>被询问人 <span className="required">*</span></label>
                    <input value={form.subject_name} onChange={e => handleChange('subject_name', e.target.value)}
                        placeholder="被询问/讯问人姓名" />
                </div>
                <div className="modal-checkbox">
                    <input type="checkbox" checked={form.auto_analyze}
                        onChange={e => handleChange('auto_analyze', e.target.checked)} />
                    提交后自动触发 AI 分析
                </div>
                <div className="form-actions">
                    <button className="btn-cancel" onClick={onClose}>取消</button>
                    <button className="btn-submit" onClick={handleSubmit} disabled={submitting}>
                        {submitting ? '上传中...' : '上传并提交'}
                    </button>
                </div>
            </div>
        </div>
    );
}


/* ==================== 交叉分析区域组件 ==================== */
function CrossAnalysisSection({ transcripts, crossAnalysis, crossLoading, onCrossAnalyze }) {
    const analyzedCount = transcripts.filter(t => t.analysis_status === 'analyzed').length;
    const totalCount = transcripts.length;
    const canAnalyze = analyzedCount >= 2;
    const status = crossAnalysis?.analysis_status;

    const getScoreClass = (score) => {
        if (score >= 75) return 'high';
        if (score >= 40) return 'medium';
        return 'low';
    };

    const getSeverityIcon = (severity) => {
        if (severity === 'high') return '🔴';
        if (severity === 'medium') return '🟡';
        return '🔵';
    };

    const circumference = 2 * Math.PI * 42;

    return (
        <div className="cross-analysis-section">
            <div className="cross-section-header">
                <span className="cross-section-title">
                    <GitCompareArrows size={20} /> 交叉分析
                </span>
                <button
                    className="cross-analyze-btn"
                    onClick={onCrossAnalyze}
                    disabled={!canAnalyze || crossLoading || status === 'analyzing'}
                >
                    {crossLoading || status === 'analyzing' ? (
                        <><Loader size={14} /> 分析中...</>
                    ) : status === 'analyzed' ? (
                        <><RefreshCw size={14} /> 重新分析</>
                    ) : (
                        <><Activity size={14} /> 开始交叉分析</>
                    )}
                </button>
            </div>

            {!canAnalyze && !status && (
                <div className="cross-status-hint">
                    <FileSearch size={32} />
                    <p>需要 2 份及以上已分析笔录才能开始交叉分析</p>
                    <p>当前：{analyzedCount}/{totalCount} 已分析</p>
                </div>
            )}

            {status === 'analyzing' && (
                <div className="cross-analyzing">
                    <div className="spinner"></div>
                    <p>正在进行交叉比对分析，请稍候...</p>
                </div>
            )}

            {status === 'failed' && (
                <div className="cross-status-hint">
                    <AlertCircle size={32} style={{ color: '#ef4444' }} />
                    <p style={{ color: '#ef4444' }}>交叉分析失败，请重试</p>
                </div>
            )}

            {status === 'analyzed' && crossAnalysis && (
                <>
                    {/* 一致性评分仪表盘 */}
                    <ConsistencyDashboard
                        score={crossAnalysis.consistency_score || 0}
                        circumference={circumference}
                        getScoreClass={getScoreClass}
                    />

                    {/* 矛盾点列表 */}
                    {crossAnalysis.contradictions?.length > 0 && (
                        <div className="contradictions-list">
                            <h4><AlertTriangle size={16} /> 矛盾点（{crossAnalysis.contradictions.length} 处）</h4>
                            {crossAnalysis.contradictions.map((c, i) => (
                                <div key={i} className={`contradiction-card severity-${c.severity}`}>
                                    <div className="contradiction-header">
                                        <span className={`severity-tag tag-${c.severity}`}>
                                            {getSeverityIcon(c.severity)} {c.severity === 'high' ? '严重' : c.severity === 'medium' ? '中等' : '轻微'}
                                        </span>
                                        <span className="contradiction-type">{c.type}</span>
                                    </div>
                                    <div className="contradiction-desc">{c.description}</div>
                                    {c.sources?.length > 0 && (
                                        <div className="contradiction-sources">
                                            {c.sources.map((s, j) => (
                                                <div key={j} className="source-quote">
                                                    <span className="source-person">{s.person}：</span>
                                                    <span className="source-text">"{s.quote}"</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* 统一时间线 */}
                    {crossAnalysis.unified_timeline?.length > 0 && (
                        <div className="unified-timeline">
                            <h4><Clock size={16} /> 统一时间线</h4>
                            <div className="timeline-track">
                                {crossAnalysis.unified_timeline.map((ev, i) => (
                                    <div key={i} className="timeline-node">
                                        <div className={`timeline-dot ${ev.disputed_by?.length > 0 ? 'disputed' : ''}`}></div>
                                        <div className="timeline-time">{ev.time}</div>
                                        <div className="timeline-event-text">{ev.event}</div>
                                        <div className="timeline-parties">
                                            {ev.agreed_by?.map((name, j) => (
                                                <span key={`a-${j}`} className="party-agreed">✓ {name}</span>
                                            ))}
                                            {ev.disputed_by?.map((name, j) => (
                                                <span key={`d-${j}`} className="party-disputed">⚠ {name}</span>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 证据链 */}
                    {crossAnalysis.evidence_chain?.length > 0 && (
                        <div className="evidence-chain">
                            <h4><Package size={16} /> 证据链</h4>
                            <div className="evidence-grid">
                                {crossAnalysis.evidence_chain.map((ev, i) => (
                                    <div key={i} className="evidence-card">
                                        <div className={`evidence-icon ${ev.status === '已获取' ? 'obtained' : 'needed'}`}>
                                            {ev.status === '已获取' ? '✅' : '❓'}
                                        </div>
                                        <div className="evidence-info">
                                            <div className="evidence-type">{ev.type}</div>
                                            <div className="evidence-desc">{ev.description}</div>
                                            {ev.source_transcripts?.length > 0 && (
                                                <div className="evidence-sources">
                                                    来源：{ev.source_transcripts.join('、')}
                                                </div>
                                            )}
                                        </div>
                                        <span className={`evidence-status-tag ${ev.status === '已获取' ? 'obtained' : 'needed'}`}>
                                            {ev.status}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 综合摘要 */}
                    {crossAnalysis.summary && (
                        <div className="cross-summary">
                            <h4><FileText size={16} /> 综合分析</h4>
                            {crossAnalysis.summary}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}


/* ==================== 一致性评分环形图组件 ==================== */
function ConsistencyDashboard({ score, circumference, getScoreClass }) {
    const scoreClass = getScoreClass(score);
    const dashoffset = circumference - (score / 100) * circumference;

    return (
        <div className="consistency-dashboard">
            <div className="score-ring">
                <svg width="100" height="100" viewBox="0 0 100 100">
                    <circle className="score-ring-bg" cx="50" cy="50" r="42" />
                    <circle
                        className={`score-ring-fill ring-${scoreClass}`}
                        cx="50" cy="50" r="42"
                        strokeDasharray={circumference}
                        strokeDashoffset={dashoffset}
                    />
                </svg>
                <span className={`score-ring-text score-${scoreClass}`}>{Math.round(score)}</span>
            </div>
            <div className="score-details">
                <h4>一致性评分</h4>
                <p>
                    {score >= 75 ? '各方陈述整体一致，矛盾点较少。' :
                     score >= 40 ? '存在一定矛盾，需重点关注异议事项。' :
                     '各方陈述矛盾较多，建议进一步核实关键事实。'}
                </p>
            </div>
        </div>
    );
}
