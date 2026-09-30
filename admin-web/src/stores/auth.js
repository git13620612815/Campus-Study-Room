import { defineStore } from 'pinia'
import { clearSession, getSession, setSession } from '../session'

export const useAuthStore = defineStore('auth', {
  state: () => ({ session: getSession() }),
  getters: {
    nickname: (state) => state.session?.nickname || '管理员',
  },
  actions: {
    save(data) {
      const session = {
        access: data.access,
        refresh: data.refresh,
        role: data.role,
        nickname: data.nickname,
      }
      setSession(session)
      this.session = session
    },
    logout() {
      clearSession()
      this.session = null
    },
  },
})
