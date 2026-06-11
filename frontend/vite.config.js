import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const proxyTarget = {
  target: 'http://127.0.0.1:8000',
  changeOrigin: true,
  timeout: 120000,
  proxyTimeout: 120000,
}

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': proxyTarget,
      '/health': proxyTarget,
    },
  },
  preview: {
    proxy: {
      '/api': proxyTarget,
      '/health': proxyTarget,
    },
  },
})
