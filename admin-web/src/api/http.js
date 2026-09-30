import axios from 'axios'
import { ElMessage } from 'element-plus'
import { clearSession, getSession, setSession } from '../session'

const http = axios.create({ baseURL: '/api/v1', timeout: 20000 })

http.interceptors.request.use((config) => {
  const session = getSession()
  if (session?.access) config.headers.Authorization = `Bearer ${session.access}`
  return config
})

async function refreshAccess() {
  const session = getSession()
  if (!session?.refresh) throw new Error('no refresh')
  const response = await axios.post('/api/v1/auth/refresh/', { refresh: session.refresh })
  if (response.data.code !== 0) throw new Error('refresh failed')
  session.access = response.data.data.access
  setSession(session)
  return session.access
}

http.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') return response
    const body = response.data
    if (body.code !== 0) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(body)
    }
    return body.data
  },
  async (error) => {
    const original = error.config || {}
    const status = error.response?.status
    if (status === 401 && !original._retry && !String(original.url || '').includes('/auth/')) {
      original._retry = true
      try {
        original.headers.Authorization = `Bearer ${await refreshAccess()}`
        return http(original)
      } catch {
        clearSession()
        if (!window.location.pathname.startsWith('/login')) window.location.href = '/login'
        return Promise.reject(error)
      }
    }
    let message = error.response?.data?.message || '网络异常'
    if (error.response?.data instanceof Blob) {
      try {
        message = JSON.parse(await error.response.data.text()).message || message
      } catch {
        message = '导出失败'
      }
    }
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export async function download(path, filename) {
  const response = await http.get(path, { responseType: 'blob' })
  const blob = response.data
  if (blob.type && blob.type.includes('json')) {
    const message = JSON.parse(await blob.text()).message || '导出失败'
    ElMessage.error(message)
    return
  }
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export default http
