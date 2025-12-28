import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Button, message, Space } from 'antd';
import { ChevronLeft, FileText, Download, Eye, Save } from 'lucide-react';
import { getTemplateDetail, renderTemplate, exportToPDF, exportToDOCX } from '../services/api';

const { TextArea } = Input;

export default function TemplateEditor() {
    const { templateId } = useParams();
    const navigate = useNavigate();
    const [template, setTemplate] = useState(null);
    const [loading, setLoading] = useState(true);
    const [preview, setPreview] = useState('');
    const [form] = Form.useForm();

    useEffect(() => {
        if (templateId !== 'new') {
            const fetchTemplate = async () => {
                try {
                    const response = await getTemplateDetail(templateId);
                    setTemplate(response.data);
                } catch (error) { message.error('加载详情失败'); }
                finally { setLoading(false); }
            };
            fetchTemplate();
        } else { setLoading(false); }
    }, [templateId]);

    const handlePreview = async (values) => {
        try {
            const response = await renderTemplate(templateId, values);
            setPreview(response.data.content);
            message.success('预览已更新');
        } catch (error) { message.error('预览失败'); }
    };

    const handleExport = async (format) => {
        const values = form.getFieldsValue();
        try {
            const blob = format === 'pdf' ? await exportToPDF(templateId, values) : await exportToDOCX(templateId, values);
            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${template.name}.${format}`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            message.success(`${format.toUpperCase()} 导出成功`);
        } catch (error) { message.error('导出失败，请检查后端配置'); }
    };

    if (loading) return <div className="loading-spinner"><div className="spinner"></div></div>;

    return (
        <div style={{ paddingBottom: '3rem' }}>
            <section className="hero-section" style={{ padding: '2rem 1rem 3rem', background: 'linear-gradient(to bottom, #581c87, #2e1065)' }}>
                <div className="container">
                    <button className="category-button" style={{ marginBottom: '1.5rem', background: 'rgba(255,255,255,0.1)', color: 'white', border: 'none', display: 'flex', alignItems: 'center', gap: '8px' }} onClick={() => navigate('/templates')}>
                        <ChevronLeft size={18} /> 返回模板库
                    </button>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <FileText size={40} color="#c084fc" />
                        <h2 className="hero-title" style={{ textAlign: 'left', margin: 0 }}>{template ? `填写文书: ${template.name}` : '新建模板'}</h2>
                    </div>
                </div>
            </section>

            <div className="main-content" style={{ marginTop: '-1.5rem', display: 'flex', gap: '2rem', maxWidth: '1200px', margin: '-1.5rem auto 0' }}>
                {/* 左侧表单 */}
                <div className="content-card" style={{ flex: 1, display: 'block', padding: '2rem' }}>
                    <h3 className="section-title" style={{ marginBottom: '1.5rem', display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <Save size={18} /> 表单详情
                    </h3>
                    <Form form={form} layout="vertical" onFinish={handlePreview}>
                        {template?.fields?.map(field => (
                            <Form.Item key={field.name} name={field.name} label={field.label} rules={[{ required: field.required, message: '必填项' }]}>
                                {field.type === 'textarea' ? <TextArea rows={4} placeholder={`请输入${field.label}`} /> : <Input placeholder={`请输入${field.label}`} />}
                            </Form.Item>
                        ))}
                        <Form.Item>
                            <Space>
                                <button type="submit" className="search-button" style={{ position: 'static', transform: 'none', background: '#9333ea' }}>
                                    <Eye size={16} /> 更新预览
                                </button>
                                <button type="button" className="nav-button" style={{ background: '#f8fafc', border: '1px solid #e2e8f0', color: '#1e293b' }} onClick={() => handleExport('pdf')}>
                                    <Download size={16} /> PDF
                                </button>
                                <button type="button" className="nav-button" style={{ background: '#f8fafc', border: '1px solid #e2e8f0', color: '#1e293b' }} onClick={() => handleExport('docx')}>
                                    <Download size={16} /> Word
                                </button>
                            </Space>
                        </Form.Item>
                    </Form>
                </div>

                {/* 右侧预览 */}
                <div className="content-card" style={{ flex: 1, display: 'block', padding: '2rem', background: '#f8fafc' }}>
                    <h3 className="section-title" style={{ marginBottom: '1.5rem', display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <Eye size={18} /> 文书预览
                    </h3>
                    <div style={{ background: 'white', padding: '2rem', minHeight: '400px', boxShadow: 'inset 0 2px 4px 0 rgba(0,0,0,0.06)', borderRadius: '8px', whiteSpace: 'pre-wrap', lineHeight: '1.8', fontSzie: '16px' }}>
                        {preview || <div style={{ color: '#94a3b8', textAlign: 'center', paddingTop: '100px' }}>填写左侧表单并点击“更新预览”以查看效果</div>}
                    </div>
                </div>
            </div>
        </div>
    );
}
