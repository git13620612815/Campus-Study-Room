<template>
  <div class="page">
    <div class="page-head">
      <div><h1>座位使用</h1><p>按时段长度累计占用和空闲，不按分钟心跳。</p></div>
      <div class="filters">
        <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="exportFile">导出</el-button>
      </div>
    </div>
    <div class="panel" style="margin-bottom: 16px"><div ref="chartEl" class="chart"></div></div>
    <div class="panel">
      <el-table :data="items" height="420">
        <el-table-column prop="room_name" label="自习室" />
        <el-table-column prop="zone" label="区域" />
        <el-table-column prop="code" label="座位" width="90" />
        <el-table-column prop="reservation_count" label="预约次数" width="100" />
        <el-table-column prop="checkin_count" label="签到次数" width="100" />
        <el-table-column prop="expired_count" label="爽约次数" width="100" />
        <el-table-column prop="occupied_minutes" label="占用分钟" width="110" />
        <el-table-column prop="reserved_minutes" label="已预约未使用" width="130" />
        <el-table-column prop="free_minutes" label="空闲分钟" width="110" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { exportSeatStats, fetchSeatStats } from '../../api'
import { recentRange } from '../../utils/date'
import { ink, useChart } from '../../utils/chart'

const range = ref(recentRange())
const items = ref([])
const chartEl = ref(null)
const { render } = useChart(chartEl)

async function load() {
  const data = await fetchSeatStats({ date_from: range.value[0], date_to: range.value[1] })
  items.value = data.items
  await nextTick()
  render({
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 16, top: 24, bottom: 80 },
    dataZoom: [{ type: 'slider', bottom: 16 }],
    xAxis: { type: 'category', data: items.value.map((item) => `${item.room_name}-${item.code}`), axisLabel: { rotate: 40 } },
    yAxis: { type: 'value', name: '预约次数' },
    series: [{ type: 'bar', data: items.value.map((item) => item.reservation_count), color: ink, barMaxWidth: 28 }],
  })
}

function exportFile() {
  exportSeatStats({ date_from: range.value[0], date_to: range.value[1] })
}

onMounted(load)
</script>
