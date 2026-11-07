// The landing page ships with the entry chunk: statically importing it saves a
// router-resolve → fetch round trip on every first visit. Its heavy pieces
// (map, API client) already load lazily from within the view. Every other
// route stays a dynamic import.
import { installAuthGuard } from '@/router/guards'
import HomeView from '@/views/HomeView.vue'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  // Back/forward restore where the reader was. A new page starts at the top:
  // without this, leaving a page from its bottom opened the next one at the
  // bottom too (issue #282, Kinane's review). Query-only changes (the
  // dashboards mirror their filters into the URL) keep the scroll as is.
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash }
    if (to.path === from.path) return false
    // Same editor after a submit, the URL only caught up with the store
    // (#403): stay on the confirmation at the bottom.
    if (from.name === 'ContributeNew' && to.name === 'ContributeEdit') return false
    return { top: 0 }
  },
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
      children: [
        {
          path: '',
          redirect: '/connections/database'
        },
        {
          path: 'database',
          component: () => import('@/components/connections/ConnectionDashboard.vue')
        },
        {
          path: 'fragility-curve',
          component: () => import('@/components/connections/ConnectionFragility.vue')
        },
        {
          path: 'model',
          component: () => import('@/components/connections/ConnectionModel.vue')
        }
      ]
    },
    {
      path: '/columns',
      children: [
        {
          path: '',
          redirect: '/columns/database'
        },
        {
          path: 'database',
          component: () => import('@/components/columns/ColumnDashboard.vue')
        },
        {
          path: 'fragility-curve',
          component: () => import('@/components/columns/ColumnFragility.vue')
        },
        {
          path: 'model',
          component: () => import('@/components/columns/ColumnModel.vue')
        }
      ]
    },
    {
      path: '/braces',
      children: [
        {
          path: '',
          redirect: '/braces/database'
        },
        {
          path: 'database',
          component: () => import('@/components/braces/BraceDashboard.vue')
        },
        {
          path: 'fragility-curve',
          component: () => import('@/components/braces/BraceFragility.vue')
        },
        {
          path: 'model',
          component: () => import('@/components/braces/BraceModel.vue')
        }
      ]
    },
    {
      path: '/materials',
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
          component: () => import('@/components/materials/MaterialDashboard.vue')
        },
        {
          path: 'tensile-coupons',
          component: () => import('@/components/tensile-coupons/TensileCouponDashboard.vue')
        },
        {
          path: 'ductile-fracture',
          component: () => import('@/components/ductile-fracture/DuctileFractureDashboard.vue')
        },
        {
          path: 'model',
          component: () => import('@/components/materials/MaterialModel.vue')
        }
      ]
    },
    {
      path: '/residuals',
      children: [
        {
          path: '',
          redirect: '/residuals/database'
        },
        {
          path: 'database',
          component: () => import('@/components/residuals/ResidualDashboard.vue')
        }
      ]
    },
    {
      path: '/hss-columns',
      children: [
        {
          path: '',
          redirect: '/hss-columns/database'
        },
        {
          path: 'database',
          component: () => import('@/components/hss/HssDashboard.vue')
        },
        {
          path: 'model',
          component: () => import('@/components/hss/HssModel.vue')
        }
      ]
    },
    {
      path: '/ebf-links',
      children: [
        {
          path: '',
          redirect: '/ebf-links/database'
        },
        {
          path: 'database',
          component: () => import('@/components/ebf/EbfDashboard.vue')
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
      // `meta.contributions` marks the contribution pipeline (submit,
      // curation, sign-in, account): it goes home on a deployment that
      // switched it off with CONTRIBUTIONS_ENABLED=false.
      path: '/contribute/new',
      name: 'ContributeNew',
      component: () => import('@/views/ContributeView.vue'),
      // Submitting needs the role, not just a session (#248).
      meta: { auth: 'contributor', contributions: true }
    },
    {
      // The same editor, opened on an open submission (#321).
      path: '/contribute/edit/:prNumber(\\d+)',
      name: 'ContributeEdit',
      component: () => import('@/views/ContributeView.vue'),
      props: true,
      meta: { auth: 'contributor', contributions: true }
    },
    {
      // Every open submission: curators only (#248).
      path: '/curation',
      name: 'CurationQueue',
      component: () => import('@/views/CurationQueueView.vue'),
      meta: { auth: 'curator', contributions: true }
    },
    {
      // One submission: a curator, or the person who sent it. The guard only
      // knows the role, so it lets a contributor through and the backend says
      // 403 when the submission is not theirs.
      path: '/curation/:prNumber(\\d+)',
      name: 'CurationReview',
      component: () => import('@/views/CurationReviewView.vue'),
      props: true,
      meta: { auth: 'contributor', contributions: true }
    },
    {
      // Rows already live and still unverified, one reference at a time
      // (?reference=, ?id= to start on one), with the same panels (#253).
      path: '/curation/verify/:type',
      name: 'VerificationReview',
      component: () => import('@/views/CurationReviewView.vue'),
      props: true,
      meta: { auth: 'curator', contributions: true }
    },
    {
      // Who can do what: members, invitations, access requests (#248).
      path: '/admin',
      name: 'Admin',
      component: () => import('@/views/AdminView.vue'),
      meta: { auth: 'admin', contributions: true }
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { contributions: true }
    },
    {
      // Where the mailed link lands: it carries the challenge and the token in
      // the query, and this view posts them.
      path: '/login/verify',
      name: 'LoginVerify',
      component: () => import('@/views/LoginVerifyView.vue'),
      meta: { contributions: true }
    },
    {
      path: '/account',
      name: 'Account',
      component: () => import('@/views/AccountView.vue'),
      meta: { auth: 'viewer', contributions: true }
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
