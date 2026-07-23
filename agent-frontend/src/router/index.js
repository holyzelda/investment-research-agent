import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// 路由：保留独立登录页，同时支持平台携带 Token 直接承接；默认落地对话首页。
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login.vue'),
    meta: { title: '用户登录', hidden: true },
  },
  {
    path: '/',
    name: 'Root',
    component: () => import('@/layout/index.vue'),
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/home/index.vue'),
        meta: { title: '对话首页' },
      },
      {
        path: 'reports/:reportId',
        name: 'ReportDetail',
        component: () => import('@/views/report/index.vue'),
        meta: { title: '正式报告', collapseSidebar: true },
      },
      {
        path: 'tie-line',
        name: 'TieLineMap',
        component: () => import('@/views/tie-line/index.vue'),
        meta: { title: '联络线地图', collapseSidebar: true },
      },
      {
        path: 'policy-market',
        name: 'PolicyMarket',
        component: () => import('@/views/policy-market/index.vue'),
        meta: { title: '政策与市场', collapseSidebar: true },
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
