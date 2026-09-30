import { createRouter, createWebHistory } from 'vue-router'
import { getSession } from '../session'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/Login.vue') },
    {
      path: '/',
      component: () => import('../layouts/AdminLayout.vue'),
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '总览' } },
        { path: 'rooms', component: () => import('../views/Rooms.vue'), meta: { title: '自习室' } },
        { path: 'rooms/:id/seats', component: () => import('../views/Seats.vue'), meta: { title: '座位布局' } },
        { path: 'reservations', component: () => import('../views/Reservations.vue'), meta: { title: '预约监管' } },
        { path: 'stats/seats', component: () => import('../views/stats/SeatStats.vue'), meta: { title: '座位使用' } },
        { path: 'stats/users', component: () => import('../views/stats/UserStats.vue'), meta: { title: '用户活跃度' } },
        { path: 'stats/utilization', component: () => import('../views/stats/Utilization.vue'), meta: { title: '利用率' } },
        { path: 'users', component: () => import('../views/Users.vue'), meta: { title: '用户管理' } },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const session = getSession()
  const signedIn = session?.access && session.role === 'admin'
  if (to.path !== '/login' && !signedIn) return '/login'
  if (to.path === '/login' && signedIn) return '/dashboard'
  return true
})

export default router
