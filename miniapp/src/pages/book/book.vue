<template>
  <view class="page" v-if="draft">
    <view class="card">
      <text class="title">确认预约</text>
      <text>{{ draft.room_name }}</text>
      <text>座位 {{ draft.code }} · {{ draft.zone }}</text>
      <text>{{ draft.reserve_date }} {{ draft.slot_name }} {{ draft.start_time }}-{{ draft.end_time }}</text>
    </view>
    <button class="primary" @click="submit">确认预约</button>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { request } from '../../api/http'

const draft = ref(null)

onShow(() => {
  draft.value = uni.getStorageSync('bookDraft')
})

async function submit() {
  try {
    await request({
      url: '/reservations/',
      method: 'POST',
      data: {
        seat_id: draft.value.seat_id,
        slot_id: draft.value.slot_id,
        reserve_date: draft.value.reserve_date,
      },
    })
    uni.removeStorageSync('bookDraft')
    uni.showToast({ title: '预约成功', icon: 'none' })
    setTimeout(() => uni.switchTab({ url: '/pages/records/records' }), 400)
  } catch {
    setTimeout(() => uni.navigateBack(), 600)
  }
}
</script>

<style scoped>
.card { display: flex; flex-direction: column; gap: 12rpx; }
.title { margin-bottom: 8rpx; }
button { margin-top: 12rpx; }
</style>
