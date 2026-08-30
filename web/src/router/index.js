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
          path: 'knowledge/:knowledgeId/files',
          name: 'KnowledgeFileList',
          component: () => import('../views/knowledge/FileList.vue'),
          meta: { title: '知识库文件', icon: 'Document' },
        },
        {
          path: 'knowledge/files/:fileId/segments',
          name: 'KnowledgeFileSegments',
          component: () => import('../views/knowledge/SegmentDetail.vue'),
          meta: { title: '分段详情', icon: 'Tickets' },
          // query 支持传入 knowledge_id，用于「返回文件列表」时回到正确的知识库
          props: (route) => ({ fileId: route.params.fileId, knowledgeId: route.query.knowledge_id }),
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
