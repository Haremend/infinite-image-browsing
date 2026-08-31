<script setup lang="ts">
// @ts-ignore
import { RecycleScroller } from '@zanllp/vue-virtual-scroller'
import '@zanllp/vue-virtual-scroller/dist/vue-virtual-scroller.css'
import { useGlobalStore } from '@/store/useGlobalStore'
import { useTagStore } from '@/store/useTagStore'
import { FileNodeInfo } from '@/api/files'
import { isImageFile, isVideoFile, isAudioFile, isMediaFile } from '@/util/file'
import { openVideoModal, openAudioModal } from '@/components/functionalCallableComp'
import { SortMethod } from '@/page/fileTransfer/fileSort'
import { ref, computed, h } from 'vue'
import {
  FileOutlined,
  FolderOpenOutlined,
  CaretUpOutlined,
  CaretDownOutlined,
  PictureOutlined,
  VideoCameraOutlined,
  SoundOutlined,
  EllipsisOutlined,
  HeartOutlined,
  HeartFilled,
  StarFilled,
  StarOutlined,
  DragOutlined,
  EyeOutlined,
  DownloadOutlined
} from '@/icon'
import { message, Modal } from 'ant-design-vue'
import { getImageGenerationInfo, downloadMetaImage as apiDownloadMetaImage } from '@/api'
import { t } from '@/i18n'
import ContextMenu from './ContextMenu.vue'
import DraggableImage from './DraggableImage.vue'
import type { MenuInfo } from 'ant-design-vue/lib/menu/src/interface'
import { fallbackImage } from 'vue3-ts-util'
import type { Tag } from '@/api/db'
import { ok } from 'vue3-ts-util'
import RetryableImage from './RetryableImage.vue'

const global = useGlobalStore()
const tagStore = useTagStore()

const props = defineProps<{
  files: FileNodeInfo[]
  sortMethod: SortMethod
  cellWidth?: number
  /** 当前全屏预览图片的 url,与非列表视图一致,用于 a-image preview 翻页 */
  fullScreenPreviewImageUrl?: string
  selected?: boolean
  isSelectedMutilFiles?: boolean
}>()

const emit = defineEmits<{
  'fileItemClick': [event: MouseEvent, file: FileNodeInfo, idx: number]
  'contextMenuClick': [e: MenuInfo, file: FileNodeInfo, idx: number]
  'dragstart': [event: DragEvent, idx: number]
  'dragend': [event: DragEvent, idx: number]
  'dropToFolder': [event: DragEvent, file: FileNodeInfo, idx: number]
  'update:sortMethod': [method: SortMethod]
  'previewVisibleChange': [value: boolean, last: boolean]
}>()

const ITEM_HEIGHT = 36
const showMenuIdx = ref(-1)

type SortField = 'name' | 'date' | 'size'
type SortOrder = 'asc' | 'desc'

// Derive sort field and order from current sortMethod
const sortInfo = computed(() => {
  const m = props.sortMethod
  if (m.startsWith('name-')) return { field: 'name' as SortField, order: m.endsWith('asc') ? 'asc' as SortOrder : 'desc' as SortOrder }
  if (m.startsWith('date-')) return { field: 'date' as SortField, order: m.endsWith('asc') ? 'asc' as SortOrder : 'desc' as SortOrder }
  if (m.startsWith('size-')) return { field: 'size' as SortField, order: m.endsWith('asc') ? 'asc' as SortOrder : 'desc' as SortOrder }
  if (m.startsWith('created-time-')) return { field: 'date' as SortField, order: m.endsWith('asc') ? 'asc' as SortOrder : 'desc' as SortOrder }
  return { field: null, order: 'asc' as SortOrder }
})

const onColumnClick = (field: SortField) => {
  const currentInfo = sortInfo.value
  if (currentInfo.field === field) {
    // Toggle order
    const newOrder = currentInfo.order === 'asc' ? 'desc' : 'asc'
    emit('update:sortMethod', `${field}-${newOrder}` as SortMethod)
  } else {
    // Set new field with default ascending
    emit('update:sortMethod', `${field}-asc` as SortMethod)
  }
}

