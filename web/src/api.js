import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      handle401Error(error)
    }
    return Promise.reject(error)
  }
)

function handle401Error(error) {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('username')
  const message = error.response?.data?.message
  if (message) {
    ElMessage.warning(message)
  }
  setTimeout(() => {
    window.location.href = '/#/login'
  }, 1500)
}

export default api

export async function login(username, password) {
  const res = await api.post('/user/login', { username, password })
  return res.data
}

export async function register({ username, email, password, confirm_password }) {
  const res = await api.post('/user/register', { username, email, password, confirm_password })
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

export async function logout() {
  const res = await api.post('/user/logout')
  return res.data
}

// ===================== 知识库 =====================

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

// ===================== 知识库文件 =====================

export async function getKnowledgeFileList(knowledgeId, params) {
  const res = await api.get(`/file/${knowledgeId}/list`, { params })
  return res.data
}

export async function createKnowledgeFile(data) {
  const res = await api.post('/file/create', data)
  return res.data
}