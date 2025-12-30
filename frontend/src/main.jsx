import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import { StyleProvider, legacyLogicalPropertiesTransformer } from '@ant-design/cssinjs';
import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import App from './App.jsx';
import './index.css';
import './App.css';

dayjs.locale('zh-cn');

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <StyleProvider
            hashPriority="high"
            transformers={[legacyLogicalPropertiesTransformer]}
        >
            <ConfigProvider locale={zhCN}>
                <App />
            </ConfigProvider>
        </StyleProvider>
    </React.StrictMode>
);
