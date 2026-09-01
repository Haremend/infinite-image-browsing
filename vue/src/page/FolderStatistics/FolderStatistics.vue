<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useGlobalStore } from '@/store/useGlobalStore'
import { uniqueId } from 'lodash-es'
// @ts-ignore
import { RecycleScroller } from '@zanllp/vue-virtual-scroller'
import {
  startScan,
  getScanStatus,
  getResult,
  type FolderCountItem,
  type FolderCountStatusResp,
} from '@/api/folderStats'
import { t } from '@/i18n'
import { message } from 'ant-design-vue'

defineProps<{
  tabIdx: number
  paneIdx: number
  paneKey: string
}>()

const global = useGlobalStore()

const LS_KEY = 'iib_folder_stats_last_path'
const folderPath = ref<string>(localStorage.getItem(LS_KEY) ?? '')

const result = ref<FolderCountItem[]>([])
const total = ref(0)
const countedAt = ref<string | null>(null)
const loading = ref(false)
const scanning = ref(false)
const jobId = ref<string | null>(null)
const scanStatus = ref<FolderCountStatusResp | null>(null)
const error = ref<string | null>(null)
const sortDir = ref<'desc' | 'asc'>('desc')
let pollTimer: number | null = null

const sortedResult = computed(() =>
  result.value
    .slice()
    .sort((a, b) => (sortDir.value === 'desc' ? b.count - a.count : a.count - b.count))
)

const hasResult = computed(() => result.value.length > 0 || !!countedAt.value)

function setLastPath(p: string) {
  folderPath.value = p
  try {
    localStorage.setItem(LS_KEY, p)
  } catch {
    /* ignore storage errors */
  }
}

async function loadResult(path: string) {
  if (!path) return
  loading.value = true
  error.value = null
  try {
    const res = await getResult(path)
    result.value = res.result ?? []
    total.value = res.total ?? 0
    countedAt.value = res.counted_at ?? null
  } catch (e: any) {
    error.value = e?.message ?? String(e)
  } finally {
    loading.value = false
  }
}

async function startStatistics() {
  const path = folderPath.value.trim()
  if (!path) {
    message.warning(t('folderStatisticsInputTip'))
    return
  }
  setLastPath(path)
  scanning.value = true
  scanStatus.value = null
  error.value = null
  result.value = []
  total.value = 0
  countedAt.value = null
  try {
    const { job_id } = await startScan(path)
    jobId.value = job_id
    startPolling()
  } catch (e: any) {
    scanning.value = false
    error.value = e?.response?.data?.detail ?? e?.message ?? String(e)
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(pollOnce, 2000)
}

function stopPolling() {
  if (pollTimer != null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollOnce() {
  if (!jobId.value) return
  try {
    const s = await getScanStatus(jobId.value)
    scanStatus.value = s
    if (s.status === 'done') {
      stopPolling()
      scanning.value = false
      if (s.result) {
        result.value = s.result
        total.value = s.total ?? 0
      }
      // 同步读表，拿到 counted_at 等持久化字段
      await loadResult(folderPath.value.trim())
    } else if (s.status === 'error') {
      stopPolling()
      scanning.value = false
      error.value = s.error ?? 'scan error'
    }
  } catch {
    // 网络抖动忽略，继续轮询
  }
}

function toggleSort() {
  sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
}

function openInStackView(fullpath: string) {
  // pane 系统既定模式：构造 FileTransferTabPane 推入 tab 并激活，stackView 收到 path 自动导航
  const tab = global.tabList[0]
  if (!tab) return
  const pane = {
    type: 'local' as const,
    path: fullpath,
    key: uniqueId(),
    name: '',
    mode: 'scanned' as const,
  }
  tab.panes.push(pane)
  tab.key = pane.key
}

onMounted(() => {
  const p = folderPath.value
  if (p) loadResult(p)
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="folder-stats">
    <!-- 顶部：路径输入 + 按钮 -->
    <div class="toolbar">
      <a-input
        v-model:value="folderPath"
        :placeholder="t('folderStatisticsInputPlaceholder')"
        allow-clear
        @press-enter="startStatistics()"
      />
      <a-button type="primary" :loading="scanning" @click="startStatistics()">
        {{ hasResult ? t('forceRescan') : t('scanStatistics') }}
      </a-button>
    </div>

    <!-- 进度 -->
    <div v-if="scanning && scanStatus" class="progress">
      <a-spin size="small" />
      <span>
        {{ t('scannedFolders') }}: {{ scanStatus.scanned ?? 0 }}　/
        {{ t('countedFiles') }}: {{ scanStatus.counted ?? 0 }}
      </span>
    </div>

    <a-alert
      v-if="error"
      type="error"
      :message="error"
      show-icon
      closable
      style="margin: 8px 0"
      @close="error = null"
    />

    <div v-if="loading" class="loading"><a-spin /></div>

    <!-- 结果表 -->
    <template v-else-if="sortedResult.length">
      <div class="summary">
        <span>{{ t('countedFiles') }}: {{ total }}</span>
        <span v-if="countedAt">{{ t('lastCountedAt') }}: {{ countedAt }}</span>
      </div>
      <div class="table-head">
        <span class="col-path">{{ t('folderPath') }}</span>
        <span class="col-count sort-head" @click="toggleSort">
          {{ t('fileCount') }}
          <span class="sort-arrow">{{ sortDir === 'desc' ? '▼' : '▲' }}</span>
        </span>
        <span class="col-op">{{ t('operation') }}</span>
      </div>
      <RecycleScroller
        class="table-body"
        :items="sortedResult"
        :item-size="44"
        key-field="path"
        v-slot="{ item }"
      >
        <div class="table-row">
          <span class="col-path" :title="item.path">{{ item.path }}</span>
          <span class="col-count">{{ item.count }}</span>
          <span class="col-op">
            <a-button size="small" type="link" @click="openInStackView(item.path)">
              {{ t('openInStackView') }}
            </a-button>
          </span>
        </div>
      </RecycleScroller>
    </template>

    <a-empty v-else :description="t('folderStatisticsEmpty')" style="margin-top: 48px" />
  </div>
</template>

<style scoped lang="scss">
.folder-stats {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 12px;
  box-sizing: border-box;
  gap: 8px;
}

.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.progress {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  opacity: 0.85;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}

.summary {
  display: flex;
  gap: 24px;
  font-size: 13px;
  opacity: 0.85;
  padding: 4px 0;
}

.table-head,
.table-row {
  display: flex;
  align-items: center;
  width: 100%;
  box-sizing: border-box;
  padding: 0 8px;
}

.table-head {
  font-weight: 600;
  font-size: 13px;
  border-bottom: 1px solid var(--zp-border-color, #eee);
  padding: 6px 8px;
}

.table-row {
  height: 44px;
  border-bottom: 1px solid var(--zp-light-background, #f5f5f5);
}

.col-path {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-count {
  flex: 0 0 120px;
  text-align: right;
}

.col-op {
  flex: 0 0 160px;
  text-align: right;
}

.sort-head {
  cursor: pointer;
  user-select: none;
}

.sort-arrow {
  margin-left: 4px;
  font-size: 11px;
}

.table-body {
  flex: 1 1 0;
  min-height: 0;
  overflow: auto;
}
</style>
