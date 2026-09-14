import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  base: '/geo/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/geo/api': {
        target: 'http://10.17.197.113:8000/',
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/geo/, '')
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
