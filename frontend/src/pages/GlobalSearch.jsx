import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { message } from 'antd';
import { Search, Book, ChevronRight, Zap, Filter, Check, X } from 'lucide-react';
import { searchGlobal } from '../services/api';
import './GlobalSearch.css';

// sessionStorage key
const STORAGE_KEY = 'global_search_state';

// 高亮关键字 - 缓存正则提升性能
const createHighlighter = (keyword) => {
    if (!keyword) return null;
    try {
        const escapedKw = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return new RegExp(`(${escapedKw})`, 'gi');
    } catch {
        return null;
    }
};

const highlightKeyword = (text, regex) => {
    if (!regex || !text) return text;
    try {
        const parts = text.split(regex);
        return parts.map((part, i) =>
            regex.test(part) ? <mark key={i} className="search-highlight">{part}</mark> : part
        );
    } catch {
        return text;
    }
};

// 从 sessionStorage 加载状态
const loadSearchState = () => {
    try {
        const saved = sessionStorage.getItem(STORAGE_KEY);
        if (saved) {
            return JSON.parse(saved);
        }
    } catch (e) {
        console.warn('加载搜索状态失败:', e);
    }
    return null;
};

// 保存状态到 sessionStorage
const saveSearchState = (state) => {
    try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
        console.warn('保存搜索状态失败:', e);
    }
};

