const KEY = 'study-room-admin'

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || 'null')
  } catch {
    return null
  }
}

export function setSession(value) {
  localStorage.setItem(KEY, JSON.stringify(value))
}

export function clearSession() {
  localStorage.removeItem(KEY)
}
