import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach token to every request if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

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
