<template>
  <view class="page">
    <text class="title">今天去哪自习</text>
    <text class="muted">只显示正在开放的自习室</text>
    <view v-if="!rooms.length" class="card empty">暂时没有开放的自习室</view>
    <view v-for="room in rooms" :key="room.id" class="card room" @click="openRoom(room)">
      <view class="row">
        <text class="name">{{ room.name }}</text>
        <text class="pill">{{ room.status_label }}</text>
      </view>
      <text class="muted">{{ room.building }} {{ room.floor }} · {{ room.enabled_seat_count }} 个可用座位</text>
      <text class="facilities">{{ room.facilities || '设施待补充' }}</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { ensureLogin, request } from '../../api/http'

const rooms = ref([])

async function load() {
  if (!ensureLogin()) return
  rooms.value = await request({ url: '/rooms/' })
  uni.stopPullDownRefresh()
}

function openRoom(room) {
  uni.setStorageSync('currentRoom', room)
  uni.navigateTo({ url: `/pages/room/room?id=${room.id}&name=${encodeURIComponent(room.name)}` })
}

onShow(load)
onPullDownRefresh(load)
</script>

<style scoped>
.title { display: block; margin: 12rpx 0 8rpx; }
.room { display: flex; flex-direction: column; gap: 10rpx; }
.row { display: flex; justify-content: space-between; align-items: center; }
.name { font-size: 34rpx; font-weight: 650; color: #1f3d32; }
.pill { background: #e7efe9; color: #1f3d32; border-radius: 999rpx; padding: 6rpx 16rpx; font-size: 22rpx; }
.facilities { color: #57534e; }
.empty { text-align: center; color: #78716c; }
</style>
