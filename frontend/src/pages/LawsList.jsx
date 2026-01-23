import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import {
    Search,
    ChevronRight,
    Shield,
    Filter,
    Zap,
    Book,
    X,
    TrendingUp,
} from 'lucide-react';
import { getLawsList, getLawCategories, getPopupSettings, getTodayViews, getTotalViews } from '../services/api';

// 法规卡片组件
const LawCard = ({ law, onClick }) => (
    <div className="law-card" onClick={() => onClick(law)}>
        <div className="card-header">
            <div className="card-tags">
                <span className={`tag ${law.category?.includes('刑事') ? 'tag-criminal' :
                    law.category?.includes('程序') ? 'tag-procedure' : 'tag-admin'
                    }`}>
                    {law.category || '未分类'}
                </span>
                {/* 效力状态标签 */}
                {(law.status === '现行有效' || law.status === '有效') && (
                    <span className="tag tag-active">现行有效</span>
                )}
                {law.status === '尚未生效' && (
                    <span className="tag tag-pending">尚未生效</span>
                )}
                {law.status === '已修订' && (
                    <span className="tag tag-revised">已修订</span>
                )}
                {law.status === '已废止' && (
                    <span className="tag tag-expired">已废止</span>
                )}
            </div>
            {/* 移除收藏按钮 */}
        </div>

        <h3 className="card-title">{law.title}</h3>

        <p className="card-description">
            {law.summary || '法规内容详情，请点击查看...'}
        </p>

        <div className="card-footer">
            <div className="footer-meta">
                <span>{law.issue_org || '相关部门'}</span>
                <span>•</span>
                <span>{law.effect_date || law.issue_date} 实施</span>
            </div>
            {/* 移除查阅详情按钮 */}
        </div>
    </div>
);

