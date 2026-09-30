<template>
  <view class="page">
    <view class="card">
      <text class="title">{{ profile.nickname || '同学' }}</text>
      <text class="muted">{{ profile.student_no }} · {{ profile.phone }}</text>
      <text class="muted">人脸档案：{{ profile.face_enrolled ? '已采集' : '未采集' }}</text>
    </view>
    <view class="card">
      <input class="field" v-model="profile.nickname" placeholder="昵称" placeholder-class="field-placeholder" />
      <input class="field" v-model="profile.phone" placeholder="手机号" placeholder-class="field-placeholder" />
      <button class="primary" @click="save">保存资料</button>
    </view>
    <view class="card">
      <input class="field" v-model="password.old_password" password placeholder="原密码" placeholder-class="field-placeholder" />
      <input class="field" v-model="password.new_password" password placeholder="新密码" placeholder-class="field-placeholder" />
      <button class="ghost" @click="changePassword">修改密码</button>
    </view>
    <button class="primary" @click="enroll">上传照片采集人脸</button>
    <button class="ghost" style="margin-top: 16rpx" @click="logout">退出登录</button>
  </view>
</template>

<script setup>
import { reactive } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { clearAuth, ensureLogin, request, saveAuth, upload, getProfile } from '../../api/http'

const profile = reactive({ nickname: '', phone: '', student_no: '', face_enrolled: false })
const password = reactive({ old_password: '', new_password: '' })

async function load() {
  if (!ensureLogin()) return
  Object.assign(profile, await request({ url: '/users/me/' }))
}

async function save() {
  const data = await request({ url: '/users/me/', method: 'PATCH', data: { nickname: profile.nickname, phone: profile.phone } })
  Object.assign(profile, data)
  const cached = getProfile()
  saveAuth({ ...cached, access: uni.getStorageSync('access'), refresh: uni.getStorageSync('refresh'), nickname: data.nickname, face_enrolled: data.face_enrolled, role: data.role })
  uni.showToast({ title: '已保存', icon: 'none' })
}

async function changePassword() {
  await request({ url: '/users/me/password/', method: 'POST', data: password })
  password.old_password = ''
  password.new_password = ''
  uni.showToast({ title: '密码已更新', icon: 'none' })
}

function enroll() {
  uni.chooseImage({
    count: 1,
    sourceType: ['camera', 'album'],
    success: async (res) => {
      await upload('/face/enroll/', res.tempFilePaths[0])
      profile.face_enrolled = true
      uni.showToast({ title: '采集成功', icon: 'none' })
    },
  })
}

function logout() {
  clearAuth()
  uni.reLaunch({ url: '/pages/login/login' })
}

onShow(load)
</script>

<style scoped>
.card { display: flex; flex-direction: column; gap: 20rpx; }
.field {
  display: block;
  width: 100%;
  height: 96rpx;
  flex-shrink: 0;
  padding: 0 28rpx;
  border-radius: 16rpx;
  background: #f6f3ec;
  font-size: 30rpx;
  line-height: 96rpx;
  color: #1c1917;
  box-sizing: border-box;
}
.field-placeholder { color: #a8a29e; font-size: 30rpx; }
button { margin-top: 8rpx; }
</style>