const getSortIcon = (field: SortField) => {
  const info = sortInfo.value
  if (info.field !== field) return 'none'
  return info.order
}

const getFileIcon = (file: FileNodeInfo) => {
  if (file.type === 'dir') return 'folder'
  if (isImageFile(file.name)) return 'image'
  if (isVideoFile(file.name)) return 'video'
  if (isAudioFile(file.name)) return 'audio'
  return 'file'
}

const handleDrop = (event: DragEvent, file: FileNodeInfo, idx: number) => {
  if (file.type === 'dir') {
    event.preventDefault()
    event.stopPropagation()
    emit('dropToFolder', event, file, idx)
  }
}

const handleDragOver = (event: DragEvent, file: FileNodeInfo) => {
  if (file.type === 'dir') {
    event.preventDefault()
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move'
    }
  }
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// ===== 全屏预览相关 =====
// AImage 组件未通过 defineExpose 暴露打开预览的方法，
// 这里直接在双击的行内查找隐藏的 a-image 图片元素并模拟点击来打开全屏预览
// （与工具方法 openImageFullscreenPreview 同思路，作用域限定到当前行更精确）

// 当前全屏预览源图（与非列表视图保持一致行为，用于 a-image preview 翻页）
const previewSrc = computed(() => props.fullScreenPreviewImageUrl || '')

// 行内隐藏 a-image 的 src。该 <img> 仅作为「双击行 / 跳转目标文件时点击触发全屏预览」的锚点，
// 自身从不展示（外层 .hidden-preview-wrap 已设为 1px / 透明 / pointer-events:none）。
// 用内联 1x1 透明像素，保证 a-image 始终渲染出可被 querySelector('.idx-N .ant-image-img')
// 命中并点击的 <img>，同时彻底避免列表滚动时对每一行发起 image-thumbnail / 原图请求
// （网速慢 + 几十 MB 大图时，这些请求会挤占浏览器并发连接、触发 _r 重试，并拖慢
// 「查看元数据」等其他接口）。全屏预览实际显示的图片由 :preview.src（fullScreenPreviewImageUrl
// = 原图 URL）决定，与此处 src 无关。
const TRANSPARENT_PIXEL =
  'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
const cellThumbUrl = (file: FileNodeInfo) => {
  if (!isImageFile(file.name)) return ''
  return TRANSPARENT_PIXEL
}

const openPreview = (file: FileNodeInfo, e: MouseEvent) => {
  if (!isImageFile(file.name)) return
  // 在双击的行 DOM 内查找隐藏的 a-image 图片元素并模拟点击
  // （AImage 组件未 expose 打开预览的方法，点击图片本身即可触发其内部的全屏预览）
  const row = e.currentTarget as HTMLElement | null
  const img = row?.querySelector('.hidden-preview-wrap .ant-image-img') as HTMLImageElement | null
  if (img) {
    img.click()
  }
}

// 双击行触发原图预览（与非列表视图点图片预览保持一致）
const onRowDblClick = (e: MouseEvent, file: FileNodeInfo) => {
  if (file.type !== 'file') return // 文件夹不预览
  if (isImageFile(file.name)) {
    e.preventDefault()
    e.stopPropagation()
    openPreview(file, e)
  }
}

// ===== 视频和音频点击打开 modal（与非列表视图一致）=====
const onMediaIconClick = (e: MouseEvent, file: FileNodeInfo, idx: number) => {
  if (file.type !== 'file') return
  e.stopPropagation()
  if (isVideoFile(file.name)) {
    openVideoModal(
      file,
      (id) => emit('contextMenuClick', { key: `toggle-tag-${id}` } as MenuInfo, file, idx),
      () => emit('contextMenuClick', { key: 'tiktokView' } as MenuInfo, file, idx)
    )
  } else if (isAudioFile(file.name)) {
    openAudioModal(
      file,
      (id) => emit('contextMenuClick', { key: `toggle-tag-${id}` } as MenuInfo, file, idx),
      () => emit('contextMenuClick', { key: 'tiktokView' } as MenuInfo, file, idx)
    )
  }
}

