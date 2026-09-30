<template>
  <div class="page">
    <div class="page-head">
      <div><h1>自习室利用率</h1><p>预约率看占座，使用率只计算已签到。</p></div>
      <div class="filters">
        <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" />
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </div>
    <div class="panel" style="margin-bottom: 16px"><div ref="barEl" class="chart"></div></div>
    <div class="panel"><div ref="heatEl" class="chart"></div></div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { fetchUtilization } from '../../api'
import { percent, recentRange } from '../../utils/date'
import { gold, ink, useChart } from '../../utils/chart'

const range = ref(recentRange())
const barEl = ref(null)
const heatEl = ref(null)
const bar = useChart(barEl)
const heat = useChart(heatEl)

async function load() {
  const data = await fetchUtilization({ date_from: range.value[0], date_to: range.value[1] })
  await nextTick()
  bar.render({
    tooltip: { trigger: 'axis', valueFormatter: (value) => percent(value) },
    legend: { data: ['预约率', '使用率'] },
    grid: { left: 48, right: 16, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: data.rooms.map((item) => item.room_name) },
    yAxis: { type: 'value', max: 1, axisLabel: { formatter: (value) => `${value * 100}%` } },
    series: [
      { name: '预约率', type: 'bar', data: data.rooms.map((item) => item.reservation_rate), color: gold, barMaxWidth: 28 },
      { name: '使用率', type: 'bar', data: data.rooms.map((item) => item.usage_rate), color: ink, barMaxWidth: 28 },
    ],
  })
  heat.render({
    tooltip: { formatter: (item) => `${data.heatmap.y[item.data[1]]} ${data.heatmap.x[item.data[0]]}<br/>${percent(item.data[2])}` },
    grid: { left: 60, right: 20, top: 20, bottom: 80 },
    xAxis: { type: 'category', data: data.heatmap.x, splitArea: { show: true } },
    yAxis: { type: 'category', data: data.heatmap.y, splitArea: { show: true } },
    visualMap: { min: 0, max: 1, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#e7efe9', '#1f3d32'] } },
    series: [{ type: 'heatmap', data: data.heatmap.values, label: { show: true, formatter: (item) => `${Math.round(item.data[2] * 100)}%` } }],
  })
}

onMounted(load)
</script>
