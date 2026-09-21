import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // host: true deja que los celulares del salón entren por la IP del PC
    // mientras se está desarrollando, no solo localhost.
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        ws: true,
      },
    },
  },
})