// ===== 点赞 tag 相关（与非列表视图一致）=====
const customTags = (file: FileNodeInfo) => tagStore.tagMap.get(file.fullpath) ?? []

const allTags = computed(() => (global.conf?.all_custom_tags ?? []) as Tag[])

const fileTags = (file: FileNodeInfo) => {
  const tags = customTags(file)
  return allTags.value.reduce((p, c) => {
    return [...p, { ...c, selected: !!tags.find((v) => v.id === c.id) }]
  }, [] as (Tag & { selected: boolean })[])
}

const likeTag = computed<Tag | undefined>(() =>
  allTags.value.find(v => v.type === 'custom' && v.name === 'like')
)

const toggleLikeTag = (file: FileNodeInfo, idx: number, e: MouseEvent) => {
  e.stopPropagation()
  ok(likeTag.value)
  emit('contextMenuClick', { key: `toggle-tag-${likeTag.value.id}` } as MenuInfo, file, idx)
}

// ===== 查看元数据（与 more 菜单里的「查看生成信息(prompt等)」按钮功能一致）=====
const onViewGenInfo = (file: FileNodeInfo, idx: number, e: MouseEvent) => {
  if (file.type !== 'file' || !isMediaFile(file.name)) return
  e.stopPropagation()
  emit('contextMenuClick', { key: 'viewGenInfo' } as MenuInfo, file, idx)
}

// ===== 下载图片格式元数据 =====
const onDownloadMetadata = async (file: FileNodeInfo, e: MouseEvent) => {
  if (file.type !== 'file' || !file.name.toLowerCase().endsWith('.png')) return
  e.stopPropagation()

  Modal.confirm({
    title: t('downloadMeta'),
    content: () => h('input', {
      id: 'meta-input',
      placeholder: t('downloadMeta'),
      maxLength: 30,
      autofocus: true,
      style: 'width:100%;box-sizing:border-box;padding:4px 8px;'
    }) as any,
    okText: t('confirm'),
    cancelText: t('cancel'),
    width: 380,
    onOk: async () => {
      const input = document.getElementById('meta-input') as HTMLInputElement
      const userText = input?.value?.trim() || ''
      if (!userText) {
        message.warning(t('pleaseInputMetadataLabel'))
        return false
      }
      const geninfo = await getImageGenerationInfo(file.fullpath)
      if (!geninfo) {
        message.warning(t('noGeninfo'))
        return false
      }
      const blob = await apiDownloadMetaImage(file.fullpath, userText)
      const base = file.name.replace(/\.[^/.]+$/, '')
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${base}_meta_${userText}.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      return true
    }
  })
}
</script>

