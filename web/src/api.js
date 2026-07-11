import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

let isRefreshing = false
let refreshSubscribers = []

function onTokenRefreshed(newToken) {
  refreshSubscribers.forEach((callback) => callback(newToken))
  refreshSubscribers = []
}

function addRefreshSubscriber(callback) {
  refreshSubscribers.push(callback)
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          addRefreshSubscriber((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            resolve(api(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) {
          throw new Error('No refresh token available')
        }
        const res = await api.post('/user/token/refresh', { refresh_token: refreshToken })
        const { access_token } = res.data
        localStorage.setItem('access_token', access_token)
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        onTokenRefreshed(access_token)
        return api(originalRequest)
      } catch (refreshError) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('username')
        ElMessage.warning('登录已失效，请重新登录')
        setTimeout(() => {
          window.location.href = '/#/login'
        }, 1500)
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

export default api

export async function login(username, password) {
  const res = await api.post('/user/login', { username, password })
  return res.data
}

export async function register({ username, email, password, confirm_password }) {
  const res = await api.post('/user/register', { username, email, password, confirm_password })
  return res.data
}

export async function refreshToken(refresh_token) {
  const res = await api.post('/user/token/refresh', { refresh_token })
  return res.data
}

export async function getUserProfile() {
  const res = await api.get('/user/profile')
  return res.data
}

export async function uploadAvatar(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post('/user/upload_avator', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function changePassword(oldPassword, newPassword) {
  const res = await api.post('/user/change_password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
  return res.data
}

// ===================== 知识库 =====================
// Note: all API functions return res.data (the parsed JSON body),
// consistent with login/register above.

export async function getKnowledgeList(params) {
  const res = await api.get('/knowledge/list', { params })
  return res.data
}

export async function createKnowledge(data) {
  const res = await api.post('/knowledge/create', data)
  return res.data
}

export async function getEmbeddingModels() {
  const res = await api.get('/knowledge/get_embedding_models')
  return res.data
}

export async function getKnowledgeDetail(knowledgeId) {
  const res = await api.get(`/knowledge/${knowledgeId}/detail`)
  return res.data
}

export async function uploadFile(formData) {
  const res = await api.post('/knowledge/upload_file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
