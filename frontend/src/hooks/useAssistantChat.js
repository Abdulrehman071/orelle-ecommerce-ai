import { useCallback, useRef, useState } from 'react';
import { assistantApi, assistantError } from '../api/assistant';

let nextId = 1;

// Shared by the floating customer widget and the staff console.
export function useAssistantChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef([]);
  messagesRef.current = messages;

  const send = useCallback(async (text) => {
    const message = text.trim();
    if (!message || loading) return;
    const history = messagesRef.current
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.text.slice(0, 2000) }));
    setMessages((prev) => [...prev, { id: nextId++, role: 'user', text: message }]);
    setLoading(true);
    try {
      const { data } = await assistantApi.chat(message, history);
      setMessages((prev) => [...prev, { id: nextId++, role: 'assistant', text: data.answer, data }]);
    } catch (err) {
      setMessages((prev) => [...prev, { id: nextId++, role: 'error', text: assistantError(err) }]);
    } finally {
      setLoading(false);
    }
  }, [loading]);

  const reset = useCallback(() => setMessages([]), []);
  return { messages, loading, send, reset };
}
