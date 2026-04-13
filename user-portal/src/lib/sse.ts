import { API_URL } from './api';

export interface SseEvent {
  event: string;
  data: Record<string, unknown>;
}

/**
 * Open an EventSource-like stream authenticated via the id token.
 * Native EventSource doesn't support custom headers, so we use fetch
 * with a ReadableStream and parse SSE frames manually.
 */
export async function openMessageStream(
  conversationId: string,
  pendingMessageId: string,
  onEvent: (event: SseEvent) => void,
): Promise<void> {
  const token = localStorage.getItem('ca:idToken') ?? '';
  const response = await fetch(
    `${API_URL}/api/v1/conversations/${conversationId}/stream?pending=${pendingMessageId}`,
    {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'text/event-stream',
      },
    },
  );

  if (!response.ok || !response.body) {
    throw new Error(`Stream open failed: HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let blockEnd: number;
    while ((blockEnd = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, blockEnd);
      buffer = buffer.slice(blockEnd + 2);
      const parsed = parseBlock(block);
      if (parsed) {
        onEvent(parsed);
        if (parsed.event === 'done' || parsed.event === 'error') {
          return;
        }
      }
    }
  }
}

function parseBlock(block: string): SseEvent | null {
  let eventName = 'message';
  let dataLine = '';
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      eventName = line.slice('event:'.length).trim();
    } else if (line.startsWith('data:')) {
      dataLine += line.slice('data:'.length).trim();
    }
  }
  if (!dataLine) return null;
  try {
    return { event: eventName, data: JSON.parse(dataLine) };
  } catch {
    return null;
  }
}
