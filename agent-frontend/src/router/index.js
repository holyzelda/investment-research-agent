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
    path: '/reports/:reportId',
    name: 'ReportDetail',
    component: () => import('@/views/report/index.vue'),
    meta: { title: '正式报告' },
  },
  {
    path: '/public/calculation-shares/:shareCode',
    name: 'CalculationShare',
    component: () => import('@/views/public/calculation-share.vue'),
    meta: { title: '测算结果分享' },
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
        path: 'index-map',
        name: 'IndexMap',
        component: () => import('@/views/index-map/index.vue'),
        meta: { title: '全国储能投资指数', collapseSidebar: true },
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
      {
        path: 'calculation-ledger',
        name: 'CalculationLedger',
        component: () => import('@/views/calculation-ledger/index.vue'),
        meta: { title: '测算台账', collapseSidebar: true },
      },
    ],
  },
  // 兜底：任何未知路径回到对话首页
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
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
