
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        host: '0.0.0.0',
        port: 3000,
        proxy: {
            '/api': {
                target: process.env.VITE_API_TARGET || 'http://localhost:8000',
                changeOrigin: true,
                autoRewrite: true,
                followRedirects: true,
                rewrite: (path) => path.replace(/^\/api/, '') || '/',
                configure: (proxy) => {
                    proxy.on('error', (err) => {
                        console.error('[PROXY ERROR]', err.message);
                    });
                    proxy.on('proxyReq', (_proxyReq, req) => {
                        console.log('[PROXY →]', req.method, req.url);
                    });
                    proxy.on('proxyRes', (proxyRes, req) => {
                        console.log('[PROXY ←]', proxyRes.statusCode, req.url);
                    });
                },
            },
        }
    }
})
