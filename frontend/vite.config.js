import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import legacy from '@vitejs/plugin-legacy'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        react(),
        // 支持低版本浏览器
        legacy({
            targets: ['defaults', 'not IE 11', 'Chrome >= 60', 'Firefox >= 60', 'Safari >= 12', 'Edge >= 79'],
            additionalLegacyPolyfills: ['regenerator-runtime/runtime'],
            renderLegacyChunks: true,
            modernPolyfills: true
        })
    ],
    server: {
        port: process.env.VITE_PORT || 6011,
        proxy: {
            '/api': {
                target: `http://${process.env.VITE_BACKEND_HOST || 'localhost'}:${process.env.VITE_BACKEND_PORT || 4008}`,
                changeOrigin: true,
            }
        }
    },
    build: {
        // 兼容旧浏览器的构建目标
        target: ['es2015', 'chrome60', 'firefox60', 'safari12', 'edge79'],
        // CSS 目标
        cssTarget: ['chrome60', 'firefox60', 'safari12', 'edge79']
    }
})
