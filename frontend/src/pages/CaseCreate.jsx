import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { ArrowLeft, X } from 'lucide-react';
import { createCase } from '../services/api';
import '../styles/Case.css';

export default function CaseCreate() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({
        case_name: '',
        case_number: '',
        case_type: '治安案件',
        description: '',
        tags: [],
    });
    const [tagInput, setTagInput] = useState('');

    const handleChange = (field, value) => {
        setForm(prev => ({ ...prev, [field]: value }));
    };

    const handleAddTag = (e) => {
        if (e.key === 'Enter' && tagInput.trim()) {
            e.preventDefault();
            const tag = tagInput.trim();
            if (!form.tags.includes(tag)) {
                setForm(prev => ({ ...prev, tags: [...prev.tags, tag] }));
            }
            setTagInput('');
        }
    };

    const handleRemoveTag = (idx) => {
        setForm(prev => ({
            ...prev,
            tags: prev.tags.filter((_, i) => i !== idx),
        }));
    };

    const handleSubmit = async () => {
        if (!form.case_name.trim()) {
            message.warning('请输入案件名称');
            return;
        }
        setLoading(true);
        try {
            const res = await createCase(form);
            if (res.success) {
                message.success('案件创建成功');
                navigate(`/cases/${res.data.case_id}`);
            } else {
                message.error(res.error || '创建失败');
            }
        } catch {
            message.error('创建案件失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="case-create-page">
            <button className="case-create-back" onClick={() => navigate('/cases')}>
                <ArrowLeft size={16} /> 返回案件列表
            </button>

            <div className="case-create-card">
                <h2>新建案件</h2>

                <div className="form-group">
                    <label>案件名称 <span className="required">*</span></label>
                    <input
                        value={form.case_name}
                        onChange={e => handleChange('case_name', e.target.value)}
                        placeholder="如：张某故意伤害案"
                    />
                </div>

                <div className="form-group">
                    <label>案件编号</label>
                    <input
                        value={form.case_number}
                        onChange={e => handleChange('case_number', e.target.value)}
                        placeholder="如：北公治行受字[2026]001号"
                    />
                </div>

                <div className="form-group">
                    <label>案件类型 <span className="required">*</span></label>
                    <select value={form.case_type} onChange={e => handleChange('case_type', e.target.value)}>
                        <option value="治安案件">治安案件</option>
                        <option value="刑事案件">刑事案件</option>
                        <option value="行政案件">行政案件</option>
                    </select>
                </div>

                <div className="form-group">
                    <label>案件简述</label>
                    <textarea
                        value={form.description}
                        onChange={e => handleChange('description', e.target.value)}
                        placeholder="简要描述案情..."
                        rows={3}
                    />
                </div>

                <div className="form-group">
                    <label>标签</label>
                    <div className="tag-input-wrapper">
                        {form.tags.map((tag, i) => (
                            <span key={i} className="tag-item">
                                {tag}
                                <button onClick={() => handleRemoveTag(i)}><X size={12} /></button>
                            </span>
                        ))}
                        <input
                            value={tagInput}
                            onChange={e => setTagInput(e.target.value)}
                            onKeyDown={handleAddTag}
                            placeholder="输入标签后按回车"
                        />
                    </div>
                </div>

                <div className="form-actions">
                    <button className="btn-cancel" onClick={() => navigate('/cases')}>取消</button>
                    <button className="btn-submit" onClick={handleSubmit} disabled={loading}>
                        {loading ? '创建中...' : '创建案件'}
                    </button>
                </div>
            </div>
        </div>
    );
}
