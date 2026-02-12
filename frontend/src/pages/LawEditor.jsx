import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Form, Input, Button, DatePicker, Select, Card, Row, Col, Divider } from 'antd';
import { ChevronLeft, Save, FileText, Zap, Info } from 'lucide-react';
import axios from 'axios';
import dayjs from 'dayjs';
import { getLawCategories, getLawLevels } from '../services/api';

const { TextArea } = Input;
const { Option } = Select;

/**
 * 中文数字转阿拉伯数字（与 import_local.py 一致）
 */
function chineseToNumber(chn) {
    if (!chn) return 0;
    if (/^\d+$/.test(chn)) return parseInt(chn, 10);

    const chineseMap = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000
    };

    // 特殊情况：十、十一 -> 一十、一十一
    if (chn.startsWith('十')) {
        chn = '一' + chn;
    }

    let result = 0;
    let unitVal = 0;

    for (const char of chn) {
        if (!(char in chineseMap)) continue;
        const val = chineseMap[char];

        if (val >= 10) { // 是单位
            if (unitVal === 0) unitVal = 1;
            result += unitVal * val;
            unitVal = 0;
        } else { // 是数字
            unitVal = val;
        }
    }
    result += unitVal; // 加上最后的个位数
    return result;
}

/**
 * 解析元数据（标题、修订说明、发布日期等）
 * 与 import_local.py 的 parse_metadata 保持一致
 */
function parseMetadata(content) {
    const metadata = {
        title: '',
        issue_date: '',
        effect_date: '',
        issue_org: '',
        status: '现行有效',
        category: '',
        level: '法律',
        summary: ''
    };

    const lines = content.split('\n').map(l => l.trim()).filter(l => l);

    if (lines.length === 0) return metadata;

    // 第一行通常是标题
    metadata.title = lines[0];

    // 1. 尝试提取修订说明（圆括号包裹的长段落）
    for (let i = 1; i < Math.min(10, lines.length); i++) {
        const line = lines[i];
        if ((line.startsWith('(') || line.startsWith('（')) &&
            (line.includes('通过') || line.includes('修正') || line.includes('修订'))) {
            metadata.summary = line;
            break;
        }
    }

    // 2. 从前20行提取KV元数据
    const headerLines = lines.slice(0, 20);
    for (const line of headerLines) {
        if (line.includes('发布日期') || line.includes('公布日期')) {
            metadata.issue_date = extractValue(line);
        }
        if (line.includes('实施日期') || line.includes('施行日期')) {
            metadata.effect_date = extractValue(line);
        }
        if (line.includes('发布部门') || line.includes('发文机关') || line.includes('制定机关')) {
            metadata.issue_org = extractValue(line);
        }
        if (line.includes('效力') && (line.includes('级别') || line.includes('等级'))) {
            metadata.level = extractValue(line);
        }
        if (line.includes('类别')) {
            metadata.category = extractValue(line);
        }
    }

    // 3. 智能分类兜底
    if (!metadata.category) {
        if (lines[0].includes('刑') || lines[0].includes('罪')) {
            metadata.category = '刑事法律';
        } else if (lines[0].includes('治安') || lines[0].includes('行政')) {
            metadata.category = '行政法律';
        } else if (lines[0].includes('程') && lines[0].includes('定')) {
            metadata.category = '程序规定';
        }
    }

    return metadata;
}

function extractValue(line) {
    return line.split('：').pop().trim().split(':').pop().trim();
}

/**
 * 拆分条文（与 import_local.py 的 split_articles 保持一致）
 * 包括章节识别和剥离
 */
