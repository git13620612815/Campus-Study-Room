<template>
  <view class="page">
    <view class="card">
      <picker mode="date" :value="date" @change="onDate">
        <view class="picker">日期 {{ date }}</view>
      </picker>
      <scroll-view scroll-x class="slots">
        <view
          v-for="slot in slots"
          :key="slot.id"
          class="slot"
          :class="{ on: slot.id === slotId }"
          @click="chooseSlot(slot.id)"
        >{{ slot.name }} {{ slot.start_time }}</view>
      </scroll-view>
    </view>
    <view class="legend">
      <text><text class="dot" style="background:#22c55e"></text>空闲</text>
      <text><text class="dot" style="background:#f59e0b"></text>预约中</text>
      <text><text class="dot" style="background:#ef4444"></text>占用</text>
      <text><text class="dot" style="background:#9ca3af"></text>不可用</text>
    </view>
    <scroll-view scroll-x class="grid-wrap">
      <view class="grid" :style="{ gridTemplateColumns: `repeat(${columns}, 120rpx)` }">
        <view v-for="seat in seats" :key="seat.id" class="cell" :style="{ background: seat.color }" @click="openSeat(seat)">{{ seat.code }}</view>
      </view>
    </scroll-view>
    <view v-for="seat in seats" :key="`list-${seat.id}`" class="card seat" @click="openSeat(seat)">
      <view class="dot big" :style="{ background: seat.color }"></view>
      <view class="meta">
        <text class="code">{{ seat.code }}</text>
        <text class="muted">{{ seat.zone }}</text>
      </view>
      <text>{{ seat.status_label }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { request } from '../../api/http'

const roomId = ref('')
const roomName = ref('')
const date = ref('')
const slotId = ref(null)
const slots = ref([])
const seats = ref([])
const columns = computed(() => Math.max(1, ...seats.value.map((seat) => seat.col_no || 1)))

function today() {
  const now = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

onLoad((query) => {
  roomId.value = query.id
  roomName.value = decodeURIComponent(query.name || '')
  date.value = today()
  if (roomName.value) uni.setNavigationBarTitle({ title: roomName.value })
})

onShow(async () => {
  const room = await request({ url: `/rooms/${roomId.value}/` })
  slots.value = (room.slots || []).filter((slot) => slot.enabled)
  if (!slotId.value && slots.value.length) slotId.value = slots.value[0].id
  await loadSeats()
})

async function loadSeats() {
  if (!slotId.value) return
  const data = await request({ url: `/rooms/${roomId.value}/seats/`, data: { date: date.value, slot_id: slotId.value } })
  seats.value = data.seats
  uni.stopPullDownRefresh()
}

function onDate(event) {
  date.value = event.detail.value
  loadSeats()
}

function chooseSlot(id) {
  slotId.value = id
  loadSeats()
}

function openSeat(seat) {
  if (seat.can_book) {
    const slot = slots.value.find((item) => item.id === slotId.value)
    uni.setStorageSync('bookDraft', {
      seat_id: seat.id,
      slot_id: slotId.value,
      reserve_date: date.value,
      code: seat.code,
      zone: seat.zone,
      room_name: roomName.value,
      slot_name: slot?.name || '',
      start_time: slot?.start_time || '',
      end_time: slot?.end_time || '',
    })
    uni.navigateTo({ url: '/pages/book/book' })
    return
  }
  if (seat.is_mine && seat.status === 'reserved') {
    uni.showActionSheet({
      itemList: ['去签到', '取消预约'],
      success: async (res) => {
        if (res.tapIndex === 0) uni.navigateTo({ url: '/pages/checkin/checkin' })
        if (res.tapIndex === 1) {
          await request({ url: `/reservations/${seat.reservation_id}/cancel/`, method: 'POST' })
          uni.showToast({ title: '已取消', icon: 'none' })
          loadSeats()
        }
      },
    })
    return
  }
  uni.showToast({ title: seat.book_tip || '该时段已被预约', icon: 'none' })
}

onPullDownRefresh(loadSeats)
</script>

<style scoped>
.picker { padding: 8rpx 0 16rpx; color: #1f3d32; }
.slots { white-space: nowrap; }
.slot { display: inline-block; margin-right: 12rpx; padding: 12rpx 20rpx; border-radius: 999rpx; background: #f6f3ec; }
.slot.on { background: #1f3d32; color: white; }
.legend { display: flex; gap: 18rpx; margin: 8rpx 8rpx 16rpx; color: #57534e; }
.dot { width: 16rpx; height: 16rpx; border-radius: 50%; display: inline-block; margin-right: 8rpx; }
.grid-wrap { margin-bottom: 16rpx; }
.grid { display: grid; gap: 12rpx; }
.cell { height: 72rpx; border-radius: 16rpx; color: white; display: flex; align-items: center; justify-content: center; font-size: 22rpx; }
.seat { display: flex; align-items: center; gap: 18rpx; }
.big { width: 28rpx; height: 28rpx; }
.meta { flex: 1; display: flex; flex-direction: column; }
.code { font-weight: 650; }
</style>
