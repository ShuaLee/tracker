import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Explicit, not just relying on Vite's default: backend/.env's
  // CORS_ALLOWED_ORIGINS / CSRF_TRUSTED_ORIGINS / FRONTEND_URL are all
  // "http://localhost:5173" - changing this port means changing those too.
  server: {
    port: 5173,
  },
})
