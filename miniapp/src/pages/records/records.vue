<template>
  <view class="page">
    <view class="card filters">
      <picker mode="date" :value="dateFrom" @change="(event) => dateFrom = event.detail.value"><view>从 {{ dateFrom || '不限' }}</view></picker>
      <picker mode="date" :value="dateTo" @change="(event) => dateTo = event.detail.value"><view>到 {{ dateTo || '不限' }}</view></picker>
      <button class="primary tiny" @click="load">筛选</button>
      <button class="ghost tiny" @click="exportFile">导出</button>
    </view>
    <view v-if="!rows.length" class="card">没有符合条件的记录</view>
    <view v-for="item in rows" :key="item.id" class="card record">
      <view class="row">
        <text class="name">{{ item.room_name }} {{ item.seat_code }}</text>
        <text>{{ item.status_label }}</text>
      </view>
      <text class="muted">{{ item.reserve_date }} {{ item.slot_name }} {{ item.start_time }}-{{ item.end_time }}</text>
      <text class="muted">签到：{{ item.checkin_result }} {{ item.checkin_at }}</text>
      <text v-if="item.cancel_reason" class="muted">原因：{{ item.cancel_reason }}</text>
      <view class="actions">
        <button v-if="item.can_cancel" class="ghost tiny" @click="cancel(item)">取消</button>
        <button v-if="item.can_check_in" class="primary tiny" @click="goCheckin">签到</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { BASE_URL } from '../../config'
import { ensureLogin, getToken, request } from '../../api/http'

const rows = ref([])
const dateFrom = ref('')
const dateTo = ref('')

async function load() {
  if (!ensureLogin()) return
  const data = await request({
    url: '/reservations/mine/',
    data: { page: 1, page_size: 50, date_from: dateFrom.value, date_to: dateTo.value },
  })
  rows.value = data.results
  uni.stopPullDownRefresh()
}

async function cancel(item) {
  await request({ url: `/reservations/${item.id}/cancel/`, method: 'POST' })
  uni.showToast({ title: '已取消', icon: 'none' })
  load()
}

function goCheckin() {
  uni.navigateTo({ url: '/pages/checkin/checkin' })
}

function exportFile() {
  const query = `date_from=${dateFrom.value || ''}&date_to=${dateTo.value || ''}`
  uni.downloadFile({
    url: `${BASE_URL}/reservations/mine/export/?${query}`,
    header: { Authorization: `Bearer ${getToken()}` },
    success: (res) => {
      if (res.statusCode !== 200) {
        uni.showToast({ title: '导出失败', icon: 'none' })
        return
      }
      // #ifdef H5
      const link = document.createElement('a')
      link.href = res.tempFilePath
      link.download = '我的预约记录.xlsx'
      link.click()
      // #endif
      // #ifndef H5
      uni.openDocument({ filePath: res.tempFilePath, showMenu: true })
      // #endif
    },
  })
}

onShow(load)
onPullDownRefresh(load)
</script>

<style scoped>
.filters { display: flex; flex-wrap: wrap; gap: 12rpx; align-items: center; }
.record { display: flex; flex-direction: column; gap: 8rpx; }
.row { display: flex; justify-content: space-between; }
.name { font-weight: 650; color: #1f3d32; }
.actions { display: flex; gap: 12rpx; }
.tiny { width: auto; padding: 0 28rpx; line-height: 64rpx; font-size: 26rpx; }
</style>
