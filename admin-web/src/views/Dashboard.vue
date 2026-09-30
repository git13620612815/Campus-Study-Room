<template>
  <div class="page">
    <div class="cards">
      <article class="metric"><span>开放自习室</span><strong>{{ overview.open_rooms }}</strong></article>
      <article class="metric"><span>今日预约</span><strong>{{ overview.today_reservations }}</strong></article>
      <article class="metric"><span>今日签到</span><strong>{{ overview.today_checkins }}</strong></article>
      <article class="metric"><span>今日使用率</span><strong>{{ percent(overview.today_usage_rate) }}</strong></article>
    </div>
    <div class="panel">
      <div class="page-head"><h1>近 7 日使用率</h1><p>已签到人次 / 可预约座位时段</p></div>
      <div ref="lineEl" class="chart"></div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { fetchOverview, fetchUtilization } from '../api'
import { percent, recentRange } from '../utils/date'
import { gold, ink, useChart } from '../utils/chart'

const overview = reactive({ open_rooms: 0, today_reservations: 0, today_checkins: 0, today_usage_rate: 0 })
const lineEl = ref(null)
const { render } = useChart(lineEl)

onMounted(async () => {
  Object.assign(overview, await fetchOverview())
  const [dateFrom, dateTo] = recentRange(7)
  const data = await fetchUtilization({ date_from: dateFrom, date_to: dateTo })
  await nextTick()
  render({
    tooltip: { trigger: 'axis', valueFormatter: (value) => percent(value) },
    legend: { data: ['使用率', '预约率'] },
    grid: { left: 48, right: 24, top: 40, bottom: 32 },
    xAxis: { type: 'category', data: data.line.map((item) => item.date.slice(5)) },
    yAxis: { type: 'value', max: 1, axisLabel: { formatter: (value) => `${value * 100}%` } },
    series: [
      { name: '使用率', type: 'line', smooth: true, data: data.line.map((item) => item.usage_rate), color: ink },
      { name: '预约率', type: 'line', smooth: true, data: data.line.map((item) => item.reservation_rate), color: gold },
    ],
  })
})
</script>