export default function GlobalSearch() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    // 尝试从 sessionStorage 恢复状态
    const savedState = useMemo(() => loadSearchState(), []);
    const urlQuery = searchParams.get('q') || '';

    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState(savedState?.results || []);
    const [allResults, setAllResults] = useState(savedState?.allResults || []); // 保存所有结果用于筛选
    const [pagination, setPagination] = useState(savedState?.pagination || {
        current: 1,
        pageSize: 20,
        total: 0,
    });
    const [searchQuery, setSearchQuery] = useState(urlQuery || savedState?.searchQuery || '');

    // 引用结果列表容器，用于翻页回顶
    const resultsRef = useRef(null);

    // 法规筛选相关状态
    const [lawsList, setLawsList] = useState(savedState?.lawsList || []); // 包含关键字的法规列表
    const [selectedLaw, setSelectedLaw] = useState(savedState?.selectedLaw || null); // 当前选中的法规

    // 分类筛选相关状态
    const [categoryList, setCategoryList] = useState(savedState?.categoryList || []); // 分类列表
    const [selectedCategory, setSelectedCategory] = useState(savedState?.selectedCategory || null); // 当前选中的分类

    // 缓存高亮正则表达式，避免每次渲染重复编译
    const highlightRegex = useMemo(() => createHighlighter(searchQuery), [searchQuery]);

    // 保存状态到 sessionStorage
    useEffect(() => {
        if (allResults.length > 0 || searchQuery) {
            saveSearchState({
                results,
                allResults,
                pagination,
                searchQuery,
                lawsList,
                selectedLaw,
                categoryList,
                selectedCategory
            });
        }
    }, [results, allResults, pagination, searchQuery, lawsList, selectedLaw, categoryList, selectedCategory]);

    useEffect(() => {
        const query = searchParams.get('q');
        // 只在 URL 参数变化时触发搜索（排除从缓存恢复的情况）
        if (query && query !== savedState?.searchQuery) {
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
        setSelectedCategory(null); // 重置分类筛选
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
            // 按分类分组
            const categoryMap = new Map();

            data.forEach(item => {
                // 法规统计
                if (!lawsMap.has(item.law_id)) {
                    lawsMap.set(item.law_id, {
                        law_id: item.law_id,
                        law_title: item.law_title,
                        law_category: item.law_category || '未分类',
                        count: 0
                    });
                }
                lawsMap.get(item.law_id).count++;

                // 分类统计
                const category = item.law_category || '未分类';
                if (!categoryMap.has(category)) {
                    categoryMap.set(category, { name: category, count: 0 });
                }
                categoryMap.get(category).count++;
            });

            // 转换为数组并按匹配数量排序
            const lawsArray = Array.from(lawsMap.values()).sort((a, b) => b.count - a.count);
            setLawsList(lawsArray);

            // 分类排序（按数量降序）
            const categoryArray = Array.from(categoryMap.values()).sort((a, b) => b.count - a.count);
            setCategoryList(categoryArray);

            // 显示所有结果（分页）
            updateDisplayResults(data, null, null, 1);
        } catch (error) {
            message.error('搜索失败');
        } finally {
            setLoading(false);
        }
    };

    // 根据筛选条件更新显示的结果
    const updateDisplayResults = (data, categoryName, lawId, page) => {
        let filtered = data;

        // 先按分类筛选
        if (categoryName) {
            filtered = filtered.filter(item => (item.law_category || '未分类') === categoryName);
        }

        // 再按法规筛选
        if (lawId) {
            filtered = filtered.filter(item => item.law_id === lawId);
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

        // 更新法规列表（根据分类筛选后的数据）
        if (categoryName && !lawId) {
            const lawsMap = new Map();
            filtered.forEach(item => {
                if (!lawsMap.has(item.law_id)) {
                    lawsMap.set(item.law_id, {
                        law_id: item.law_id,
                        law_title: item.law_title,
                        law_category: item.law_category || '未分类',
                        count: 0
                    });
                }
                lawsMap.get(item.law_id).count++;
            });
            const lawsArray = Array.from(lawsMap.values()).sort((a, b) => b.count - a.count);
            setLawsList(lawsArray);
        }
    };

    // 选择分类筛选
    const handleCategoryFilter = (category) => {
        if (selectedCategory?.name === category.name) {
            // 取消筛选
            setSelectedCategory(null);
            setSelectedLaw(null);
            // 重新计算法规列表
            const lawsMap = new Map();
            allResults.forEach(item => {
                if (!lawsMap.has(item.law_id)) {
                    lawsMap.set(item.law_id, {
                        law_id: item.law_id,
                        law_title: item.law_title,
                        law_category: item.law_category || '未分类',
                        count: 0
                    });
                }
                lawsMap.get(item.law_id).count++;
            });
            setLawsList(Array.from(lawsMap.values()).sort((a, b) => b.count - a.count));
            updateDisplayResults(allResults, null, null, 1);
        } else {
            setSelectedCategory(category);
            setSelectedLaw(null); // 切换分类时清除法规筛选
            updateDisplayResults(allResults, category.name, null, 1);
        }
    };

    // 选择法规筛选
    const handleLawFilter = (law) => {
        if (selectedLaw?.law_id === law.law_id) {
            // 取消筛选
            setSelectedLaw(null);
            updateDisplayResults(allResults, selectedCategory?.name, null, 1);
        } else {
            setSelectedLaw(law);
            updateDisplayResults(allResults, selectedCategory?.name, law.law_id, 1);
        }
    };

    // 清除所有筛选
    const clearFilter = () => {
        setSelectedLaw(null);
        setSelectedCategory(null);
        // 重新计算法规列表
        const lawsMap = new Map();
        allResults.forEach(item => {
            if (!lawsMap.has(item.law_id)) {
                lawsMap.set(item.law_id, {
                    law_id: item.law_id,
                    law_title: item.law_title,
                    law_category: item.law_category || '未分类',
                    count: 0
                });
            }
            lawsMap.get(item.law_id).count++;
        });
        setLawsList(Array.from(lawsMap.values()).sort((a, b) => b.count - a.count));
        updateDisplayResults(allResults, null, null, 1);
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
                        支持对所有已收录的法律法规进行全文检索，结果精确到具体条文，需要注意，如已收录的库中没有相应关键词，则无法检索到，如“刑事拘留”等，因为没有任何条文会出现“刑事拘留”这个词组。<br />
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
                        {/* 左侧：搜索结果 */}
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
                                            <div className="result-card-title-group">
                                                <h4>{result.law_title}</h4>
                                                {result.law_category && (
                                                    <span className="category-tag">{result.law_category}</span>
                                                )}
                                            </div>
                                            {result.article_display && (
                                                <span className="result-article-tag">{result.article_display}</span>
                                            )}
                                        </div>
                                        <div className="result-card-content">
                                            {highlightKeyword(result.content, highlightRegex)}
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
                                        onClick={() => updateDisplayResults(allResults, selectedCategory?.name, selectedLaw?.law_id, pagination.current - 1)}
                                    >
                                        上一页
                                    </button>
                                    <div className="pagination-info">
                                        第 {pagination.current} / {Math.ceil(pagination.total / pagination.pageSize)} 页
                                    </div>
                                    <button
                                        className="pagination-button"
                                        disabled={pagination.current >= Math.ceil(pagination.total / pagination.pageSize)}
                                        onClick={() => updateDisplayResults(allResults, selectedCategory?.name, selectedLaw?.law_id, pagination.current + 1)}
                                    >
                                        下一页
                                    </button>
                                </div>
                            )}
                        </main>

                        {/* 右侧：筛选列表 */}
                        <aside className="law-filter-sidebar">
                            {/* 分类筛选 */}
                            <div className="filter-section">
                                <div className="filter-header">
                                    <Filter size={18} />
                                    <span>按分类筛选</span>
                                    {(selectedCategory || selectedLaw) && (
                                        <button className="clear-filter-btn" onClick={clearFilter}>
                                            <X size={14} /> 清除
                                        </button>
                                    )}
                                </div>
                                <div className="category-filter-list">
                                    {categoryList.map(cat => (
                                        <button
                                            key={cat.name}
                                            className={`category-filter-item ${selectedCategory?.name === cat.name ? 'active' : ''}`}
                                            onClick={() => handleCategoryFilter(cat)}
                                        >
                                            <span className="category-name">{cat.name}</span>
                                            <span className="category-count">{cat.count}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* 法规筛选 */}
                            <div className="filter-section">
                                <div className="filter-header">
                                    <Book size={18} />
                                    <span>按法规筛选</span>
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
                            </div>
                        </aside>
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
