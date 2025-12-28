import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, ChevronLeft, ArrowRight } from 'lucide-react';
import { message } from 'antd';
import { adminLogin } from '../services/api';
import '../styles/Admin.css'; // 复用部分管理后台样式

export default function AdminLogin() {
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        if (!password) return message.warning('请输入管理密码');

        setLoading(true);
        try {
            const response = await adminLogin(password);
            if (response.success) {
                localStorage.setItem('adminToken', response.token);
                message.success('验证成功');
                navigate('/admin');
            }
        } catch (error) {
            message.error(error.response?.data?.detail || '验证失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="admin-login-container">
            <div className="login-card">
                <button className="login-back-btn" onClick={() => navigate('/')}>
                    <ChevronLeft size={20} />
                    返回主站
                </button>

                <div className="login-header">
                    <div className="login-icon">
                        <Shield size={32} />
                    </div>
                    <h1>管理系统身份验证</h1>
                    <p>请输入超级管理员密码以继续</p>
                </div>

                <form onSubmit={handleLogin} className="login-form">
                    <div className="input-group">
                        <Lock className="input-icon" size={20} />
                        <input
                            type="password"
                            placeholder="管理密码"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            autoFocus
                        />
                    </div>

                    <button type="submit" className="login-submit-btn" disabled={loading}>
                        {loading ? '正在验证...' : '进入管理后台'}
                        {!loading && <ArrowRight size={18} />}
                    </button>
                </form>

                <div className="login-footer">
                    <p>法律文库检索平台 · 内部管理专用</p>
                </div>
            </div>
        </div>
    );
}
