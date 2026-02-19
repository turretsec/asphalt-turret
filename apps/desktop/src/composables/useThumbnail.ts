/**
 * useThumbnail
 *
 * Wraps a thumbnail URL with two behaviours:
 *
 * 1. Concurrency semaphore — at most MAX_CONCURRENT requests fire at once.
 * 2. Retry on HTTP 202 — the clip thumbnail endpoint returns 202 while
 *    generation is in progress. We retry with exponential backoff.
 *
 * HTTP semantics:
 *   200 → ready, display it
 *   202 → not ready yet, retry after delay
 *   404 → genuinely missing, fail fast
 *   5xx → server error, fail fast
 *
 * WHY retry() EXISTS:
 * VirtualScroller reuses Vue component instances when scrolling. If a
 * component previously exhausted MAX_RETRIES (failed = true), its srcRef
 * doesn't change when the scroller hands it back for the same item —
 * so the watch never fires again, and failed stays true forever.
 * retry() lets ThumbnailImage's click handler break out of that state.
 */

import { ref, watch, onUnmounted } from 'vue'
import type { Ref } from 'vue'

// ─── Semaphore (module-level singleton) ───────────────────────────────────────

const MAX_CONCURRENT = 4
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
// URLs that have returned 200 — skip the fetch on remount.

const readyThumbnails = new Set<string>()

// ─── Retry config ─────────────────────────────────────────────────────────────

const MAX_RETRIES   = 8
const BASE_DELAY_MS = 1_500
const MAX_DELAY_MS  = 30_000

function retryDelay(attempt: number): number {
  return Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS)
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
    requestId += 1
    controller?.abort()
    controller = null
    if (retryTimer !== null) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
  }

  async function load(src: string, attempt = 0, currentRequestId = requestId) {
    if (aborted || currentRequestId !== requestId) return

    if (readyThumbnails.has(src)) {
      thumbnailSrc.value = src
      loading.value = false
      return
    }

    loading.value = true

    await acquireSemaphore()

    if (aborted || currentRequestId !== requestId) {
      releaseSemaphore()
      return
    }

    try {
      controller = new AbortController()
      const response = await fetch(src, { method: 'GET', signal: controller.signal })
      controller = null

      if (aborted || currentRequestId !== requestId) return

      // ── 202: not ready yet, retry with backoff ────────────────────────────
      // MUST come before response.ok — 202 is 2xx so response.ok is true.
      if (response.status === 202) {
        if (attempt >= MAX_RETRIES) {
          failed.value  = true
          loading.value = false
          return
        }
        retryTimer = setTimeout(() => {
          retryTimer = null
          load(src, attempt + 1, currentRequestId)
        }, retryDelay(attempt))
        return
      }

      // ── 200: image ready ──────────────────────────────────────────────────
      if (response.ok) {
        readyThumbnails.add(src)
        if (!aborted && currentRequestId === requestId) {
          thumbnailSrc.value = src
          loading.value      = false
        }
        return
      }

      // ── 404 / 5xx: give up immediately ───────────────────────────────────
      failed.value  = true
      loading.value = false

    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        loading.value = false
        return
      }
      if (!aborted && currentRequestId === requestId && attempt < MAX_RETRIES) {
        retryTimer = setTimeout(() => {
          retryTimer = null
          load(src, attempt + 1, currentRequestId)
        }, retryDelay(attempt))
      } else {
        failed.value  = true
        loading.value = false
      }
    } finally {
      releaseSemaphore()
    }
  }

  // Re-run whenever src changes (different item rendered in same scroller slot)
  watch(
    srcRef,
    (newSrc) => {
      cancelPending()
      aborted = false
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

  onUnmounted(() => {
    cancelPending()
  })

  // Exposed so ThumbnailImage can call this when the user clicks the camera
  // icon — handles the VirtualScroller instance-reuse case where srcRef
  // didn't change so the watch never fired again after a previous failure.
  function retry() {
    const src = srcRef.value
    if (!src) return
    cancelPending()
    aborted = false
    thumbnailSrc.value = null
    failed.value       = false
    load(src)
  }

  return { thumbnailSrc, loading, failed, retry }
}