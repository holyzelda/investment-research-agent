import { defineStore } from 'pinia'
import { getRouters } from '@/api/menu'
import { buildRailRoutes, filterBackendRoutes } from '@/router/menuAdapter'

const modules = import.meta.glob('./../../views/**/*.vue')

function loadView(view) {
  const normalized = String(view || '').replace(/^\/+/, '').replace(/\.vue$/, '')
  for (const path in modules) {
    const key = path.split('views/')[1]?.replace(/\.vue$/, '')
    if (key === normalized) return () => modules[path]()
  }
  return null
}

export const usePermissionStore = defineStore('permission', {
  state: () => ({
    routes: [],
    railRoutes: [],
    loaded: false,
    loading: null,
  }),
  getters: {
    firstRoutePath: (state) => state.railRoutes[0]?.path || '',
  },
  actions: {
    resetRoutes() {
      this.routes = []
      this.railRoutes = []
      this.loaded = false
      this.loading = null
    },
    async generateRoutes() {
      if (this.loaded) return this.routes
      if (this.loading) return this.loading

      this.loading = (async () => {
        try {
          const res = await getRouters()
          const rawRoutes = Array.isArray(res?.data) ? res.data : []
          const routes = filterBackendRoutes(rawRoutes, loadView)
          this.routes = routes
          this.railRoutes = buildRailRoutes(routes)
          return routes
        } finally {
          this.loaded = true
          this.loading = null
        }
      })()
      return this.loading
    },
  },
})
