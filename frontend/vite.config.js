import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// UpajMitra frontend dev server.
// Proxies /api/* to the FastAPI backend at localhost:8000 so the frontend
// can just call fetch('/api/predict') without worrying about CORS/ports.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