export default function LawsList() {
    const navigate = useNavigate();

    const [laws, setLaws] = useState([]);
    const [loading, setLoading] = useState(false);
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 9,
        total: 0,
    });

    const [filterText, setFilterText] = useState('');
    const [activeCategory, setActiveCategory] = useState('全部');
    const [categories, setCategories] = useState(['全部']);
    const [titleFilter, setTitleFilter] = useState(''); // 标题搜索

    // 首页弹窗状态
    const [showPopup, setShowPopup] = useState(false);
    const [popupData, setPopupData] = useState({ title: '', content: '' });

    // 网站数据状态
    const [todayViews, setTodayViews] = useState(0);
    const [totalViews, setTotalViews] = useState(0);

    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const response = await getLawCategories();
                if (response.success) {
                    // 直接使用后端返回的分类名称，不再进行特殊映射
                    setCategories(['全部', ...(response.data || [])]);
                }
            } catch (error) {
                console.error('加载分类失败:', error);
            }
        };
        fetchCategories();

        // 检查首页弹窗设置
        const checkPopup = async () => {
            try {
                const popup = await getPopupSettings();
                if (popup.enabled && popup.title) {
                    // 检查本次会话是否已关闭过弹窗
                    const dismissed = sessionStorage.getItem('popupDismissed');
                    if (!dismissed) {
                        setPopupData({ title: popup.title, content: popup.content });
                        setShowPopup(true);
                    }
                }
            } catch (error) {
                console.error('加载弹窗设置失败:', error);
            }
        };
        checkPopup();

        // 加载网站统计数据
        const fetchStats = async () => {
            try {
                const [todayRes, totalRes] = await Promise.all([
                    getTodayViews(),
                    getTotalViews()
                ]);
                if (todayRes.success) setTodayViews(todayRes.data?.today_views || 0);
                if (totalRes.success) setTotalViews(totalRes.data?.total_views || 0);
            } catch (error) {
                console.error('加载网站数据失败:', error);
            }
        };
        fetchStats();
    }, []);

    useEffect(() => {
        // 翻页时平滑滚动到顶部
        window.scrollTo({ top: 0, behavior: 'smooth' });

        const fetchLaws = async () => {
            setLoading(true);
            try {
                const params = {
                    page: pagination.current,
                    page_size: pagination.pageSize,
                };
                if (activeCategory !== '全部') {
                    params.category = activeCategory;
                }
                if (titleFilter) {
                    params.title = titleFilter;
                }
                const response = await getLawsList(params);
                if (response.success) {
                    setLaws(response.data || []);
                    setPagination(prev => ({ ...prev, total: response.pagination?.total || 0 }));
                }
            } catch (error) {
                message.error('加载法规列表失败');
            } finally {
                setLoading(false);
            }
        };

        // 简单的防抖：如果是有标题搜索，延迟 300ms 执行
        if (titleFilter) {
            const timer = setTimeout(fetchLaws, 300);
            return () => clearTimeout(timer);
        } else {
            fetchLaws();
        }
    }, [pagination.current, activeCategory, titleFilter, pagination.pageSize]);

    const handleSearch = () => {
        if (filterText.trim()) {
            navigate(`/search?q=${encodeURIComponent(filterText)}`);
        }
    };

    const handleClosePopup = () => {
        setShowPopup(false);
        sessionStorage.setItem('popupDismissed', 'true');
    };

    return (
        <div style={{ paddingBottom: '3rem' }}>
            {/* 首页弹窗 */}
            {showPopup && (
                <div className="homepage-popup-overlay" onClick={handleClosePopup}>
                    <div className="homepage-popup" onClick={e => e.stopPropagation()}>
                        <button className="popup-close-btn" onClick={handleClosePopup}>
                            <X size={20} />
                        </button>
                        <h2 className="popup-title">{popupData.title}</h2>
                        <div className="popup-content">
                            {popupData.content.split('\n').map((paragraph, idx) => (
                                <p key={idx}>{paragraph.trim() ? `　　${paragraph}` : ''}</p>
                            ))}
                        </div>
                        <button className="popup-confirm-btn" onClick={handleClosePopup}>
                            关闭
                        </button>
                    </div>
                </div>
            )}

            <section className="hero-section">
                <div className="container">
                    <h2 className="hero-title">精准执法，有法可依</h2>
                </div>
            </section>

            {/* 主内容区 */}
            <div className="main-content">
                <div className="content-card">
                    {/* 侧边栏 */}
                    <aside className="sidebar">
                        <div className="sidebar-title">
                            <Filter size={18} />
                            <span>法规分类</span>
                        </div>
                        <div className="category-list">
                            {categories.map(cat => (
                                <button
                                    key={cat}
                                    className={`category-button ${activeCategory === cat ? 'active' : ''}`}
                                    onClick={() => { setActiveCategory(cat); setPagination(p => ({ ...p, current: 1 })); }}
                                >
                                    {cat}
                                </button>
                            ))}
                        </div>
                        <div className="tools-section">
                            <div className="tools-title">常用工具</div>
                            <button className="tool-button" onClick={() => navigate('/search')}>
                                <Zap size={16} color="#eab308" /> 法条速查
                            </button>
                            <button className="tool-button" onClick={() => navigate('/laws/create')} style={{ marginTop: '0.5rem' }}>
                                <Shield size={16} /> 录入法规
                            </button>
                        </div>

                        <div className="tools-section" style={{ marginTop: '1.5rem' }}>
                            <div className="tools-title">网站数据</div>
                            <div style={{
                                background: '#f8fafc',
                                borderRadius: '8px',
                                padding: '12px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '12px',
                                border: '1px solid #e2e8f0'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#64748b', fontSize: '13px' }}>
                                        <div style={{
                                            background: '#dbeafe',
                                            color: '#2563eb',
                                            padding: '4px',
                                            borderRadius: '6px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center'
                                        }}>
                                            <Zap size={14} />
                                        </div>
                                        <span>总浏览量</span>
                                    </div>
                                    <span style={{ fontWeight: '600', color: '#1e293b', fontFamily: 'monospace', fontSize: '14px' }}>
                                        {totalViews.toLocaleString()}
                                    </span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#64748b', fontSize: '13px' }}>
                                        <div style={{
                                            background: '#fef3c7',
                                            color: '#d97706',
                                            padding: '4px',
                                            borderRadius: '6px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center'
                                        }}>
                                            <TrendingUp size={14} />
                                        </div>
                                        <span>今日浏览</span>
                                    </div>
                                    <span style={{ fontWeight: '600', color: '#1e293b', fontFamily: 'monospace', fontSize: '14px' }}>
                                        {todayViews.toLocaleString()}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </aside>

                    {/* 列表区 */}
                    <main className="main-section">
                        <header className="section-header" style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', gap: '16px', padding: '8px 0', marginBottom: '8px' }}>
                            <h3 className="section-title" style={{ fontSize: '16px', margin: 0, color: '#1e293b', fontWeight: 600 }}>
                                {activeCategory} <span className="section-count" style={{ color: '#1e293b' }}>({pagination.total})</span>
                            </h3>
                            {/* 标题搜索框 */}
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                background: '#f1f5f9',
                                borderRadius: '10px',
                                padding: '8px 16px',
                                border: '1px solid #e2e8f0',
                                transition: 'all 0.2s',
                                minWidth: '320px'
                            }}>
                                <Search size={18} color="#94a3b8" />
                                <input
                                    type="text"
                                    placeholder="输入法规名称进行筛选..."
                                    value={titleFilter}
                                    onChange={(e) => {
                                        setTitleFilter(e.target.value);
                                        setPagination(p => ({ ...p, current: 1 }));
                                    }}
                                    style={{
                                        border: 'none',
                                        background: 'transparent',
                                        outline: 'none',
                                        marginLeft: '10px',
                                        width: '260px',
                                        fontSize: '14px',
                                        color: '#334155'
                                    }}
                                />
                                {titleFilter && (
                                    <button
                                        onClick={() => {
                                            setTitleFilter('');
                                            setPagination(p => ({ ...p, current: 1 }));
                                        }}
                                        style={{
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            color: '#94a3b8',
                                            padding: '2px',
                                            display: 'flex'
                                        }}
                                    >
                                        ×
                                    </button>
                                )}
                            </div>
                        </header>

                        {loading ? (
                            <div className="loading-spinner"><div className="spinner"></div></div>
                        ) : laws.length > 0 ? (
                            <>
                                <div className="card-grid">
                                    {laws.map(law => (
                                        <LawCard key={law.law_id} law={law} onClick={(l) => navigate(`/laws/${l.law_id}`)} />
                                    ))}
                                </div>
                                {pagination.total > pagination.pageSize && (
                                    <div className="pagination">
                                        <button
                                            className="pagination-button"
                                            disabled={pagination.current === 1}
                                            onClick={() => setPagination(p => ({ ...p, current: p.current - 1 }))}
                                        >上一页</button>
                                        <div className="pagination-info">第 {pagination.current} / {Math.ceil(pagination.total / pagination.pageSize)} 页</div>
                                        <button
                                            className="pagination-button"
                                            disabled={pagination.current >= Math.ceil(pagination.total / pagination.pageSize)}
                                            onClick={() => setPagination(p => ({ ...p, current: p.current + 1 }))}
                                        >下一页</button>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="empty-state">
                                <Book size={48} className="empty-icon" />
                                <p>未找到相关法规</p>
                            </div>
                        )}
                    </main>
                </div>
            </div>
        </div>
    );
}
