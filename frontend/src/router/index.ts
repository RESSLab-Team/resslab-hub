// The landing page ships with the entry chunk: statically importing it saves a
// router-resolve → fetch round trip on every first visit. Its heavy pieces
// (map, API client) already load lazily from within the view. Every other
// route stays a dynamic import.
import { installAuthGuard } from '@/router/guards'
import HomeView from '@/views/HomeView.vue'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: HomeView
    },
    {
      path: '/about',
      name: 'About',
      component: () => import('@/views/AboutView.vue')
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
          redirect: '/materials/cyclic-coupons'
        },
        {
          path: 'database',
          redirect: '/materials/cyclic-coupons'
        },
        {
          path: 'cyclic-coupons',
          component: () => import('@/views/MaterialsDatabase.vue')
        },
        {
          path: 'tensile-coupons',
          component: () => import('@/views/TensileCouponsDatabase.vue')
        },
        {
          path: 'ductile-fracture',
          component: () => import('@/views/DuctileFractureDatabase.vue')
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
    },
    {
      path: '/ebf-links',
      component: () => import('@/views/EbfView.vue'),
      children: [
        {
          path: '',
          redirect: '/ebf-links/database'
        },
        {
          path: 'database',
          component: () => import('@/views/EbfDatabase.vue')
        }
      ]
    },
    {
      path: '/contribute',
      redirect: '/contribute/new'
    },
    {
      // `meta.auth` names the weakest role that may open the route; the guard
      // in router/guards.ts does the rest. Everything without it is public,
      // which is every database page: browsing needs no account.
      path: '/contribute/new',
      name: 'ContributeNew',
      component: () => import('@/views/ContributeView.vue'),
      meta: { auth: 'viewer' }
    },
    {
      path: '/curation',
      name: 'CurationQueue',
      component: () => import('@/views/CurationQueueView.vue'),
      meta: { auth: 'viewer' }
    },
    {
      path: '/curation/:prNumber(\\d+)',
      name: 'CurationReview',
      component: () => import('@/views/CurationReviewView.vue'),
      props: true,
      meta: { auth: 'viewer' }
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue')
    },
    {
      // Where the mailed link lands: it carries the challenge and the token in
      // the query, and this view posts them.
      path: '/login/verify',
      name: 'LoginVerify',
      component: () => import('@/views/LoginVerifyView.vue')
    },
    {
      path: '/account',
      name: 'Account',
      component: () => import('@/views/AccountView.vue'),
      meta: { auth: 'viewer' }
    },
    {
      path: '/forbidden',
      name: 'Forbidden',
      component: () => import('@/views/ForbiddenView.vue')
    }
  ]
})

installAuthGuard(router)

export default router
