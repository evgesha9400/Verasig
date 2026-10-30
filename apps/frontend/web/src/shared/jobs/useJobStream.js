import { useEffect, useRef } from 'react'

/* Verasig — start a server job then subscribe to its SSE progress, once per key.
   Handlers are latched in a ref so a parent re-creating them each render never
   refires the effect (it is keyed on `key` alone). Teardown flips a `closed`
   guard and closes the subscription, so a StrictMode double-invoke — or a feed
   switch mid-stream — cannot leak a live stream or fire a stale handler.

   `tolerate409`: a re-invoked effect may re-start a job that is still live; the
   backend replays state to a late subscriber, so swallow the 409 and subscribe
   anyway. Any other start failure surfaces through `onError`. */

export function useJobStream({
  feedId,
  start,
  stream,
  onProgress,
  onDone,
  onError,
  tolerate409 = false
}) {
  const handlers = useRef({ start, stream, onProgress, onDone, onError })
  handlers.current = { start, stream, onProgress, onDone, onError }

  useEffect(() => {
    let closed = false
    let subscription = null

    async function run() {
      try {
        try {
          await handlers.current.start(feedId)
        } catch (error) {
          if (!(tolerate409 && error?.status === 409)) throw error
        }
        if (closed) return
        subscription = handlers.current.stream(feedId, {
          onProgress: (progress) => handlers.current.onProgress?.(progress),
          onDone: (result) => handlers.current.onDone?.(result),
          onError: (error) => handlers.current.onError?.(error)
        })
      } catch (error) {
        if (!closed) handlers.current.onError?.({ message: error?.message })
      }
    }

    void run()
    return () => {
      closed = true
      subscription && subscription.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedId])
}
