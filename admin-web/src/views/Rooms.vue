<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>自习室</h1>
        <p>开放、关闭和维护会立即影响学生能否预约。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建自习室</el-button>
    </div>
    <div class="panel">
      <el-table :data="rooms" v-loading="loading">
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="building" label="楼栋" width="120" />
        <el-table-column prop="floor" label="楼层" width="80" />
        <el-table-column prop="facilities" label="设施" min-width="160" />
        <el-table-column prop="enabled_seat_count" label="可用座位" width="100" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link @click="openEdit(row)">编辑</el-button>
              <el-button link @click="openSlots(row)">时段</el-button>
              <el-button link @click="$router.push(`/rooms/${row.id}/seats`)">座位</el-button>
              <el-dropdown trigger="click" @command="(status) => changeStatus(row, status)">
                <el-button link>状态</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="open">开放</el-dropdown-item>
                    <el-dropdown-item command="closed">关闭</el-dropdown-item>
                    <el-dropdown-item command="maintenance">维护</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="roomDialog" :title="form.id ? '编辑自习室' : '新建自习室'" width="520px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="楼栋"><el-input v-model="form.building" /></el-form-item>
        <el-form-item label="楼层"><el-input v-model="form.floor" /></el-form-item>
        <el-form-item label="设施"><el-input v-model="form.facilities" placeholder="插座,空调,台灯" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roomDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRoom">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="slotDialog" title="可预约时段" width="680px">
      <el-table :data="slotRows">
        <el-table-column label="名称" min-width="140">
          <template #default="{ row }"><el-input v-model="row.name" /></template>
        </el-table-column>
        <el-table-column label="开始" width="140">
          <template #default="{ row }"><el-time-picker v-model="row.start_time" value-format="HH:mm" format="HH:mm" /></template>
        </el-table-column>
        <el-table-column label="结束" width="140">
          <template #default="{ row }"><el-time-picker v-model="row.end_time" value-format="HH:mm" format="HH:mm" /></template>
        </el-table-column>
        <el-table-column label="启用" width="80">
          <template #default="{ row }"><el-switch v-model="row.enabled" /></template>
        </el-table-column>
        <el-table-column width="80">
          <template #default="{ $index }"><el-button link @click="slotRows.splice($index, 1)">删除</el-button></template>
        </el-table-column>
      </el-table>
      <el-button style="margin-top: 12px" @click="slotRows.push({ name: '', start_time: '08:00', end_time: '10:00', enabled: true })">添加时段</el-button>
      <template #footer>
        <el-button @click="slotDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSlots">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { createRoom, fetchRooms, replaceSlots, updateRoom } from '../api'

const rooms = ref([])
const loading = ref(false)
const roomDialog = ref(false)
const slotDialog = ref(false)
const slotRows = ref([])
const slotRoomId = ref(null)
const form = reactive({ id: null, name: '', building: '', floor: '', facilities: '', description: '' })

function tagType(status) {
  if (status === 'open') return 'success'
  if (status === 'maintenance') return 'warning'
  return 'info'
}

async function load() {
  loading.value = true
  try { rooms.value = await fetchRooms() } finally { loading.value = false }
}

function openCreate() {
  Object.assign(form, { id: null, name: '', building: '', floor: '', facilities: '', description: '' })
  roomDialog.value = true
}

function openEdit(row) {
  Object.assign(form, row)
  roomDialog.value = true
}

async function saveRoom() {
  const payload = { name: form.name, building: form.building, floor: form.floor, facilities: form.facilities, description: form.description }
  if (form.id) await updateRoom(form.id, payload)
  else await createRoom(payload)
  roomDialog.value = false
  load()
}

function openSlots(row) {
  slotRoomId.value = row.id
  slotRows.value = row.slots.map((slot) => ({ ...slot }))
  slotDialog.value = true
}

async function saveSlots() {
  await replaceSlots(slotRoomId.value, { slots: slotRows.value })
  slotDialog.value = false
  load()
}

async function changeStatus(row, status) {
  if (status === row.status) return
  if (status !== 'open') {
    await ElMessageBox.confirm('关闭或维护后，尚未开始的预约会被取消。', '修改自习室状态')
  }
  await updateRoom(row.id, { status })
  load()
}

onMounted(load)
</script>

<style scoped>
.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.row-actions :deep(.el-button) {
  margin: 0;
  height: 32px;
  vertical-align: middle;
}
.row-actions :deep(.el-dropdown) {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
  line-height: inherit;
}
</style>
