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

export async function deleteKnowledge(knowledgeId) {
  const res = await api.delete(`/knowledge/${knowledgeId}/detail`)
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

export async function deleteKnowledgeFile(fileId) {
  const res = await api.delete(`/file/${fileId}`)
  return res.data
}

/**
 * 获取指定文件的分段详情（含父子分段层级）。
 *
 * 后端统一用 SuccessResponse(JSONResponse) 封装：
 *   { success:true, code:200, message:"...", data:[...] }
 * 其中 data 才是分段数组，数组元素结构：
 *   { id, content, position, child_segments: [{ id, content, position }] }
 *
 * 见 api/router/v1/file.py -> get_file_segments -> api/service/file.py::FileService.get_file_segments
 * 见 api/common/response.py SuccessResponse / ResponseSchema
 *
 * 本函数直接返回解包后的分段数组（与其他 api 方法 getKnowledgeFileList / getKnowledgeList 一致）。
 */
export async function getFileSegments(fileId) {
  const res = await api.get(`/file/${fileId}/segments`)
  // axios res.data 是 SuccessResponse 本体；真正的分段数组在 res.data.data
  const payload = res.data ?? {}
  const list = payload.data
  if (!Array.isArray(list)) {
    // 兼容未来字段变化或旧格式：若 payload 本身就是数组也直接用
    if (Array.isArray(payload)) return payload
    return []
  }
  return list
}