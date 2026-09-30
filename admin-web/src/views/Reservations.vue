<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>预约监管</h1>
        <p>可以按日期、状态和自习室查看，并强制取消。</p>
      </div>
    </div>
    <div class="filters">
      <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始" end-placeholder="结束" />
      <el-select v-model="status" clearable placeholder="状态" style="width: 140px">
        <el-option v-for="item in statuses" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-model="roomId" clearable placeholder="自习室" style="width: 180px">
        <el-option v-for="room in rooms" :key="room.id" :label="room.name" :value="room.id" />
      </el-select>
      <el-button type="primary" @click="load(1)">查询</el-button>
    </div>
    <div class="panel">
      <el-table :data="rows" v-loading="loading">
        <el-table-column prop="reserve_date" label="日期" width="120" />
        <el-table-column prop="room_name" label="自习室" min-width="140" />
        <el-table-column prop="seat_code" label="座位" width="90" />
        <el-table-column label="时段" min-width="150">
          <template #default="{ row }">{{ row.slot_name }} {{ row.start_time }}-{{ row.end_time }}</template>
        </el-table-column>
        <el-table-column prop="nickname" label="学生" width="100" />
        <el-table-column prop="student_no" label="学号" width="120" />
        <el-table-column prop="status_label" label="状态" width="110" />
        <el-table-column prop="checkin_result" label="签到" width="90" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending' || row.status === 'checked_in'" link @click="cancel(row)">强制取消</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        style="margin-top: 16px"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { adminCancel, fetchReservations, fetchRooms } from '../api'

const rooms = ref([])
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const range = ref([])
const status = ref('')
const roomId = ref('')
const statuses = [
  { value: 'pending', label: '预约中' },
  { value: 'checked_in', label: '已签到' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
  { value: 'expired', label: '爽约' },
  { value: 'admin_cancelled', label: '管理员取消' },
]

async function load(nextPage = page.value) {
  page.value = nextPage
  loading.value = true
  try {
    const data = await fetchReservations({
      page: page.value,
      page_size: pageSize,
      date_from: range.value?.[0] || '',
      date_to: range.value?.[1] || '',
      status: status.value || '',
      room_id: roomId.value || '',
    })
    rows.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

async function cancel(row) {
  const { value } = await ElMessageBox.prompt('请输入取消原因', '强制取消', {
    inputPattern: /\S+/,
    inputErrorMessage: '请填写原因',
  })
  await adminCancel(row.id, value)
  load()
}

onMounted(async () => {
  rooms.value = await fetchRooms()
  load(1)
})
</script>
