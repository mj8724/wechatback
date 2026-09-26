import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/xlsx')) {
            return 'vendor-xlsx'
          }
          if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router')) {
            return 'vendor-vue'
          }
        },
      },
    },
  },
})
