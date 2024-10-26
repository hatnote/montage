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
  }
]

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  await userStore.checkAuth()

  if (to.meta.requiresAuth && userStore.user === null) {
    return next({ name: 'home' })
  }

  next()
})

export default router