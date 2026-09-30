<template>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <strong>自习室</strong>
        <span>管理后台</span>
      </div>
      <el-menu :default-active="route.path" router background-color="transparent" text-color="#d7e5dc" active-text-color="#f3d48a">
        <el-menu-item index="/dashboard"><el-icon><Odometer /></el-icon>总览</el-menu-item>
        <el-menu-item index="/rooms"><el-icon><OfficeBuilding /></el-icon>自习室</el-menu-item>
        <el-menu-item index="/reservations"><el-icon><Tickets /></el-icon>预约监管</el-menu-item>
        <el-menu-item index="/stats/seats"><el-icon><Histogram /></el-icon>座位使用</el-menu-item>
        <el-menu-item index="/stats/users"><el-icon><User /></el-icon>用户活跃</el-menu-item>
        <el-menu-item index="/stats/utilization"><el-icon><PieChart /></el-icon>利用率</el-menu-item>
        <el-menu-item index="/users"><el-icon><Avatar /></el-icon>用户管理</el-menu-item>
      </el-menu>
    </aside>
    <section class="main">
      <header class="top">
        <h1>{{ route.meta.title || '管理后台' }}</h1>
        <div class="who">
          <span>{{ auth.nickname }}</span>
          <el-button text @click="logout">退出</el-button>
        </div>
      </header>
      <router-view />
    </section>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import { Avatar, Histogram, Odometer, OfficeBuilding, PieChart, Tickets, User } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.shell { display: flex; min-height: 100vh; }
.side { width: 220px; background: #1f3d32; color: #e7efe9; flex-shrink: 0; }
.brand { padding: 28px 22px 18px; display: flex; flex-direction: column; gap: 4px; }
.brand strong { font-size: 22px; letter-spacing: 0.08em; }
.brand span { color: #c4a35a; font-size: 12px; letter-spacing: 0.18em; }
.el-menu { border-right: none; }
.main { flex: 1; min-width: 0; }
.top { height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; background: #fffdf8; border-bottom: 1px solid #e4dccb; }
.top h1 { margin: 0; font-size: 18px; color: #1f3d32; }
.who { display: flex; align-items: center; gap: 8px; color: #57534e; }
</style>
