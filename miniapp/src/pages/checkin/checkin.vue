<template>
  <view class="page">
    <view class="card" v-if="!faceEnrolled">
      <text>还没有采集人脸，签到前需要一张正脸照片。</text>
      <button class="ghost" @click="goProfile">去采集</button>
    </view>
    <view v-if="!ready.length" class="card">当前没有可签到的预约。未到开始时间也可以签到，开始后请在 15 分钟内完成。</view>
    <view v-for="item in ready" :key="item.id" class="card">
      <text class="name">{{ item.room_name }} · {{ item.seat_code }}</text>
      <text class="muted">{{ item.reserve_date }} {{ item.slot_name }} {{ item.start_time }}-{{ item.end_time }}</text>
      <button class="primary" @click="shoot(item)">拍照签到</button>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { ensureLogin, request, upload } from '../../api/http'

const ready = ref([])
const faceEnrolled = ref(true)

async function load() {
  if (!ensureLogin()) return
  const face = await request({ url: '/face/status/' })
  faceEnrolled.value = face.face_enrolled
  const data = await request({ url: '/reservations/mine/', data: { page: 1, page_size: 50, status: 'pending' } })
  ready.value = data.results.filter((item) => item.can_check_in)
}

function goProfile() {
  uni.switchTab({ url: '/pages/profile/profile' })
}

function shoot(item) {
  uni.chooseImage({
    count: 1,
    sourceType: ['camera'],
    success: async (res) => {
      const data = await upload(`/reservations/${item.id}/check-in/`, res.tempFilePaths[0])
      uni.showModal({
        title: '签到成功',
        content: `${data.room_name || item.room_name} ${data.seat_code}，请在 ${data.end_at} 前使用`,
        showCancel: false,
      })
      load()
    },
  })
}

onShow(load)
</script>

<style scoped>
.card { display: flex; flex-direction: column; gap: 12rpx; }
.name { font-size: 32rpx; font-weight: 650; color: #1f3d32; }
button { margin-top: 8rpx; }
</style>
