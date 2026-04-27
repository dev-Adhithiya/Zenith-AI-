import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/',
  server: {
    port: 3000,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/calendar': 'http://localhost:8000',
      '/gmail': 'http://localhost:8000',
      '/tasks': 'http://localhost:8000',
      '/notes': 'http://localhost:8000',
      '/sessions': 'http://localhost:8000',
      '/settings': 'http://localhost:8000',
      '/preferences': 'http://localhost:8000',
      '/insights': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
