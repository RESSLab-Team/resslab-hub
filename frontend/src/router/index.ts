import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('@/views/HomeView.vue')
    },
    {
      path: '/connections',
      component: () => import('@/views/ConnectionsView.vue'),
      children: [
        {
          path: '',
          redirect: '/connections/database'
        },
        {
          path: 'database',
          component: () => import('@/views/ConnectionsDatabase.vue')
        },
        {
          path: 'fragility-curve',
          component: () => import('@/views/ConnectionsFragilityCurve.vue')
        },
        {
          path: 'model',
          component: () => import('@/views/ConnectionsModelView.vue')
        }
      ]
    },
    {
      path: '/columns',
      component: () => import('@/views/ColumnsView.vue'),
      children: [
        {
          path: '',
          redirect: '/columns/database'
        },
        {
          path: 'database',
          component: () => import('@/views/ColumnsDatabase.vue')
        },
        {
          path: 'fragility-curve',
          component: () => import('@/views/ColumnsFragilityCurve.vue')
        },
        {
          path: 'model',
          component: () => import('@/views/ColumnsModelView.vue')
        }
      ]
    },
    {
      path: '/braces',
      component: () => import('@/views/BracesView.vue'),
      children: [
        {
          path: '',
          redirect: '/braces/database'
        },
        {
          path: 'database',
          component: () => import('@/views/BracesDatabase.vue')
        },
        {
          path: 'fragility-curve',
          component: () => import('@/views/BracesFragilityCurve.vue')
        },
        {
          path: 'model',
          component: () => import('@/views/BracesModelView.vue')
        }
      ]
    },
    {
      path: '/materials',
      component: () => import('@/views/MaterialsView.vue'),
      children: [
        {
          path: '',
          redirect: '/materials/database'
        },
        {
          path: 'database',
          component: () => import('@/views/MaterialsDatabase.vue')
        },
        {
          path: 'model',
          component: () => import('@/views/MaterialsModelView.vue')
        }
      ]
    },
    {
      path: '/residuals',
      component: () => import('@/views/ResidualsView.vue'),
      children: [
        {
          path: '',
          redirect: '/residuals/database'
        },
        {
          path: 'database',
          component: () => import('@/views/ResidualsDatabase.vue')
        }
      ]
    },
    {
      path: '/hss-columns',
      component: () => import('@/views/HssView.vue'),
      children: [
        {
          path: '',
          redirect: '/hss-columns/database'
        },
        {
          path: 'database',
          component: () => import('@/views/HssDatabase.vue')
        },
        {
          path: 'model',
          component: () => import('@/views/HssModelView.vue')
        }
      ]
    }
  ]
})

export default router
