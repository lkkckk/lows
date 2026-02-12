import { useState, useRef, useEffect } from 'react';
import { message } from 'antd';
import { Link } from 'react-router-dom';
import { Send, MessageCircle, Bot, User, Sparkles, Trash2, Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react';
import { sendAiMessage, submitAiFeedback } from '../services/api';
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

/**
 * 将 AI 回复中的法律引用（如《治安管理处罚法》第七十二条）转为可点击链接
 * 点击后跳转到全文检索页 /search?q=《xxx》第xx条
 */
function LawLinkText({ content }) {
    if (!content) return null;

    const regex = /《(.+?)》(第[零一二三四五六七八九十百千\d]+条(?:之[一二三四五六七八九十])?)?/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(content)) !== null) {
        if (match.index > lastIndex) {
            parts.push(content.slice(lastIndex, match.index));
        }

        const fullMatch = match[0];
        const url = `/search?q=${encodeURIComponent(fullMatch)}`;

        parts.push(
            <Link key={match.index} to={url} className="law-link" title="点击查看法条详情">
                {fullMatch}
            </Link>
        );

        lastIndex = regex.lastIndex;
    }

    if (lastIndex < content.length) {
        parts.push(content.slice(lastIndex));
    }

    return <>{parts}</>;
}

export default function AiConsult() {
    const [messages, setMessages] = useState(loadMessages);
    const [inputValue, setInputValue] = useState('');
    const [loading, setLoading] = useState(false);
    const [copiedIndex, setCopiedIndex] = useState(null);
    const [feedbackMap, setFeedbackMap] = useState({});  // index -> 'good' | 'bad'
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    // 复制消息内容
    const handleCopy = async (content, index) => {
        try {
            await navigator.clipboard.writeText(content);
            setCopiedIndex(index);
            message.success('已复制到剪贴板');
            setTimeout(() => setCopiedIndex(null), 2000);
        } catch (err) {
            message.error('复制失败');
        }
    };

    // 提交反馈（好/坏答案）
    const handleFeedback = async (index, isGood) => {
        // 找到对应的用户问题（前一条 user 消息）
        let question = '';
        for (let i = index - 1; i >= 0; i--) {
            if (messages[i].role === 'user') {
                question = messages[i].content;
                break;
            }
        }
        if (!question) return;

        const answer = messages[index].content;
        
        try {
            await submitAiFeedback(question, answer, isGood);
            setFeedbackMap(prev => ({ ...prev, [index]: isGood ? 'good' : 'bad' }));
            message.success(isGood ? '已记住此回答，下次将优先使用' : '已标记，下次将重新生成');
        } catch (err) {
            message.error('反馈提交失败');
        }
    };

    // 消息变化时保存到 sessionStorage
    useEffect(() => {
        saveMessages(messages);
    }, [messages]);

    // 滚动到最新消息（仅滚动消息区域，不影响整个页面）
    const isFirstRender = useRef(true);
    const messagesAreaRef = useRef(null);
    const scrollToBottom = () => {
        if (messagesAreaRef.current) {
            messagesAreaRef.current.scrollTop = messagesAreaRef.current.scrollHeight;
        }
    };

    // 页面首次加载时，确保页面从顶部开始
    useEffect(() => {
        window.scrollTo(0, 0);
    }, []);

    useEffect(() => {
        // 首次渲染不自动滚动消息区域
        if (isFirstRender.current) {
            isFirstRender.current = false;
            return;
        }
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
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: response.reply,
                sources: response.sources || []
            }]);
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
                        <Sparkles size={24} color="#a78bfa" />
                        <h1>AI 法律问答</h1>
                    </div>
                    <p className="ai-hero-subtitle">
                        请注意！！！AI对法律法规的理解可能出现偏差，引用时请务必进行核对。
                        <br />请给正确的答案给予好评或在回答有误时给予差评,您的反馈对提升AI的准确性非常重要！
                    </p>
                </div>
            </section>

            {/* 聊天区域 */}
            <div className="chat-container">
                {/* 消息列表 */}
                <div className="messages-area" ref={messagesAreaRef}>
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
                                    <LawLinkText content={msg.content} />
                                </div>
                                <div className="message-actions">
                                    <button
                                        className="copy-btn"
                                        onClick={() => handleCopy(msg.content, index)}
                                        title="复制内容"
                                    >
                                        {copiedIndex === index ? (
                                            <><Check size={14} /> 已复制</>
                                        ) : (
                                            <><Copy size={14} /> 复制</>
                                        )}
                                    </button>
                                    {msg.role === 'assistant' && index > 0 && (
                                        <>
                                            <button
                                                className={`feedback-btn good ${feedbackMap[index] === 'good' ? 'active' : ''}`}
                                                onClick={() => handleFeedback(index, true)}
                                                disabled={!!feedbackMap[index]}
                                                title="回答正确，记住它"
                                            >
                                                <ThumbsUp size={14} />
                                            </button>
                                            <button
                                                className={`feedback-btn bad ${feedbackMap[index] === 'bad' ? 'active' : ''}`}
                                                onClick={() => handleFeedback(index, false)}
                                                disabled={!!feedbackMap[index]}
                                                title="回答有误，下次重新生成"
                                            >
                                                <ThumbsDown size={14} />
                                            </button>
                                        </>
                                    )}
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
                            rows={2}
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
