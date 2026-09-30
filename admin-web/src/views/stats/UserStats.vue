<template>
  <div class="page">
    <div class="page-head">
      <div><h1>用户活跃度</h1><p>高活跃：有效预约不少于 8 且签到率不低于 80%。低活跃：签到率低于 40%，或爽约达到 3 次。</p></div>
      <div class="filters">
        <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" />
        <el-radio-group v-model="label">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="高活跃">高活跃</el-radio-button>
          <el-radio-button value="低活跃">低活跃</el-radio-button>
          <el-radio-button value="普通">普通</el-radio-button>
          <el-radio-button value="样本不足">样本不足</el-radio-button>
        </el-radio-group>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </div>
    <div class="panel" style="margin-bottom: 16px"><div ref="chartEl" class="chart"></div></div>
    <div class="panel">
      <el-table :data="filtered">
        <el-table-column prop="student_no" label="学号" width="140" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="valid_count" label="有效预约" width="110" />
        <el-table-column prop="cancel_count" label="取消次数" width="110" />
        <el-table-column prop="checkin_count" label="签到次数" width="110" />
        <el-table-column prop="expired_count" label="爽约次数" width="110" />
        <el-table-column label="签到率" width="110">
          <template #default="{ row }">{{ percent(row.checkin_rate) }}</template>
        </el-table-column>
        <el-table-column label="标签" width="120">
          <template #default="{ row }"><el-tag :type="tagType(row.label)">{{ row.label }}</el-tag></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { fetchUserStats } from '../../api'
import { percent, recentRange } from '../../utils/date'
import { ink, useChart } from '../../utils/chart'

const range = ref(recentRange())
const items = ref([])
const label = ref('')
const chartEl = ref(null)
const { render } = useChart(chartEl)
const filtered = computed(() => items.value.filter((item) => !label.value || item.label === label.value))

function tagType(value) {
  if (value === '高活跃') return 'success'
  if (value === '低活跃') return 'danger'
  if (value === '样本不足') return 'warning'
  return 'info'
}

async function load() {
  const data = await fetchUserStats({ date_from: range.value[0], date_to: range.value[1] })
  items.value = data.items
  await nextTick()
  const top = [...filtered.value].sort((a, b) => b.checkin_count - a.checkin_count).slice(0, 12)
  render({
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 24, top: 16, bottom: 24 },
    xAxis: { type: 'value', name: '签到次数' },
    yAxis: { type: 'category', data: top.map((item) => item.nickname || item.student_no).reverse() },
    series: [{ type: 'bar', data: top.map((item) => item.checkin_count).reverse(), color: ink, barMaxWidth: 18 }],
  })
}

onMounted(load)
</script>
