export function formatDate(date) {
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function recentRange(days = 30) {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - (days - 1))
  return [formatDate(start), formatDate(end)]
}

export function percent(value) {
  if (value === null || value === undefined) return '--'
  return `${(Number(value) * 100).toFixed(1)}%`
}
