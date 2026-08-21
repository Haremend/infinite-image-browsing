<script setup lang="ts">
/**
 * RetryableImage — a-thin wrapper around ant-design-vue <a-image> that
 * automatically retries on load failure with exponential backoff and
 * re-triggers on browser online events.
 *
 * After MAX_RETRY (5) consecutive failures the image enters "manual retry"
 * mode: a semi-transparent overlay with a "Reload image" button is shown
 * so the user can retry without refreshing the whole page.
 *
 * Props are passed through to <a-image> (including :preview).
 */
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { fallbackImage } from 'vue3-ts-util'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const MAX_RETRY = 5
const props = defineProps<{
  src: string
  /** Defaults to the app-level fallback placeholder. */
  fallback?: string
  /** Same shape as <a-image :preview> — passed through to the inner a-image. */
  preview?: Record<string, unknown>
}>()

defineOptions({ inheritAttrs: false })

const retryCount = ref(0)
const token = ref(0)
const failedPermanently = ref(false)

let timer: ReturnType<typeof setTimeout> | undefined
let onlineOnce = false

// Build a URL that looks "new" to a-image so it re-enters the loading path.
// The backend ignores _r (it only looks at path+date), so cache-hits are
// unaffected but the browser sees a distinct URL and the image element
// re-triggers the fetch.
const retrySrc = computed(() => {
  if (!token.value) return props.src
  let base = props.src
  const sep = base.includes('?') ? '&' : '?'
  return `${base}${sep}_r=${token.value}`
})

const scheduleRetry = () => {
  if (failedPermanently.value) return
  if (retryCount.value >= MAX_RETRY) {
    failedPermanently.value = true
    return
  }
  const delay = Math.min(600 * 2 ** retryCount.value, 60_000)
  retryCount.value++
  timer = setTimeout(() => {
    timer = undefined
    token.value++
  }, delay)
}

const clearTimer = () => {
  if (timer) {
    clearTimeout(timer)
    timer = undefined
  }
}

const onError = () => {
  scheduleRetry()
}

const onImageLoad = () => {
  // Reset state when a fresh load succeeds (e.g. after a manual retry or
  // after the browser online event caused a retry).
  if (failedPermanently.value) {
    retryCount.value = 0
    failedPermanently.value = false
  }
}

const manualRetry = () => {
  retryCount.value = 0
  failedPermanently.value = false
  token.value++
}

// When the browser reconnects, kick off one retry regardless of where we
// are in the backoff sequence. This covers the common case where the user
// loses connectivity while scrolling and regains it later.
const onOnline = () => {
  if (onlineOnce) return
  onlineOnce = true
  // Small delay lets the browser settle before hitting the network again.
  setTimeout(() => {
    token.value++
    retryCount.value = 0
    failedPermanently.value = false
    onlineOnce = false
  }, 300)
}

onMounted(() => window.addEventListener('online', onOnline))
onBeforeUnmount(() => {
  clearTimer()
  window.removeEventListener('online', onOnline)
})
</script>

<template>
  <div class="iib-retryable-img-wrap">
    <a-image
      v-bind="$attrs"
      :src="retrySrc"
      :fallback="fallback ?? fallbackImage"
      :preview="preview"
      @error="onError"
      @load="onImageLoad"
    />
    <div
      v-if="failedPermanently"
      class="iib-retry-mask"
      @click.stop="manualRetry"
      :title="t('reloadImage')"
    >
      <span class="iib-retry-mask-text">{{ t('reloadImage') }}</span>
    </div>
  </div>
</template>

<style scoped>
.iib-retryable-img-wrap {
  position: relative;
  display: inline-block;
}

.iib-retry-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  border-radius: inherit;
  cursor: pointer;
  z-index: 1;
  transition: background 0.2s;
}

.iib-retry-mask:hover {
  background: rgba(0, 0, 0, 0.55);
}

.iib-retry-mask-text {
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
}
</style>
