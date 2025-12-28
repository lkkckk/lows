import { Shield, Book, Search as SearchIcon, FileText } from 'lucide-react';
import LawsList from './pages/LawsList';
import LawDetail from './pages/LawDetail';
import GlobalSearch from './pages/GlobalSearch';
import TemplatesList from './pages/TemplatesList';
import TemplateEditor from './pages/TemplateEditor';
import LawEditor from './pages/LawEditor';
import Admin from './pages/Admin';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import './App.css';

// 顶部导航栏组件
const Navbar = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const getActiveTab = () => {
        if (location.pathname.startsWith('/search')) return 'search';
        if (location.pathname.startsWith('/templates')) return 'templates';
        return 'laws';
    };

    const activeTab = getActiveTab();

    const handleTabChange = (tab) => {
        const routes = {
            'laws': '/laws',
            'search': '/search',
            'templates': '/templates'
        };
        navigate(routes[tab]);
    };

    return (
        <header className="navbar">
            <div className="navbar-content">
                {/* Logo 区 */}
                <div className="navbar-logo">
                    <img src="/logo.png" alt="北流公安" className="logo-image" />
                    <div className="navbar-title">
                        <h1>法律文库检索平台</h1>
                        <p className="navbar-subtitle">Legal Library Search Platform</p>
                    </div>
                </div>

                {/* 导航菜单 */}
                <nav className="navbar-nav">
                    {[
                        { id: 'laws', label: '法规库', icon: Book },
                        { id: 'search', label: '全文检索', icon: SearchIcon },
                        { id: 'templates', label: '文书模板', icon: FileText },
                    ].map((item) => (
                        <button
                            key={item.id}
                            onClick={() => handleTabChange(item.id)}
                            className={`nav-button ${activeTab === item.id ? 'active' : ''}`}
                        >
                            <item.icon size={16} />
                            {item.label}
                        </button>
                    ))}
                </nav>

                {/* 用户/系统状态 - 已移动或隐藏，保持布局整洁 */}
                {/* <div className="navbar-status"></div> */}
            </div>
        </header>
    );
};

// Footer组件
const Footer = () => (
    <footer className="footer">
        <div className="container">
            <p>&copy; 2025 北流市公安局 | 内网版本 V1.0</p>
            <p className="footer-disclaimer">本系统数据来源于公开渠道，仅供执法参考，请以正式文本为准</p>
        </div>
    </footer>
);

// 主布局（带导航栏和页脚）
const MainLayout = ({ children }) => (
    <>
        <Navbar />
        <main style={{ flex: 1 }}>{children}</main>
        <Footer />
    </>
);

function App() {
    return (
        <BrowserRouter>
            <Routes>
                {/* 管理页面 - 独立布局，不显示导航栏 */}
                <Route path="/admin" element={<Admin />} />

                {/* 主站页面 - 带导航栏和页脚 */}
                <Route path="/*" element={
                    <MainLayout>
                        <Routes>
                            <Route path="/" element={<Navigate to="/laws" replace />} />
                            <Route path="laws" element={<LawsList />} />
                            <Route path="laws/create" element={<LawEditor />} />
                            <Route path="laws/:lawId" element={<LawDetail />} />
                            <Route path="search" element={<GlobalSearch />} />
                            <Route path="templates" element={<TemplatesList />} />
                            <Route path="templates/:templateId" element={<TemplateEditor />} />
                        </Routes>
                    </MainLayout>
                } />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
