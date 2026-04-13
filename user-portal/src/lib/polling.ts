import { useEffect, useRef, useState } from 'react';

export interface PollingResult<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
}

/**
 * Poll `fetcher` every `intervalMs` until `shouldStop(latest)` returns true
 * or the component unmounts. Cancels cleanly on unmount.
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  shouldStop: (latest: T) => boolean,
): PollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    let timer: number | undefined;

    async function poll(): Promise<void> {
      if (cancelledRef.current) return;
      try {
        const latest = await fetcher();
        if (cancelledRef.current) return;
        setData(latest);
        setError(null);
        setLoading(false);
        if (shouldStop(latest)) return;
      } catch (e) {
        if (!cancelledRef.current) {
          setError(e as Error);
          setLoading(false);
        }
      }
      timer = window.setTimeout(poll, intervalMs);
    }

    void poll();
    return () => {
      cancelledRef.current = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs]);

  return { data, error, loading };
}
