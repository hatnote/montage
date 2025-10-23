import '@wikimedia/codex/dist/codex.style.css'
import '@/assets/main.css'

import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

import HomeView from '../views/HomeView.vue'
import NewCampaignView from '@/views/NewCampaignView.vue'
import CampaignView from '@/views/CampaignView.vue'
import VoteView from '@/views/VoteView.vue'
import VoteEditView from '@/views/VoteEditView.vue'
import AllCampaignView from '@/views/AllCampaignView.vue'
import PermissionDenied from '@/views/PermissionDenied.vue'
import EntryQuery from '@/components/Maintainer/EntryQuery.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/campaign/all',
    name: 'campaign-all',
    component: AllCampaignView,
    meta: { requiresAuth: true }
  },
  {
    path: '/campaign/new',
    name: 'new-campaign',
    component: NewCampaignView,
    meta: { requiresAuth: true }
  },
  {
    path: '/campaign/:id',
    name: 'campaign',
    component: CampaignView,
    meta: { requiresAuth: true }
  },
  {
    path: '/vote/:id',
    name: 'vote',
    component: VoteView,
    meta: { requiresAuth: true }
  },
  {
    path: '/vote/:id/edit',
    name: 'vote-edit',
    component: VoteEditView,
    meta: { requiresAuth: true }
  },
  {
    path: '/entry-query',
    name: 'entry-query',
    component: EntryQuery,
    meta: { requiresAuth: true }
  },
  {
    path: '/permission-denied',
    name: 'permission-denied',
    component: PermissionDenied,
  }
]

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  if (!userStore.authChecked) {
    await userStore.checkAuth()
  }

  if (to.meta.requiresAuth && userStore.user === null) {
    return next({ name: 'home' })
  }

  next()
})

export default router
