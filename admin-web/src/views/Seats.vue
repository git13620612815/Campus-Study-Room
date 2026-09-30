<template>
  <div class="page" v-loading="loading">
    <div class="page-head">
      <div>
        <h1>{{ room.name || '座位布局' }}</h1>
        <p>{{ room.building }} {{ room.floor }} · {{ room.facilities }}</p>
      </div>
      <div class="filters">
        <el-date-picker v-model="date" value-format="YYYY-MM-DD" @change="loadSeats" />
        <el-select v-model="slotId" placeholder="时段" style="width: 180px" @change="loadSeats">
          <el-option v-for="slot in room.slots || []" :key="slot.id" :label="`${slot.name} ${slot.start_time}-${slot.end_time}`" :value="slot.id" />
        </el-select>
      </div>
    </div>
    <div class="panel" style="margin-bottom: 16px">
      <el-form inline>
        <el-form-item label="区域"><el-input v-model="batch.zone" placeholder="靠窗" /></el-form-item>
        <el-form-item label="前缀"><el-input v-model="batch.prefix" placeholder="A" style="width: 80px" /></el-form-item>
        <el-form-item label="行"><el-input-number v-model="batch.rows" :min="1" :max="20" /></el-form-item>
        <el-form-item label="列"><el-input-number v-model="batch.cols" :min="1" :max="20" /></el-form-item>
        <el-button type="primary" @click="createSeats">批量生成</el-button>
      </el-form>
      <div class="seat-grid" :style="{ gridTemplateColumns: `repeat(${columns}, 76px)` }">
        <div v-for="seat in seats" :key="seat.id" class="cell" :style="{ background: seat.color }">{{ seat.code }}</div>
      </div>
    </div>
    <div class="panel">
      <el-table :data="seats">
        <el-table-column prop="code" label="座位号" width="120" />
        <el-table-column prop="zone" label="区域" />
        <el-table-column prop="row_no" label="行" width="80" />
        <el-table-column prop="col_no" label="列" width="80" />
        <el-table-column label="当前状态" width="140">
          <template #default="{ row }"><span class="swatch" :style="{ background: row.color }"></span>{{ row.status_label }}</template>
        </el-table-column>
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(value) => toggle(row, value)" />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { batchSeats, fetchRoom, fetchSeatBoard, updateSeat } from '../api'
import { formatDate } from '../utils/date'

const route = useRoute()
const room = ref({})
const seats = ref([])
const loading = ref(false)
const date = ref(formatDate(new Date()))
const slotId = ref(null)
const batch = reactive({ zone: '靠窗', prefix: 'A', rows: 2, cols: 2 })
const columns = computed(() => Math.max(1, ...seats.value.map((seat) => seat.col_no || 1)))

async function loadRoom() {
  room.value = await fetchRoom(route.params.id)
  const enabled = (room.value.slots || []).find((slot) => slot.enabled) || room.value.slots?.[0]
  slotId.value = enabled?.id || null
  await loadSeats()
}

async function loadSeats() {
  if (!slotId.value || !date.value) return
  loading.value = true
  try {
    const data = await fetchSeatBoard(route.params.id, { date: date.value, slot_id: slotId.value })
    seats.value = data.seats
  } finally {
    loading.value = false
  }
}

async function createSeats() {
  await batchSeats(route.params.id, { items: [{ ...batch }] })
  await loadRoom()
}

async function toggle(row, enabled) {
  await updateSeat(row.id, { enabled })
  await loadSeats()
}

onMounted(loadRoom)
</script>

<style scoped>
.seat-grid { display: grid; gap: 8px; margin-top: 8px; }
.cell { height: 42px; border-radius: 10px; color: white; display: grid; place-items: center; font-size: 12px; }
</style>
