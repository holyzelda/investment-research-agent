import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// 路由：无登录页、无登录守卫。默认落地对话首页（承接平台跳转）。
const routes = [
  {
    path: '/',
    component: () => import('@/layout/index.vue'),
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/home/index.vue'),
        meta: { title: '对话首页' },
      },
    ],
  },
  // 兜底：任何未知路径回到对话首页
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

NProgress.configure({ showSpinner: false })

router.beforeEach((to, from, next) => {
  NProgress.start()
  if (to.meta?.title) {
    document.title = `${to.meta.title} · ${import.meta.env.VITE_APP_TITLE || '朱雀投研智能体'}`
  }
  next()
})

router.afterEach(() => {
  NProgress.done()
})

export default router
