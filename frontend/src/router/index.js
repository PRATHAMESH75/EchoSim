import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const SentimentView = () => import('../views/SentimentView.vue')

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
  },
  {
    path: '/sentiment',
    name: 'SentimentSimulator',
    component: SentimentView,
  },
  {
    path: '/sentiment/campaign/:campaignId',
    name: 'SentimentCampaign',
    component: SentimentView,
    props: true,
  },
  {
    path: '/process/:pathMatch(.*)*',
    redirect: '/sentiment',
  },
  {
    path: '/simulation/:pathMatch(.*)*',
    redirect: '/sentiment',
  },
  {
    path: '/report/:pathMatch(.*)*',
    redirect: '/sentiment',
  },
  {
    path: '/interaction/:pathMatch(.*)*',
    redirect: '/sentiment',
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/sentiment',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
