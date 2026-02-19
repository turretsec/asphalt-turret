/**
 * useThumbnail
 *
 * Wraps a thumbnail URL with two behaviours:
 *
 * 1. Concurrency semaphore — at most MAX_CONCURRENT requests fire at once.
 * 2. Retry on HTTP 202 — the clip thumbnail endpoint returns 202 while the
 *    thumb_batch job hasn't generated the file yet. We retry with exponential
 *    backoff until 200 arrives or MAX_RETRIES is hit.
 *
 * HTTP semantics used by the backend:
 *   200 → image ready, display it
 *   202 → not ready yet, retry after a delay
 *   404 → genuinely not found → fail fast, show placeholder
 *   5xx → server error → fail fast, show placeholder
 */

import { ref, watch, onUnmounted } from 'vue'
import type { Ref } from 'vue'

// ─── Semaphore (module-level singleton) ───────────────────────────────────────
// Shared across all useThumbnail instances so the total in-flight requests
// across the entire page stays bounded regardless of how many items are rendered.

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

// ─── Retry config ─────────────────────────────────────────────────────────────

const MAX_RETRIES   = 8
const BASE_DELAY_MS = 1_500   // first retry after 1.5s
const MAX_DELAY_MS  = 30_000  // cap at 30s

function retryDelay(attempt: number): number {
  return Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS)
}

// Cache URLs that have already returned 200 so remounting virtualized rows
// does not keep re-fetching/regenerating thumbnails while scrolling.
const readyThumbnails = new Set<string>()

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

      // ── 202: thumbnail not ready yet, retry with backoff ─────────────────
      //
      // CRITICAL: this check must come BEFORE response.ok.
      // 202 is a 2xx status so response.ok === true for 202.
      // If we fall through to the response.ok branch, we'd try to create a
      // blob URL from an empty response body → broken image element.
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

      // ── 200: image is ready ───────────────────────────────────────────────
      if (response.ok) {
        readyThumbnails.add(src)
        if (!aborted && currentRequestId === requestId) {
          thumbnailSrc.value = src
          loading.value      = false
        }
        return
      }

      // ── 404 / 5xx: genuine failure, give up immediately ───────────────────
      // Retrying a 404 won't help — the file is missing or the path is wrong.
      failed.value  = true
      loading.value = false

    } catch (error) {
      // Expected during unmount/src-change cancellation.
      if (error instanceof DOMException && error.name === 'AbortError') {
        loading.value = false
        return
      }

      // Network / fetch error — worth a few retries
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

  return { thumbnailSrc, loading, failed }
}
