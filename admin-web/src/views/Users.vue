<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>用户</h1>
        <p>停用账号后不能登录，其未开始的预约会被取消。</p>
      </div>
    </div>
    <div class="filters">
      <el-input v-model="keyword" placeholder="昵称 / 学号 / 手机" style="width: 240px" clearable />
      <el-select v-model="role" clearable placeholder="角色" style="width: 140px">
        <el-option label="学生" value="student" />
        <el-option label="管理员" value="admin" />
      </el-select>
      <el-button type="primary" @click="load(1)">查询</el-button>
    </div>
    <div class="panel">
      <el-table :data="rows" v-loading="loading">
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="student_no" label="学号" width="140" />
        <el-table-column prop="phone" label="手机" width="140" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">{{ row.role === 'admin' ? '管理员' : '学生' }}</template>
        </el-table-column>
        <el-table-column label="人脸" width="90">
          <template #default="{ row }">{{ row.face_enrolled ? '已采集' : '未采集' }}</template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" @change="(value) => toggle(row, value)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }"><el-button link @click="reset(row)">重置密码</el-button></template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top: 16px" background layout="total, prev, pager, next" :total="total" :page-size="pageSize" :current-page="page" @current-change="load" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { fetchUsers, resetPassword, setUserStatus } from '../api'

const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const keyword = ref('')
const role = ref('')
const loading = ref(false)

async function load(nextPage = page.value) {
  page.value = nextPage
  loading.value = true
  try {
    const data = await fetchUsers({ page: page.value, page_size: pageSize, keyword: keyword.value, role: role.value })
    rows.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

async function toggle(row, isActive) {
  await setUserStatus(row.id, isActive)
  load()
}

async function reset(row) {
  const data = await resetPassword(row.id)
  await ElMessageBox.alert(`临时密码：${data.temporary_password}`, `已重置 ${row.nickname || row.username}`)
}

onMounted(() => load(1))
</script>
