<template>
  <view class="page login">
    <text class="eyebrow">校园自习室</text>
    <text class="title">先选一个座位，到了再刷脸。</text>
    <view class="card">
      <input class="field" v-model="form.username" placeholder="用户名 / 学号" placeholder-class="field-placeholder" />
      <input class="field" v-model="form.password" password placeholder="密码" placeholder-class="field-placeholder" />
      <button class="primary" @click="submit">登录</button>
      <button class="ghost" @click="goRegister">注册学生账号</button>
    </view>
    <text class="muted hint">演示学生 student / student123456</text>
  </view>
</template>

<script setup>
import { reactive } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { request, saveAuth, getToken } from '../../api/http'

const form = reactive({ username: 'student', password: 'student123456' })

onShow(() => {
  if (getToken()) uni.switchTab({ url: '/pages/index/index' })
})

async function submit() {
  const data = await request({ url: '/auth/login/', method: 'POST', data: form, auth: false })
  saveAuth(data)
  uni.switchTab({ url: '/pages/index/index' })
}

function goRegister() {
  uni.navigateTo({ url: '/pages/register/register' })
}
</script>

<style scoped>
.login { padding-top: 80rpx; }
.eyebrow { color: #b8893a; letter-spacing: 6rpx; display: block; margin-bottom: 16rpx; }
.title { display: block; margin-bottom: 36rpx; line-height: 1.35; }
.field {
  display: block;
  width: 100%;
  height: 96rpx;
  margin-bottom: 24rpx;
  padding: 0 28rpx;
  border-radius: 16rpx;
  background: #f6f3ec;
  font-size: 30rpx;
  line-height: 96rpx;
  color: #1c1917;
  box-sizing: border-box;
}
.field-placeholder { color: #a8a29e; font-size: 30rpx; }
button { margin-top: 12rpx; }
.hint { display: block; margin-top: 24rpx; }
</style>
