import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// 朱雀投研智能体前端构建配置
// 说明：前端配置网关基地址；固定接口 Token 由 src/utils/request.js 从 VITE_API_TOKEN 读取并注入，Vite 代理不处理鉴权。
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const baseApi = env.VITE_APP_BASE_API || '/gateway/ir-agent/'
  return {
    base: '/investment/',
    plugins: [
      vue(),
      AutoImport({ resolvers: [ElementPlusResolver({ importStyle: false })] }),
      Components({ resolvers: [ElementPlusResolver({ importStyle: false })] }),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    css: {
      preprocessorOptions: {
        scss: { api: 'modern-compiler' },
      },
    },
    server: {
      port: 5210,
      proxy: {
        // 开发环境把网关基地址代理到后端；生产由统一平台网关承担。
        [baseApi]: {
          target: env.VITE_DEV_BACKEND || 'http://127.0.0.1:9089',
          changeOrigin: true,
          rewrite: (p) => p.replace(new RegExp('^' + baseApi), '/'),
        },
        // 菜单和用户信息由统一 ecenter 网关提供，开发环境直连测试网关。
        '/gateway/ecenter/': {
          target: env.VITE_ECENTER_BACKEND || 'http://internal-2-58.example.invalid:8183',
          changeOrigin: true,
          secure: false,
        },
        '/gateway/': {
          target: env.VITE_GATEWAY_BACKEND || env.VITE_ECENTER_BACKEND || 'http://internal-2-58.example.invalid:8183',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      include: ['tests/**/*.spec.js'],
      css: true,
    },
  }
})
