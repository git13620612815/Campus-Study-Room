import { onBeforeUnmount, onMounted } from 'vue'
import * as echarts from 'echarts'

export function useChart(target) {
  let chart
  function render(option) {
    if (!target.value) return
    if (!chart) chart = echarts.init(target.value)
    chart.setOption(option, true)
  }
  function resize() {
    chart?.resize()
  }
  onMounted(() => window.addEventListener('resize', resize))
  onBeforeUnmount(() => {
    window.removeEventListener('resize', resize)
    chart?.dispose()
    chart = null
  })
  return { render }
}

export const ink = '#1f3d32'
export const gold = '#b8893a'
