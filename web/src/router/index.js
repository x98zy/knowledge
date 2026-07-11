import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { title: '注册', guest: true },
  },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/knowledge',
    children: [
        {
          path: 'knowledge',
          name: 'KnowledgeList',
          component: () => import('../views/knowledge/List.vue'),
          meta: { title: '知识库', icon: 'Collection' },
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('../views/Profile.vue'),
          meta: { title: '个人信息', icon: 'User' },
        },
      ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// Navigation guard: redirect to login if no token
router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  if (!to.meta.guest && !token) {
    return { name: 'Login' }
  }
  // Redirect logged-in users away from login/register
  if (to.meta.guest && token) {
    return { name: 'KnowledgeList' }
  }
})

export default router
