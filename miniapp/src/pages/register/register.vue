<template>
  <view class="page">
    <view class="card">
      <input v-model="form.username" placeholder="用户名，4-32 位字母数字" />
      <input v-model="form.student_no" placeholder="学号" />
      <input v-model="form.nickname" placeholder="昵称" />
      <input v-model="form.phone" placeholder="手机号" />
      <input v-model="form.password" password placeholder="密码，至少 6 位" />
      <button class="primary" @click="submit">注册并登录</button>
    </view>
  </view>
</template>

<script setup>
import { reactive } from 'vue'
import { request, saveAuth } from '../../api/http'

const form = reactive({ username: '', student_no: '', nickname: '', phone: '', password: '' })

async function submit() {
  await request({ url: '/auth/register/', method: 'POST', data: form, auth: false })
  const data = await request({
    url: '/auth/login/',
    method: 'POST',
    auth: false,
    data: { username: form.username, password: form.password },
  })
  saveAuth(data)
  uni.switchTab({ url: '/pages/index/index' })
}
</script>

<style scoped>
input { background: #f6f3ec; border-radius: 16rpx; padding: 22rpx 24rpx; margin-bottom: 20rpx; }
</style>
