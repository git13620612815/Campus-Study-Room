import { BASE_URL } from '../config'

const ACCESS = 'access'
const REFRESH = 'refresh'
const PROFILE = 'profile'

export function getToken() {
  return uni.getStorageSync(ACCESS) || ''
}

export function saveAuth(data) {
  uni.setStorageSync(ACCESS, data.access)
  uni.setStorageSync(REFRESH, data.refresh)
  uni.setStorageSync(PROFILE, { role: data.role, nickname: data.nickname, face_enrolled: data.face_enrolled })
}

export function clearAuth() {
  uni.removeStorageSync(ACCESS)
  uni.removeStorageSync(REFRESH)
  uni.removeStorageSync(PROFILE)
}

export function getProfile() {
  return uni.getStorageSync(PROFILE) || {}
}

function parseBody(raw) {
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return { message: '响应无法解析' } }
  }
  return raw || {}
}

export function request({ url, method = 'GET', data, auth = true, retry = false }) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...(auth && getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
      },
      success: async (res) => {
        const body = parseBody(res.data)
        if (res.statusCode === 401 && auth && !retry && getToken()) {
          const refreshed = await refresh()
          if (refreshed) {
            resolve(await request({ url, method, data, auth, retry: true }))
            return
          }
          clearAuth()
          uni.reLaunch({ url: '/pages/login/login' })
          reject(body)
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300 && body.code === 0) {
          resolve(body.data)
          return
        }
        uni.showToast({ title: body.message || '请求失败', icon: 'none' })
        reject(body)
      },
      fail: (error) => {
        uni.showToast({ title: '网络异常', icon: 'none' })
        reject(error)
      },
    })
  })
}

function refresh() {
  const token = uni.getStorageSync(REFRESH)
  if (!token || request._refreshing) return Promise.resolve(false)
  request._refreshing = true
  return new Promise((resolve) => {
    uni.request({
      url: `${BASE_URL}/auth/refresh/`,
      method: 'POST',
      data: { refresh: token },
      success: (res) => {
        const body = parseBody(res.data)
        if (body.code === 0 && body.data?.access) {
          uni.setStorageSync(ACCESS, body.data.access)
          resolve(true)
        } else resolve(false)
      },
      fail: () => resolve(false),
      complete: () => { request._refreshing = false },
    })
  })
}

export function upload(url, filePath) {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + url,
      filePath,
      name: 'image',
      header: { Authorization: `Bearer ${getToken()}` },
      success: (res) => {
        const body = parseBody(res.data)
        if (res.statusCode >= 200 && res.statusCode < 300 && body.code === 0) {
          resolve(body.data)
          return
        }
        uni.showToast({ title: body.message || '请求失败', icon: 'none' })
        reject(body)
      },
      fail: (error) => {
        uni.showToast({ title: '网络异常', icon: 'none' })
        reject(error)
      },
    })
  })
}

export function ensureLogin() {
  if (!getToken()) {
    uni.reLaunch({ url: '/pages/login/login' })
    return false
  }
  return true
}