<template>
  <div class="list-view-container">
    <!-- Column Headers -->
    <div class="list-header">
      <div class="col-icon"></div>
      <div class="col-name sortable" @click="onColumnClick('name')">
        <span class="col-label">{{ $t('fileName') }}</span>
        <span class="sort-icon" :class="{ active: getSortIcon('name') !== 'none' }">
          <CaretUpOutlined v-if="getSortIcon('name') === 'asc'" />
          <CaretDownOutlined v-if="getSortIcon('name') === 'desc'" />
        </span>
      </div>
      <div class="col-meta">{{ $t('viewGenerationInfo') }}</div>
      <div class="col-date sortable" @click="onColumnClick('date')">
        <span class="col-label">{{ $t('modifiedDate') }}</span>
        <span class="sort-icon" :class="{ active: getSortIcon('date') !== 'none' }">
          <CaretUpOutlined v-if="getSortIcon('date') === 'asc'" />
          <CaretDownOutlined v-if="getSortIcon('date') === 'desc'" />
        </span>
      </div>
      <div class="col-size sortable" @click="onColumnClick('size')">
        <span class="col-label">{{ $t('fileSize') }}</span>
        <span class="sort-icon" :class="{ active: getSortIcon('size') !== 'none' }">
          <CaretUpOutlined v-if="getSortIcon('size') === 'asc'" />
          <CaretDownOutlined v-if="getSortIcon('size') === 'desc'" />
        </span>
      </div>
      <div class="col-actions"></div>
    </div>

    <!-- File List -->
    <RecycleScroller
      class="list-body"
      :items="files"
      :item-size="ITEM_HEIGHT"
      key-field="fullpath"
    >
      <template v-slot="{ item: file, index: idx }">
        <a-dropdown
          :trigger="['contextmenu']"
          :visible="showMenuIdx === idx"
          @update:visible="(v: boolean) => showMenuIdx = v ? idx : -1"
        >
          <div
            class="list-row file-item-trigger"
            :class="{ 'is-dir': file.type === 'dir' }"
            :data-idx="idx"
            draggable="true"
            @dragstart="emit('dragstart', $event, idx)"
            @dragend="emit('dragend', $event, idx)"
            @dragover="handleDragOver($event, file)"
            @drop="handleDrop($event, file, idx)"
            @click="emit('fileItemClick', $event, file, idx)"
            @dblclick="onRowDblClick($event, file)"
          >
            <!-- 隐藏的 RetryableImage，双击行时点击其内部图片触发全屏预览；idx-${idx} 用于全屏预览滚动定位 -->
            <div v-if="isImageFile(file.name)" :class="`idx-${idx}`" class="hidden-preview-wrap">
              <RetryableImage
                class="hidden-preview"
                :src="cellThumbUrl(file)"
                :fallback="fallbackImage"
                :preview="{
                  src: previewSrc,
                  onVisibleChange: (v: boolean, lv: boolean) => emit('previewVisibleChange', v, lv)
                }"
              />
            </div>
            <div class="col-icon" @click="onMediaIconClick($event, file, idx)">
              <folder-open-outlined v-if="getFileIcon(file) === 'folder'" class="file-icon folder-icon" />
              <picture-outlined v-else-if="getFileIcon(file) === 'image'" class="file-icon image-icon" />
              <video-camera-outlined v-else-if="getFileIcon(file) === 'video'" class="file-icon video-icon" />
              <sound-outlined v-else-if="getFileIcon(file) === 'audio'" class="file-icon audio-icon" />
              <file-outlined v-else class="file-icon" />
            </div>
            <div class="col-name" :title="file.name">
              <span class="file-name-text">{{ file.name }}</span>
              <div class="tags-inline" v-if="file.type !== 'dir'">
                <a-tag
                  v-for="tag in (tagStore.tagMap.get(file.fullpath) ?? [])"
                  :key="tag.id"
                  :color="tagStore.getColor(tag)"
                  class="inline-tag"
                >
                  {{ tag.name }}
                </a-tag>
              </div>
            </div>
            <div class="col-meta" @click.stop>
              <div
                v-if="file.type === 'file' && isMediaFile(file.name)"
                class="action-btn"
                :title="$t('viewGenerationInfo')"
                @click="onViewGenInfo(file, idx, $event)"
              >
                <eye-outlined />
              </div>
              <div
                v-if="file.type === 'file' && file.name.toLowerCase().endsWith('.png')"
                class="action-btn"
                :title="$t('downloadMeta')"
                @click="onDownloadMetadata(file, $event)"
              >
                <download-outlined />
              </div>
            </div>
            <div class="col-date">{{ file.date }}</div>
            <div class="col-size">{{ file.type === 'dir' ? '--' : formatFileSize(file.bytes) }}</div>
            <div class="col-actions" @click.stop>
              <!-- 点赞 -->
              <a-dropdown v-if="file.type === 'file'">
                <div class="action-btn" :class="{ 'like-selected': fileTags(file).find(v => v.name === 'like')?.selected }" @click="toggleLikeTag(file, idx, $event)">
                  <HeartFilled v-if="fileTags(file).find(v => v.name === 'like')?.selected" />
                  <HeartOutlined v-else />
                </div>
                <template #overlay>
                  <a-menu @click="emit('contextMenuClick', $event, file, idx)" v-if="fileTags(file).length > 1">
                    <a-menu-item v-for="tag in fileTags(file)" :key="`toggle-tag-${tag.id}`">{{ tag.name }}
                      <star-filled v-if="tag.selected" /><star-outlined v-else />
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
              <!-- 拖拽图片（仅图片） -->
              <DraggableImage size="192px" v-if="file.type === 'file' && isImageFile(file.fullpath)" :file="file">
                <div class="action-btn">
                  <DragOutlined />
                </div>
              </DraggableImage>
              <!-- more 菜单（完整右键菜单） -->
              <a-dropdown>
                <div class="action-btn">
                  <ellipsis-outlined />
                </div>
                <template #overlay>
                  <context-menu
                    :file="file"
                    :idx="idx"
                    :selected-tag="customTags(file)"
                    :is-selected-mutil-files="isSelectedMutilFiles"
                    @context-menu-click="(e, f, i) => emit('contextMenuClick', e, f, i)"
                  />
                </template>
              </a-dropdown>
            </div>
          </div>
          <template #overlay>
            <context-menu
              :file="file"
              :idx="idx"
              :selected-tag="tagStore.tagMap.get(file.fullpath) ?? []"
              @context-menu-click="(e, f, i) => emit('contextMenuClick', e, f, i)"
            />
          </template>
        </a-dropdown>
      </template>
    </RecycleScroller>
  </div>
