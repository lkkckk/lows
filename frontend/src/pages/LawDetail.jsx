/**
 * 法规详情页 - 纯 CSS 重构版本
 */
import { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { message, Input, Button, Spin } from 'antd';
import { Search, ChevronLeft, Shield, Book, Bookmark, ChevronUp, ChevronDown } from 'lucide-react';
import { getLawDetail, getLawArticles, searchInLaw } from '../services/api';
import '../styles/LawDetail.css';

export default function LawDetail() {
    const { lawId } = useParams();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    const [law, setLaw] = useState(null);
    const [articles, setArticles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [contentReady, setContentReady] = useState(false); // 内容是否就绪（滚动完成后）
    const [searching, setSearching] = useState(false);
    const [highlightedArticle, setHighlightedArticle] = useState(null);
    const [highlightKeyword, setHighlightKeyword] = useState('');

    // 搜索结果导航状态
    const [searchResults, setSearchResults] = useState([]);
    const [currentResultIndex, setCurrentResultIndex] = useState(0);
    const [isSummaryExpanded, setIsSummaryExpanded] = useState(false);

    const articlesContainerRef = useRef(null);

    // 缓存配置
    const CACHE_PREFIX = 'law_cache_';
    const CACHE_TTL = 30 * 60 * 1000; // 30分钟

    // 从缓存读取法规数据
    const getCachedLaw = (lawId) => {
        try {
            const key = `${CACHE_PREFIX}${lawId}`;
            const cached = sessionStorage.getItem(key);
            if (!cached) return null;

            const { data, timestamp } = JSON.parse(cached);
            // 检查是否过期
            if (Date.now() - timestamp > CACHE_TTL) {
                sessionStorage.removeItem(key);
                return null;
            }
            return data;
        } catch (error) {
            console.error('读取缓存失败:', error);
            return null;
        }
    };

    // 写入缓存
    const setCachedLaw = (lawId, data) => {
        try {
            const key = `${CACHE_PREFIX}${lawId}`;
            sessionStorage.setItem(key, JSON.stringify({
                data,
                timestamp: Date.now()
            }));
        } catch (error) {
            console.error('写入缓存失败:', error);
        }
    };

    // 获取 URL 参数
    const targetArticle = searchParams.get('article');
    const targetKeyword = searchParams.get('kw');

    useEffect(() => {
        fetchLawData();
    }, [lawId]);

    // 数据加载完成后处理跳转
    useEffect(() => {
        if (!loading && articles.length > 0) {
            if (targetArticle) {
                // 如果有目标条文，设置高亮关键字
                setHighlightKeyword(targetKeyword || '');
                // 延迟滚动，确保 DOM 已渲染
                setTimeout(() => {
                    scrollToArticle(parseInt(targetArticle));
                    // 滚动完成后显示内容
                    setTimeout(() => setContentReady(true), 50);
                }, 50);
            } else if (targetKeyword) {
                handleSearch(targetKeyword);
                setContentReady(true);
            } else {
                // 没有目标条文时直接显示
                setContentReady(true);
            }
        }
    }, [loading, articles, targetArticle, targetKeyword]);

    const fetchLawData = async () => {
        // 先尝试从缓存读取
        const cached = getCachedLaw(lawId);
        if (cached) {
            setLaw(cached.law);
            setArticles(cached.articles);
            setLoading(false);
            setContentReady(true); // 缓存数据立即可用
            return;
        }

        // 缓存未命中，从服务器加载
        setLoading(true);
        try {
            const [lawRes, articlesRes] = await Promise.all([
                getLawDetail(lawId),
                getLawArticles(lawId),
            ]);
            setLaw(lawRes.data);
            setArticles(articlesRes.data || []);

            // 写入缓存
            setCachedLaw(lawId, {
                law: lawRes.data,
                articles: articlesRes.data || []
            });
        } catch (error) {
            message.error('加载法规详情失败');
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = async (value) => {
        if (!value.trim()) {
            message.warning('请输入搜索内容');
            return;
        }
        setSearching(true);
        setHighlightKeyword(value);
        try {
            // 获取所有匹配结果（最多100条）
            const response = await searchInLaw(lawId, { query: value, page: 1, page_size: 100 });
            if (response.data && response.data.length > 0) {
                const results = response.data.map(r => r.article_num);
                setSearchResults(results);
                setCurrentResultIndex(0);
                scrollToArticle(results[0]);
                message.success(`找到 ${results.length} 条匹配结果`);
            } else {
                message.info('未找到匹配条文');
                setSearchResults([]);
                setCurrentResultIndex(0);
                setHighlightedArticle(null);
                setHighlightKeyword('');
            }
        } catch (error) {
            message.error('搜索失败');
        } finally {
            setSearching(false);
        }
    };

    // 导航到上一个搜索结果
    const goToPrevResult = () => {
        if (searchResults.length === 0) return;
        const newIndex = currentResultIndex > 0 ? currentResultIndex - 1 : searchResults.length - 1;
        setCurrentResultIndex(newIndex);
        scrollToArticle(searchResults[newIndex]);
    };

    // 导航到下一个搜索结果
    const goToNextResult = () => {
        if (searchResults.length === 0) return;
        const newIndex = currentResultIndex < searchResults.length - 1 ? currentResultIndex + 1 : 0;
        setCurrentResultIndex(newIndex);
        scrollToArticle(searchResults[newIndex]);
    };

    const scrollToArticle = (articleNum) => {
        const element = document.getElementById(`article-${articleNum}`);
        if (element) {
            // 使用 scrollIntoView + 偏移，保留头部信息可见
            element.scrollIntoView({ behavior: 'instant', block: 'start' });
            // 向下偏移，让头部仍然可见（头部大约 280px）
            window.scrollBy({ top: -300, behavior: 'instant' });
            setHighlightedArticle(articleNum);
            // 不再自动清除高亮，保持永久高亮以区分搜索结果
        }
    };

    const highlightText = (text, keyword) => {
        if (!keyword) return text;
        try {
            const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const parts = text.split(new RegExp(`(${escapedKeyword})`, 'gi'));
            return parts.map((part, index) =>
                part.toLowerCase() === keyword.toLowerCase() ? (
                    <mark key={index} className="highlight">{part}</mark>
                ) : (part)
            );
        } catch (e) {
            return text;
        }
    };

    if (loading) return (
        <div className="loading-spinner" style={{ minHeight: '60vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
            <div className="spinner"></div>
        </div>
    );
    if (!law) return <div className="empty-state"><p>法规不存在</p></div>;

    return (
        <>
            {/* 覆盖层：在滚动定位完成前遮盖内容 */}
            {targetArticle && !contentReady && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: '#f8fafc',
                    zIndex: 9999,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '16px'
                }}>
                    <div className="spinner"></div>
                    <p style={{ color: '#64748b', fontSize: '14px' }}>正在定位到目标条文...</p>
                </div>
            )}
            <div className="law-detail-page">
                {/* 顶部英雄区 */}
                <section className="detail-hero">
                    <div className="hero-content">
                        {/* 第一行：返回按钮 */}
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginBottom: '0.5rem' }}>
                            {/* 如果从搜索页面进入，显示返回搜索结果按钮 */}
                            {searchParams.get('kw') && (
                                <button
                                    type="button"
                                    style={{
                                        background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                                        color: 'white',
                                        border: 'none',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                        padding: '8px 16px',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontWeight: '600',
                                        boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)'
                                    }}
                                    onClick={() => navigate(`/search?q=${encodeURIComponent(searchParams.get('kw'))}`)}
                                >
                                    <ChevronLeft size={18} /> 返回搜索结果
                                </button>
                            )}
                            <button
                                type="button"
                                style={{
                                    background: 'rgba(255,255,255,0.1)',
                                    color: 'white',
                                    border: 'none',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    padding: '8px 16px',
                                    borderRadius: '8px',
                                    cursor: 'pointer'
                                }}
                                onClick={() => navigate('/laws')}
                            >
                                <ChevronLeft size={18} /> 返回法规库
                            </button>
                        </div>

                        {/* 第二行：标题 + 标签 */}
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '1rem' }}>
                            <h1 className="detail-title" style={{ margin: 0 }}>{law.title}</h1>
                            <span className={`tag ${law.category?.includes('刑事') ? 'tag-criminal' :
                                law.category?.includes('程序') ? 'tag-procedure' : 'tag-admin'
                                }`}>{law.category}</span>
                            <span className={`tag ${(law.status === '现行有效' || law.status === '有效') ? 'tag-active' :
                                law.status === '尚未生效' ? 'tag-pending' :
                                    law.status === '已修订' ? 'tag-revised' :
                                        law.status === '已失效' ? 'tag-expired' : 'tag-active'
                                }`}>
                                {(law.status === '有效') ? '现行有效' : law.status}
                            </span>
                        </div>

                        {law.summary && (
                            <div className={`summary-card ${isSummaryExpanded ? 'expanded' : ''}`}>
                                <div
                                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', marginBottom: isSummaryExpanded ? '10px' : '0' }}
                                    onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
                                >
                                    <div style={{ display: 'flex', gap: '10px', color: '#3b82f6', fontWeight: 'bold', fontSize: '14px', alignItems: 'center' }}>
                                        <Book size={16} /> 修订说明 / 摘要
                                    </div>
                                    <div style={{ color: '#64748b', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                        {isSummaryExpanded ? '收起' : '展开全文'}
                                        {isSummaryExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                    </div>
                                </div>
                                <div className="summary-content">
                                    {law.summary}
                                </div>
                            </div>
                        )}

                        <div className="metadata-bar">
                            <div className="metadata-group">
                                <div className="meta-item">
                                    <span className="meta-label">制定机关</span>
                                    <span className="meta-value">{law.issue_org}</span>
                                </div>
                                <div className="meta-item">
                                    <span className="meta-label">实施日期</span>
                                    <span className="meta-value">{law.effect_date || law.issue_date}</span>
                                </div>
                                <div className="meta-item">
                                    <span className="meta-label">效力层级</span>
                                    <span className="meta-value">{law.level}</span>
                                </div>
                            </div>

                            {/* 搜索框区域 - 核心功能 */}
                            {/* 搜索框区域 - 核心功能 */}
                            <div className="detail-search-box-enhanced">
                                <Search size={20} color={searchResults.length > 0 ? "#cbd5e1" : "#64748b"} />
                                <input
                                    type="text"
                                    className="detail-search-input"
                                    placeholder="在法规中搜索条文或条号..."
                                    onKeyPress={(e) => e.key === 'Enter' && handleSearch(e.target.value)}
                                    onChange={(e) => {
                                        if (!e.target.value.trim()) {
                                            setSearchResults([]);
                                            setCurrentResultIndex(0);
                                            setHighlightedArticle(null);
                                            setHighlightKeyword('');
                                        }
                                    }}
                                />

                                {/* 内嵌式搜索导航 */}
                                {searchResults.length > 0 && (
                                    <>
                                        <div className="search-inline-divider"></div>
                                        <div className="search-inline-info">
                                            <span className="search-counter">
                                                {currentResultIndex + 1} / {searchResults.length}
                                            </span>
                                        </div>
                                        <div className="search-inline-actions">
                                            <button
                                                type="button"
                                                className="search-nav-btn-inline"
                                                onClick={goToPrevResult}
                                            >
                                                <ChevronUp size={16} />
                                            </button>
                                            <button
                                                type="button"
                                                className="search-nav-btn-inline"
                                                onClick={goToNextResult}
                                            >
                                                <ChevronDown size={16} />
                                            </button>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                </section>

                {/* 条文详情区域 */}
                <main className="detail-body">
                    <div className="law-content-card">
                        <div className="articles-container" ref={articlesContainerRef}>
                            {articles.length > 0 ? articles.map((article, index) => {
                                const prevChapter = index > 0 ? articles[index - 1].chapter : '';
                                const showChapterHeader = article.chapter && article.chapter !== prevChapter;

                                const chapterParts = article.chapter ? article.chapter.split(' / ') : [];
                                const prevParts = prevChapter ? prevChapter.split(' / ') : [];

                                return (
                                    <div key={article.article_num}>
                                        {showChapterHeader && (
                                            <div className="chapter-header-container">
                                                <div className="chapter-title-box">
                                                    {chapterParts.map((part, partIndex) => {
                                                        const prevPart = prevParts[partIndex] || '';
                                                        const isNewPart = part !== prevPart;
                                                        if (!isNewPart && partIndex < prevParts.length) return null;

                                                        const isPartLevel = part.includes('编') || part === '附则' || part === '总则' || part === '分则';
                                                        const isChapterLevel = part.includes('章');

                                                        if (isPartLevel) return <div key={partIndex} className="part-title">{part}</div>;
                                                        if (isChapterLevel) return <div key={partIndex} className="chapter-title">{part}</div>;
                                                        return <div key={partIndex} className="section-title">{part}</div>;
                                                    })}
                                                </div>
                                            </div>
                                        )}

                                        <div
                                            id={`article-${article.article_num}`}
                                            className={`article-item ${highlightedArticle === article.article_num ? 'highlighted' : ''}`}
                                        >
                                            <div className="article-header">
                                                <span className="article-num">{article.article_display}</span>
                                                {article.chapter && (
                                                    <span className="tag" style={{ background: '#f8fafc', color: '#94a3b8', fontSize: '11px', border: '1px solid #e2e8f0' }}>
                                                        {article.chapter}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="article-content">
                                                {highlightText(article.content, highlightKeyword)}
                                            </div>
                                        </div>
                                    </div>
                                );
                            }) : (
                                <div className="empty-state">
                                    <Book size={48} style={{ opacity: 0.1, marginBottom: '1rem' }} />
                                    <p>未找到条文内容</p>
                                </div>
                            )}
                        </div>
                    </div>
                </main>

                {/* 返回顶部 */}
                <div className="back-to-top" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
                    <ChevronUp size={24} />
                </div>
            </div>
        </>
    );
}