function splitArticles(fullText) {
    const articles = [];

    // 预处理：替换全角空格
    fullText = fullText.replace(/\u3000/g, ' ');

    // 核心正则：匹配 "第X条"
    const articlePattern = /(^|\n)\s*(第[零一二三四五六七八九十百千0-9]+条)\s*/g;

    // 找出所有匹配
    const matches = [];
    let match;
    while ((match = articlePattern.exec(fullText)) !== null) {
        matches.push({
            index: match.index,
            display: match[2].trim(),
            fullMatch: match[0]
        });
    }

    if (matches.length === 0) {
        // 没有匹配到标准条文格式
        return [{
            article_num: 1,
            article_display: '全文',
            content: fullText.trim(),
            chapter: '',
            section: ''
        }];
    }

    // 分别匹配：编、章、节、特殊章节（支持全角空格 \u3000 和普通空格）
    const partPattern = /^\s*(第[零一二三四五六七八九十百千]+编[\s\u3000]+.*)$/;
    const chapterPattern = /^\s*(第[零一二三四五六七八九十百千]+章[\s\u3000]+.*)$/;
    const sectionPattern = /^\s*(第[零一二三四五六七八九十百千]+节[\s\u3000]+.*)$/;
    const specialPattern = /^\s*(附[\s\u3000]*则|总[\s\u3000]*则|分[\s\u3000]*则)$/;

    let currentPart = '';
    let currentChapter = '';
    let currentSection = '';

    const getFullChapter = () => {
        const parts = [];
        if (currentPart) parts.push(currentPart);
        if (currentChapter) parts.push(currentChapter);
        if (currentSection) parts.push(currentSection);
        return parts.join(' / ');
    };

    const isStructureLine = (lineStrip) => {
        return partPattern.test(lineStrip) ||
            chapterPattern.test(lineStrip) ||
            sectionPattern.test(lineStrip) ||
            specialPattern.test(lineStrip);
    };

    const updateStructure = (lineStrip) => {
        if (partPattern.test(lineStrip)) {
            currentPart = lineStrip;
            currentChapter = '';
            currentSection = '';
        } else if (chapterPattern.test(lineStrip)) {
            currentChapter = lineStrip;
            currentSection = '';
        } else if (sectionPattern.test(lineStrip)) {
            currentSection = lineStrip;
        } else if (specialPattern.test(lineStrip)) {
            currentPart = lineStrip;
            currentChapter = '';
            currentSection = '';
        }
    };

    // 初始层级：扫描第一条之前的内容
    const preText = fullText.slice(0, matches[0].index);
    for (const line of preText.split('\n')) {
        const lineStrip = line.trim();
        if (isStructureLine(lineStrip)) {
            updateStructure(lineStrip);
        }
    }

    // ===== 新增：前言提取（司法解释特有） =====
    // 检测 "为依法...解释如下：" 类型的前言段落
    let preambleContent = null;
    const preLines = preText.split('\n');
    const preambleLines = [];
    let inPreamble = false;

    for (const line of preLines) {
        const lineStrip = line.trim();
        if (!lineStrip) continue;
        if (isStructureLine(lineStrip)) continue;
        // 检测前言开始
        if (lineStrip.startsWith('为') || lineStrip.startsWith('根据')) {
            inPreamble = true;
        }
        if (inPreamble) {
            preambleLines.push(lineStrip);
        }
        // 检测前言结束
        if (inPreamble && (lineStrip.endsWith('：') || lineStrip.endsWith(':'))) {
            break;
        }
    }

    if (preambleLines.length > 0) {
        preambleContent = preambleLines.join('');
    }


    // 遍历每一条
    for (let i = 0; i < matches.length; i++) {
        const current = matches[i];
        const start = current.index;
        const end = i + 1 < matches.length ? matches[i + 1].index : fullText.length;

        // 提取原始内容块
        const rawContent = fullText.slice(start, end);
        const lines = rawContent.split('\n');

        const cleanedLines = [];
        const foundNextStructures = [];

        for (const line of lines) {
            const lineStrip = line.trim();
            if (!lineStrip) {
                cleanedLines.push(line);
                continue;
            }

            if (isStructureLine(lineStrip)) {
                foundNextStructures.push(lineStrip);
                continue;
            }

            cleanedLines.push(line);
        }

        // 记录当前条文的章节
        const chapterForArticle = getFullChapter();

        // 重新组合内容
        let contentStr = cleanedLines.join('\n').trim();
        const displayPattern = new RegExp(`^\\s*${current.display}\\s*`);
        contentStr = contentStr.replace(displayPattern, '').trim();

        articles.push({
            article_num: i + 1,
            article_display: current.display,
            content: contentStr,
            chapter: chapterForArticle,
            section: ''
        });

        // 更新结构层级
        for (const structLine of foundNextStructures) {
            updateStructure(structLine);
        }
    }

    // ===== 新增：将前言插入为第零条 =====
    if (preambleContent) {
        // 重新编号
        for (const art of articles) {
            art.article_num += 1;
        }
        // 插入前言
        articles.unshift({
            article_num: 0,
            article_display: '前言',
            content: preambleContent,
            chapter: '',
            section: ''
        });
    }

    return articles;
}

