import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { message } from 'antd';
import { Search, Book, ChevronRight, Zap, Filter, Check, X } from 'lucide-react';
import { searchGlobal } from '../services/api';
import './GlobalSearch.css';

// 高亮关键字
const highlightKeyword = (text, keyword) => {
    if (!keyword || !text) return text;
    try {
        const escapedKw = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedKw})`, 'gi');
        const parts = text.split(regex);
        return parts.map((part, i) =>
            regex.test(part) ? <mark key={i} className="search-highlight">{part}</mark> : part
        );
    } catch {
        return text;
    }
};

export default function GlobalSearch() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState([]);
    const [allResults, setAllResults] = useState([]); // 保存所有结果用于筛选
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 20,
        total: 0,
    });
    const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');

    // 引用结果列表容器，用于翻页回顶
    const resultsRef = useRef(null);

    // 法规筛选相关状态
    const [lawsList, setLawsList] = useState([]); // 包含关键字的法规列表
    const [selectedLaw, setSelectedLaw] = useState(null); // 当前选中的法规

    useEffect(() => {
        const query = searchParams.get('q');
        if (query) {
            setSearchQuery(query);
            handleSearch(query, 1);
        }
    }, [searchParams]);

    const handleSearch = async (value, page = 1) => {
        if (!value.trim()) {
            message.warning('请输入搜索关键字');
            return;
        }

        // 更新 URL，使浏览器返回时能恢复搜索状态
        window.history.replaceState(null, '', `/search?q=${encodeURIComponent(value)}`);

        setLoading(true);
        setSelectedLaw(null); // 重置法规筛选
        try {
            const response = await searchGlobal({
                query: value,
                page: 1,
                page_size: 500, // 增加到500以覆盖更多结果
            });
            const data = response.data || [];
            setAllResults(data);

            // 按法规分组，统计每部法规的匹配数量
            const lawsMap = new Map();
            data.forEach(item => {
                if (!lawsMap.has(item.law_id)) {
                    lawsMap.set(item.law_id, {
                        law_id: item.law_id,
                        law_title: item.law_title,
                        count: 0
                    });
                }
                lawsMap.get(item.law_id).count++;
            });

            // 转换为数组并按匹配数量排序
            const lawsArray = Array.from(lawsMap.values()).sort((a, b) => b.count - a.count);
            setLawsList(lawsArray);

            // 显示所有结果（分页）
            updateDisplayResults(data, null, page);
        } catch (error) {
            message.error('搜索失败');
        } finally {
            setLoading(false);
        }
    };

    // 根据筛选条件更新显示的结果
    const updateDisplayResults = (data, lawId, page) => {
        let filtered = data;
        if (lawId) {
            filtered = data.filter(item => item.law_id === lawId);
        }

        const pageSize = 20;
        const start = (page - 1) * pageSize;
        const end = start + pageSize;

        setResults(filtered.slice(start, end));
        setPagination({
            current: page,
            pageSize: pageSize,
            total: filtered.length,
        });

        // 翻页或筛选后滚动回顶部
        if (resultsRef.current) {
            resultsRef.current.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    // 选择法规筛选
    const handleLawFilter = (law) => {
        if (selectedLaw?.law_id === law.law_id) {
            // 取消筛选
            setSelectedLaw(null);
            updateDisplayResults(allResults, null, 1);
        } else {
            setSelectedLaw(law);
            updateDisplayResults(allResults, law.law_id, 1);
        }
    };

    // 清除筛选
    const clearFilter = () => {
        setSelectedLaw(null);
        updateDisplayResults(allResults, null, 1);
    };

    return (
        <div className="global-search-page">
            {/* 搜索区 - 发光渐变设计 */}
            <section className="search-hero">
                <div className="search-hero-content">
                    <div className="search-hero-header">
                        <Zap size={36} color="#fbbf24" />
                        <h1>全库全文检索</h1>
                    </div>
                    <p className="search-hero-subtitle">
                        支持对所有已收录的法律法规进行全文检索，结果精确到具体条文，需要注意，如已收录的库中没有相应关键字，则无法检索到，如“刑事拘留”等，因为没有任何条文会出现“刑事拘留”这个词组。<br />
                        <br />
                    </p>

                    {/* 发光搜索框 */}
                    <div className="global-search-box">
                        <Search size={24} className="search-box-icon" />
                        <input
                            type="text"
                            className="global-search-input"
                            placeholder="输入关键字，如：拘留、传唤、取保候审..."
                            value={searchQuery}
                            onChange={(e) => {
                                const val = e.target.value;
                                setSearchQuery(val);
                                if (!val.trim()) {
                                    // 清空时重置所有状态
                                    setAllResults([]);
                                    setResults([]);
                                    setLawsList([]);
                                    setSelectedLaw(null);
                                    setPagination({ ...pagination, total: 0, current: 1 });
                                    // 同步更新 URL
                                    window.history.replaceState(null, '', '/search');
                                }
                            }}
                            onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchQuery, 1)}
                            autoFocus
                        />
                        <button
                            className="global-search-btn"
                            onClick={() => handleSearch(searchQuery, 1)}
                        >
                            搜索
                        </button>
                    </div>
                </div>
            </section>

            {/* 主内容区 */}
            <div className="search-main">
                {loading ? (
                    <div className="loading-spinner"><div className="spinner"></div></div>
                ) : allResults.length > 0 ? (
                    <div className="search-layout">
                        {/* 左侧：法规筛选列表 */}
                        <aside className="law-filter-sidebar">
                            <div className="filter-header">
                                <Filter size={18} />
                                <span>按法规筛选</span>
                                {selectedLaw && (
                                    <button className="clear-filter-btn" onClick={clearFilter}>
                                        <X size={14} /> 清除
                                    </button>
                                )}
                            </div>
                            <div className="filter-list">
                                {lawsList.map(law => (
                                    <button
                                        key={law.law_id}
                                        className={`filter-item ${selectedLaw?.law_id === law.law_id ? 'active' : ''}`}
                                        onClick={() => handleLawFilter(law)}
                                    >
                                        <span className="filter-item-title">{law.law_title}</span>
                                        <span className="filter-item-count">{law.count}</span>
                                        {selectedLaw?.law_id === law.law_id && <Check size={14} className="filter-check" />}
                                    </button>
                                ))}
                            </div>
                        </aside>

                        {/* 右侧：搜索结果 */}
                        <main className="search-results" ref={resultsRef}>
                            <header className="results-header">
                                <h3>
                                    {selectedLaw ? (
                                        <>在「{selectedLaw.law_title}」中找到 <strong>{pagination.total}</strong> 条匹配</>
                                    ) : (
                                        <>共找到 <strong>{pagination.total}</strong> 条相关条文</>
                                    )}
                                </h3>
                            </header>

                            <div className="results-list">
                                {results.map((result, index) => (
                                    <div
                                        key={`${result.law_id}-${result.article_num}-${index}`}
                                        className="result-card"
                                        onClick={() => navigate(`/laws/${result.law_id}?article=${result.article_num}&kw=${searchQuery}`)}
                                    >
                                        <div className="result-card-header">
                                            <h4>{result.law_title}</h4>
                                            {result.article_display && (
                                                <span className="result-article-tag">{result.article_display}</span>
                                            )}
                                        </div>
                                        <div className="result-card-content">
                                            {highlightKeyword(result.content, searchQuery)}
                                        </div>
                                        <div className="result-card-footer">
                                            <span className="view-detail">
                                                查看完整条文 <ChevronRight size={14} />
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {pagination.total > pagination.pageSize && (
                                <div className="pagination">
                                    <button
                                        className="pagination-button"
                                        disabled={pagination.current === 1}
                                        onClick={() => updateDisplayResults(allResults, selectedLaw?.law_id, pagination.current - 1)}
                                    >
                                        上一页
                                    </button>
                                    <div className="pagination-info">
                                        第 {pagination.current} / {Math.ceil(pagination.total / pagination.pageSize)} 页
                                    </div>
                                    <button
                                        className="pagination-button"
                                        disabled={pagination.current >= Math.ceil(pagination.total / pagination.pageSize)}
                                        onClick={() => updateDisplayResults(allResults, selectedLaw?.law_id, pagination.current + 1)}
                                    >
                                        下一页
                                    </button>
                                </div>
                            )}
                        </main>
                    </div>
                ) : searchQuery ? (
                    <div className="empty-state">
                        <Search size={48} className="empty-icon" />
                        <p>未找到相关结果</p>
                    </div>
                ) : (
                    <div className="empty-state">
                        <Book size={48} className="empty-icon" />
                        <p>输入关键字开始搜索</p>
                    </div>
                )}
            </div>
        </div>
    );
}
