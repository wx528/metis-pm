import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'

function getVersion() {
  if (process.env.APP_VERSION) return process.env.APP_VERSION
  try {
    return readFileSync(resolve(__dirname, '../VERSION'), 'utf-8').trim()
  } catch {
    return '0.0.0'
  }
}

const version = getVersion()

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/') || id.includes('node_modules/react-router-dom')) {
            return 'vendor-react';
          }
          if (id.includes('node_modules/antd') || id.includes('node_modules/@ant-design')) {
            return 'vendor-antd';
          }
          if (id.includes('node_modules/@dnd-kit')) {
            return 'vendor-dnd';
          }
        },
      },
    },
  },
})
