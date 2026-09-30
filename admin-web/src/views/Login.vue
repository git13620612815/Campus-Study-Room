<template>
  <div class="login">
    <section class="intro">
      <img class="cover" src="../assets/login-study-room.png" alt="安静的校园自习室" />
      <div class="caption">
        <strong>校园自习室</strong>
        <span>管理后台</span>
      </div>
    </section>
    <section class="panel">
      <form class="card" @submit.prevent="submit">
        <h2>管理员登录</h2>
        <p class="lead">请使用管理员账号进入后台。</p>
        <label class="field">
          <span>用户名</span>
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" clearable autocomplete="username" />
        </label>
        <label class="field">
          <span>密码</span>
          <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" show-password autocomplete="current-password" />
        </label>
        <el-button class="submit" type="primary" size="large" native-type="submit" :loading="loading">进入后台</el-button>
        <p class="hint">演示账号 <b>admin</b> / <b>admin123456</b></p>
      </form>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123456' })

async function submit() {
  const username = form.username.trim()
  const password = form.password
  if (!username || !password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    const data = await login({ username, password })
    if (data.role !== 'admin') {
      ElMessage.error('请使用管理员账号登录')
      return
    }
    auth.save(data)
    router.push('/dashboard')
  } catch {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(460px, 1.05fr) minmax(420px, 0.95fr);
  background: #f3f0e8;
}
.intro { position: relative; min-height: 100vh; overflow: hidden; background: #1f3d32; }
.cover { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
.caption {
  position: absolute;
  left: 28px;
  bottom: 28px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 18px;
  border-radius: 16px;
  color: #f6f1e6;
  background: rgba(31, 61, 50, 0.55);
  backdrop-filter: blur(8px);
}
.caption strong { font-size: 18px; letter-spacing: 0.12em; }
.caption span { color: #e6c98a; font-size: 13px; letter-spacing: 0.18em; }
.panel { display: grid; place-items: center; padding: 40px 32px; }
.card {
  width: min(420px, 100%);
  padding: 36px 32px 28px;
  background: #fffdf8;
  border: 1px solid #e4dccb;
  border-radius: 20px;
}
.card h2 { margin: 0; color: #1f3d32; font-size: 26px; }
.lead { margin: 8px 0 24px; color: #78716c; font-size: 14px; }
.field { display: block; margin-bottom: 16px; }
.field span { display: block; margin-bottom: 8px; color: #1f3d32; font-size: 13px; }
.submit { width: 100%; margin-top: 8px; }
.hint { margin: 18px 0 0; color: #78716c; font-size: 13px; text-align: center; }
.hint b { color: #1f3d32; font-weight: 650; }
</style>