export default function LawEditor() {
    const navigate = useNavigate();
    const [form] = Form.useForm();
    const [parsedArticles, setParsedArticles] = useState([]);
    const [isParsing, setIsParsing] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    // 动态选项状态
    const [categories, setCategories] = useState(['刑事法律', '行政法律', '民事法律', '社会法律', '行政法规', '司法解释', '部门规章', '地方条例', '实施办法', '内部规章', '其他']);
    const [levels, setLevels] = useState(['法律', '行政法规', '部门规章', '地方性法规', '司法解释', '内部规章', '其他']);

    useEffect(() => {
        const fetchOptions = async () => {
            try {
                const [catRes, levelRes] = await Promise.all([
                    getLawCategories(),
                    getLawLevels()
                ]);

                if (catRes.success && catRes.data) {
                    setCategories(prev => {
                        const combined = [...new Set([...prev, ...catRes.data])];
                        return combined.filter(c => c && c !== '全部');
                    });
                }

                if (levelRes.success && levelRes.data) {
                    setLevels(prev => {
                        return [...new Set([...prev, ...levelRes.data])];
                    });
                }
            } catch (error) {
                console.error('获取动态选项失败:', error);
            }
        };
        fetchOptions();
    }, []);

    // 核心功能：智能解析全文（与 import_local.py 一致）
    const handleSmartParse = () => {
        const content = form.getFieldValue('rawContent');
        if (!content) {
            message.warning('请先粘贴法规全文');
            return;
        }

        setIsParsing(true);
        try {
            // 1. 解析元数据
            const metadata = parseMetadata(content);

            // 自动填充表单字段
            if (metadata.title) form.setFieldValue('title', metadata.title);
            if (metadata.issue_org) form.setFieldValue('issue_org', metadata.issue_org);
            if (metadata.category) form.setFieldValue('category', metadata.category);
            if (metadata.level) form.setFieldValue('level', metadata.level);
            if (metadata.summary) form.setFieldValue('summary', metadata.summary);
            if (metadata.issue_date) {
                const d = dayjs(metadata.issue_date);
                if (d.isValid()) form.setFieldValue('issue_date', d);
            }
            if (metadata.effect_date) {
                const d = dayjs(metadata.effect_date);
                if (d.isValid()) form.setFieldValue('effect_date', d);
            }

            // 2. 拆分条文
            const articles = splitArticles(content);
            setParsedArticles(articles);

            // 统计章节数
            const chapters = new Set(articles.filter(a => a.chapter).map(a => a.chapter));

            message.success(`成功识别 ${articles.length} 条条文${chapters.size > 0 ? `，${chapters.size} 个章节` : ''}`);
        } catch (error) {
            console.error(error);
            message.error('解析失败');
        } finally {
            setIsParsing(false);
        }
    };

    const handleSubmit = async (values) => {
        if (parsedArticles.length === 0) {
            message.error('请先点击"智能解析"验证条文内容');
            return;
        }

        setSubmitting(true);
        try {
            const payload = {
                title: values.title,
                issue_org: values.issue_org,
                issue_date: values.issue_date?.format('YYYY-MM-DD') || '',
                effect_date: values.effect_date?.format('YYYY-MM-DD') || '',
                category: values.category,
                level: values.level,
                status: values.status,
                summary: values.summary || '',
                articles: parsedArticles.map((a, index) => ({
                    article_num: a.article_num || index + 1,
                    article_display: a.article_display,
                    content: a.content,
                    chapter: a.chapter || '',
                    section: a.section || ''
                }))
            };

            await axios.post('/api/laws/', payload);
            message.success('录入成功！');
            navigate('/laws');

        } catch (error) {
            console.error(error);
            const errorMsg = error.response?.data?.detail || error.message || '保存失败';
            message.error(`保存失败: ${errorMsg}`);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div style={{ paddingBottom: '3rem' }}>
            <section className="hero-section" style={{ padding: '2rem 1rem 3rem', background: 'linear-gradient(to right, #0f172a, #334155)' }}>
                <div className="container">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <FileText size={40} color="#38bdf8" />
                            <h2 className="hero-title" style={{ textAlign: 'left', margin: 0 }}>手动录入新法规</h2>
                        </div>
                        <button className="category-button" style={{ background: 'rgba(255,255,255,0.1)', color: 'white', border: 'none', display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer' }} onClick={() => navigate('/laws')}>
                            <ChevronLeft size={18} /> 返回列表
                        </button>
                    </div>
                </div>
            </section>

            <div className="main-content" style={{ marginTop: '-1.5rem', maxWidth: '1400px', margin: '-1.5rem auto 0', padding: '0 1rem' }}>
                <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ category: '刑事法律', level: '法律', status: '现行有效' }}>
                    <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
                        {/* 左侧：编辑区 */}
                        <div className="content-card" style={{ flex: 1, padding: '2rem', display: 'block', minHeight: 'auto' }}>
                            <h3 className="section-title"><FileText size={18} /> 基本信息</h3>
                            <Form.Item name="title" label="法规标题" rules={[{ required: true }]}>
                                <Input size="large" placeholder="例如：中华人民共和国刑法" />
                            </Form.Item>

                            <Form.Item name="summary" label="修订说明">
                                <TextArea rows={2} placeholder="（2023年12月29日第十四届全国人民代表大会常务委员会第七次会议通过）" />
                            </Form.Item>

                            <Row gutter={16}>
                                <Col span={12}>
                                    <Form.Item name="issue_org" label="制定机关" rules={[{ required: true }]}>
                                        <Input placeholder="例如：全国人大常委会" />
                                    </Form.Item>
                                </Col>
                                <Col span={12}>
                                    <Form.Item name="status" label="效力状态">
                                        <Select>
                                            <Option value="现行有效">现行有效</Option>
                                            <Option value="尚未生效">尚未生效</Option>
                                            <Option value="已修订">已修订</Option>
                                            <Option value="已失效">已废止</Option>
                                        </Select>
                                    </Form.Item>
                                </Col>
                            </Row>

                            <Row gutter={16}>
                                <Col span={12}>
                                    <Form.Item name="issue_date" label="发布日期">
                                        <DatePicker style={{ width: '100%' }} />
                                    </Form.Item>
                                </Col>
                                <Col span={12}>
                                    <Form.Item name="effect_date" label="实施日期">
                                        <DatePicker style={{ width: '100%' }} />
                                    </Form.Item>
                                </Col>
                            </Row>

                            <Row gutter={16}>
                                <Col span={12}>
                                    <Form.Item name="category" label="法规分类">
                                        <Select placeholder="请选择或输入分类" showSearch allowClear dropdownRender={menu => (
                                            <>
                                                {menu}
                                            </>
                                        )}>
                                            {categories.map(cat => (
                                                <Option key={cat} value={cat}>{cat}</Option>
                                            ))}
                                        </Select>
                                    </Form.Item>
                                </Col>
                                <Col span={12}>
                                    <Form.Item name="level" label="效力层级">
                                        <Select placeholder="请选择或输入层级" showSearch allowClear>
                                            {levels.map(level => (
                                                <Option key={level} value={level}>{level}</Option>
                                            ))}
                                        </Select>
                                    </Form.Item>
                                </Col>
                            </Row>

                            <Divider />

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                <h3 className="section-title" style={{ margin: 0 }}><Zap size={18} /> 正文内容</h3>
                                <Button type="primary" icon={<Zap size={14} />} onClick={handleSmartParse} loading={isParsing}>
                                    智能解析全文
                                </Button>
                            </div>

                            <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '8px', padding: '12px', marginBottom: '1rem', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                                <Info size={18} color="#0284c7" style={{ flexShrink: 0, marginTop: '2px' }} />
                                <div style={{ fontSize: '13px', color: '#0369a1' }}>
                                    <strong>智能解析功能：</strong>
                                    <ul style={{ margin: '4px 0 0 0', paddingLeft: '20px' }}>
                                        <li>自动识别法规标题、修订说明、发布日期等元数据</li>
                                        <li>自动拆分"第X条"格式的条文</li>
                                        <li>自动识别"第X章"、"第X节"等章节结构</li>
                                        <li>支持中文数字（一、二、十三等）</li>
                                    </ul>
                                </div>
                            </div>

                            <Form.Item name="rawContent" help="直接粘贴法规全文，点击「智能解析」自动识别结构">
                                <TextArea
                                    rows={18}
                                    placeholder={`请在此处粘贴法规全文...

中华人民共和国治安管理处罚法

（2005年8月28日第十届全国人民代表大会常务委员会...）

第一章　总则

第一条　为了维护社会治安秩序，保障公共安全...

第二条　扰乱公共秩序...`}
                                    style={{ fontFamily: 'monospace', fontSize: '14px' }}
                                />
                            </Form.Item>

                            <Form.Item>
                                <Button type="primary" htmlType="submit" icon={<Save size={16} />} loading={submitting} block style={{ height: '45px', fontSize: '16px' }}>
                                    保存并入库
                                </Button>
                            </Form.Item>
                        </div>

                        {/* 右侧：预览区 */}
                        <div className="content-card" style={{ flex: 1, padding: '2rem', background: '#f8fafc', display: 'block', minHeight: 'auto' }}>
                            <h3 className="section-title">解析结果预览 ({parsedArticles.length} 条)</h3>
                            <div className="parse-preview" style={{ maxHeight: '900px', overflowY: 'auto' }}>
                                {parsedArticles.length > 0 ? (
                                    parsedArticles.map((article, idx) => (
                                        <div key={idx} style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e2e8f0' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                                                <span style={{ fontWeight: 'bold', color: '#2563eb' }}>
                                                    {article.article_display}
                                                </span>
                                                {article.chapter && (
                                                    <span style={{ fontSize: '12px', padding: '2px 8px', background: '#e0f2fe', color: '#0284c7', borderRadius: '4px' }}>
                                                        {article.chapter}
                                                    </span>
                                                )}
                                            </div>
                                            <div style={{ color: '#334155', whiteSpace: 'pre-wrap', fontSize: '14px', lineHeight: '1.6' }}>
                                                {article.content}
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div style={{ textAlign: 'center', color: '#94a3b8', marginTop: '100px' }}>
                                        <FileText size={48} style={{ opacity: 0.2 }} />
                                        <p>等待解析...</p>
                                        <p style={{ fontSize: '12px' }}>请在左侧粘贴法规全文并点击"智能解析"</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </Form>
            </div >
        </div >
    );
}
