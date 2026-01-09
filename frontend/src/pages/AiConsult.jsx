import { useState, useRef, useEffect } from 'react';
import { message } from 'antd';
import { Send, MessageCircle, Bot, User, Sparkles, Trash2 } from 'lucide-react';
import { sendAiMessage } from '../services/api';
import './AiConsult.css';

// sessionStorage key
const STORAGE_KEY = 'ai_chat_messages';

// 默认欢迎消息
const DEFAULT_MESSAGES = [
    {
        role: 'assistant',
        content: '您好！我是法律AI助手，可以为您解答法律相关问题。请注意，我的回答仅供参考，不构成正式法律意见。有什么我可以帮您的吗？'
    }
];

// 从 sessionStorage 加载消息
const loadMessages = () => {
    try {
        const saved = sessionStorage.getItem(STORAGE_KEY);
        if (saved) {
            const parsed = JSON.parse(saved);
            if (Array.isArray(parsed) && parsed.length > 0) {
                return parsed;
            }
        }
    } catch (e) {
        console.warn('加载对话记录失败:', e);
    }
    return DEFAULT_MESSAGES;
};

// 保存消息到 sessionStorage
const saveMessages = (messages) => {
    try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch (e) {
        console.warn('保存对话记录失败:', e);
    }
};

export default function AiConsult() {
    const [messages, setMessages] = useState(loadMessages);
    const [inputValue, setInputValue] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    // 消息变化时保存到 sessionStorage
    useEffect(() => {
        saveMessages(messages);
    }, [messages]);

    // 滚动到最新消息
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // 发送消息
    const handleSend = async () => {
        const trimmedValue = inputValue.trim();
        if (!trimmedValue) {
            message.warning('请输入问题');
            return;
        }

        // 添加用户消息
        const userMessage = { role: 'user', content: trimmedValue };
        const newMessages = [...messages, userMessage];
        setMessages(newMessages);
        setInputValue('');
        setLoading(true);

        try {
            // 准备历史消息（排除系统消息，只保留最近10轮对话）
            const history = newMessages.slice(-20).map(msg => ({
                role: msg.role,
                content: msg.content
            }));

            const response = await sendAiMessage(trimmedValue, history.slice(0, -1));

            // 添加 AI 回复
            setMessages(prev => [...prev, { role: 'assistant', content: response.reply }]);
        } catch (error) {
            console.error('AI 请求失败:', error);
            message.error(error.response?.data?.detail || 'AI 服务暂时不可用，请稍后重试');
            // 移除用户消息
            setMessages(prev => prev.slice(0, -1));
        } finally {
            setLoading(false);
            inputRef.current?.focus();
        }
    };

    // 清空对话
    const handleClear = () => {
        const clearedMessages = [
            {
                role: 'assistant',
                content: '对话已清空。有什么我可以帮您的吗？'
            }
        ];
        setMessages(clearedMessages);
    };

    // 按键处理
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="ai-consult-page">
            {/* 头部区域 */}
            <section className="ai-hero">
                <div className="ai-hero-content">
                    <div className="ai-hero-header">
                        <Sparkles size={36} color="#a78bfa" />
                        <h1>AI 法律问答</h1>
                    </div>
                    <p className="ai-hero-subtitle">
                        基于 AI 大模型的智能法律助手，可解答法律相关问题，回答仅供参考
                    </p>
                </div>
            </section>

            {/* 聊天区域 */}
            <div className="chat-container">
                {/* 消息列表 */}
                <div className="messages-area">
                    {messages.map((msg, index) => (
                        <div key={index} className={`message ${msg.role}`}>
                            <div className="message-avatar">
                                {msg.role === 'assistant' ? (
                                    <Bot size={24} />
                                ) : (
                                    <User size={24} />
                                )}
                            </div>
                            <div className="message-content">
                                <div className="message-bubble">
                                    {msg.content}
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* 加载动画 */}
                    {loading && (
                        <div className="message assistant">
                            <div className="message-avatar">
                                <Bot size={24} />
                            </div>
                            <div className="message-content">
                                <div className="message-bubble loading">
                                    <span className="typing-dot"></span>
                                    <span className="typing-dot"></span>
                                    <span className="typing-dot"></span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* 输入区域 */}
                <div className="input-area">
                    <button
                        className="clear-btn"
                        onClick={handleClear}
                        title="清空对话"
                    >
                        <Trash2 size={18} />
                    </button>
                    <div className="input-wrapper">
                        <textarea
                            ref={inputRef}
                            className="chat-input"
                            placeholder="输入您的法律问题..."
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={loading}
                            rows={1}
                        />
                        <button
                            className="send-btn"
                            onClick={handleSend}
                            disabled={loading || !inputValue.trim()}
                        >
                            <Send size={20} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
