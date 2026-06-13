import axios from 'axios'

const api = axios.create({
  baseURL: 'http://127.0.0.1:5000',
  headers: {
    'Content-Type': 'application/json'
  },
  validateStatus(status) {
    return status >= 200 && status < 300
  }
})

export default api
