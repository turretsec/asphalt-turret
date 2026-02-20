/**
 * useThumbnail
 *
 * Loads thumbnail images using `new Image()` instead of `fetch()`.
 *
 * WHY NOT fetch():
 * fetch() is a CORS request. <img> and new Image() are not — the browser
 * loads them as "no-cors" requests and doesn't enforce the CORS policy.
 * Since our thumbnail endpoints return image files (not JSON), there's no
 * reason to use fetch(). Switching to Image() makes CORS completely irrelevant.
 *
 * RETRY LOGIC:
 * Both "not ready yet" (202) and genuine errors look like onerror() when
 * loading via Image(). We can't distinguish them, so we retry up to
 * MAX_RETRIES times with exponential backoff. BackgroundTasks generates
 * thumbnails in < 1s, so the second retry (1.5s later) almost always wins.
 * After MAX_RETRIES, show the placeholder icon.
 *
 * CONCURRENCY:
 * Module-level semaphore caps simultaneous in-flight image probes to
 * MAX_CONCURRENT so we don't hammer the server when the list first renders.
 *
 * VirtualScroller instance reuse:
 * retry() lets ThumbnailImage reset a failed state when the user clicks
 * the placeholder icon — handles the case where srcRef didn't change
 * (same item recycled in the same scroller slot) so the watch didn't fire.
 */

import { ref, watch, onUnmounted } from 'vue'
import type { Ref } from 'vue'

// ─── Semaphore ────────────────────────────────────────────────────────────────

const MAX_CONCURRENT = 6   // slightly higher since Image() is lower-overhead than fetch()
let _active = 0
const _queue: Array<() => void> = []

function acquireSemaphore(): Promise<void> {
  return new Promise((resolve) => {
    if (_active < MAX_CONCURRENT) {
      _active++
      resolve()
    } else {
      _queue.push(() => { _active++; resolve() })
    }
  })
}

function releaseSemaphore() {
  _active = Math.max(0, _active - 1)
  const next = _queue.shift()
  if (next) next()
}

// ─── Ready cache ──────────────────────────────────────────────────────────────
// If a URL successfully loaded once, skip the probe on remount.
// (VirtualScroller remounts items as you scroll back up.)

const readyUrls = new Set<string>()

// ─── Retry config ─────────────────────────────────────────────────────────────

const MAX_RETRIES   = 6
const BASE_DELAY_MS = 1_200
const MAX_DELAY_MS  = 15_000

function retryDelay(attempt: number): number {
  return Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS)
}

// ─── Image probe ──────────────────────────────────────────────────────────────

function probeImage(src: string, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) { reject(new DOMException('Aborted', 'AbortError')); return }

    const img = new Image()

    const cleanup = () => {
      img.onload  = null
      img.onerror = null
    }

    signal.addEventListener('abort', () => {
      cleanup()
      img.src = ''
      reject(new DOMException('Aborted', 'AbortError'))
    }, { once: true })

    img.onload  = () => { cleanup(); resolve() }
    img.onerror = () => { cleanup(); reject(new Error('Image load failed')) }

    img.src = src
  })
}

// ─── Composable ───────────────────────────────────────────────────────────────

export function useThumbnail(srcRef: Ref<string | null | undefined>) {
  const thumbnailSrc = ref<string | null>(null)
  const loading      = ref(false)
  const failed       = ref(false)

  let aborted    = false
  let requestId  = 0
  let retryTimer: ReturnType<typeof setTimeout> | null = null
  let controller: AbortController | null = null

  function cancelPending() {
    aborted = true
    requestId++
    controller?.abort()
    controller = null
    if (retryTimer !== null) { clearTimeout(retryTimer); retryTimer = null }
  }

  async function load(src: string, attempt = 0, rid = requestId) {
    if (aborted || rid !== requestId) return

    // Already known good — set directly, no probe needed
    if (readyUrls.has(src)) {
      thumbnailSrc.value = src
      loading.value      = false
      return
    }

    loading.value = true

    await acquireSemaphore()

    if (aborted || rid !== requestId) {
      releaseSemaphore()
      return
    }

    try {
      controller = new AbortController()
      await probeImage(src, controller.signal)
      controller = null

      if (aborted || rid !== requestId) return

      // Image loaded successfully
      readyUrls.add(src)
      thumbnailSrc.value = src
      loading.value      = false

    } catch (err) {
      controller = null

      if (err instanceof DOMException && err.name === 'AbortError') {
        loading.value = false
        return
      }

      // Load failed — could be 202 (not ready yet) or real 404.
      // Retry either way; BackgroundTasks will have the file ready soon.
      if (!aborted && rid === requestId && attempt < MAX_RETRIES) {
        retryTimer = setTimeout(() => {
          retryTimer = null
          load(src, attempt + 1, rid)
        }, retryDelay(attempt))
      } else {
        failed.value  = true
        loading.value = false
      }
    } finally {
      releaseSemaphore()
    }
  }

  watch(
    srcRef,
    (newSrc) => {
      cancelPending()
      aborted            = false
      thumbnailSrc.value = null
      failed.value       = false

      if (newSrc) {
        load(newSrc)
      } else {
        loading.value = false
      }
    },
    { immediate: true }
  )

  onUnmounted(() => { cancelPending() })

  function retry() {
    const src = srcRef.value
    if (!src) return
    cancelPending()
    aborted            = false
    thumbnailSrc.value = null
    failed.value       = false
    load(src)
  }

  return { thumbnailSrc, loading, failed, retry }
}