</template>

<style lang="scss" scoped>
.list-view-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--zp-primary-background);
}

.list-header {
  display: flex;
  align-items: center;
  padding: 0 12px;
  height: 36px;
  background: var(--zp-secondary-background);
  border-bottom: 2px solid var(--zp-border);
  font-weight: 600;
  font-size: 13px;
  color: var(--zp-primary);
  user-select: none;
  flex-shrink: 0;

  .sortable {
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: background 0.15s;

    &:hover {
      background: var(--zp-secondary-variant-background);
    }

    .sort-icon {
      font-size: 12px;
      opacity: 0.3;
      transition: opacity 0.15s;

      &.active {
        opacity: 1;
        color: var(--zp-primary-color, #d03f0a);
      }
    }
  }
}

.list-body {
  flex: 1;
  overflow: auto;
}

.list-row {
  display: flex;
  align-items: center;
  padding: 0 12px;
  height: 36px;
  border-bottom: 1px solid var(--zp-border);
  cursor: default;
  transition: background 0.1s;
  font-size: 13px;

  &:hover {
    background: var(--zp-secondary-variant-background);
  }

  &.is-dir {
    cursor: pointer;
    font-weight: 500;
  }
}

.col-icon {
  width: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;

  .file-icon {
    font-size: 18px;
    color: var(--zp-secondary);
  }

  .folder-icon {
    color: #f5c542;
  }

  .image-icon {
    color: #4caf50;
  }

  .video-icon {
    color: #e91e63;
  }

  .audio-icon {
    color: #9c27b0;
  }
}

.col-name {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;

  .file-name-text {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 1;
    min-width: 0;
  }

  .tags-inline {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
    overflow: hidden;

    .inline-tag {
      margin: 0;
      font-size: 11px;
      line-height: 18px;
      padding: 0 6px;
      border-radius: 3px;
    }
  }
}

.col-date {
  width: 170px;
  flex-shrink: 0;
  text-align: right;
  padding-right: 12px;
  font-size: 12px;
  color: var(--zp-secondary);
}

.col-meta {
  width: 140px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.col-size {
  width: 90px;
  flex-shrink: 0;
  text-align: right;
  font-size: 12px;
  color: var(--zp-secondary);
}

.col-actions {
  width: 110px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 100vh;
  cursor: pointer;
  color: var(--zp-secondary);
  font-size: 16px;
  transition: all 0.15s;

  &:hover {
    color: var(--zp-primary-color, #d03f0a);
    background: var(--zp-secondary-variant-background);
  }

  &.like-selected {
    color: rgb(223, 5, 5);
  }
}

.hidden-preview-wrap {
  // 不用 display:none，否则 a-image 内部可能不会渲染 <img> 导致无法点击触发预览。
  // 改为绝对定位 + 0 尺寸 + 透明，保留渲染同时不占空间、不可见、不接收点击。
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
  top: 0;
  left: 0;
}

.col-label {
  font-size: 13px;
}
</style>
