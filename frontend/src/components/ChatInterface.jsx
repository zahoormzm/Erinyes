import { ChevronRight, RotateCcw, Send } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { streamChat } from '../api';
import useStore from '../store';

function TypingBubble({ dark = false }) {
  return (
    <div className={`rounded-2xl rounded-bl-md px-4 py-2.5 flex gap-1 border ${dark ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'}`}>
      <span className="w-2 h-2 bg-slate-400 rounded-full typing-dot" />
      <span className="w-2 h-2 bg-slate-400 rounded-full typing-dot" />
      <span className="w-2 h-2 bg-slate-400 rounded-full typing-dot" />
    </div>
  );
}

export default function ChatInterface({
  chatType,
  userId,
  title,
  placeholder,
  tall = false,
  helperText = '',
  suggestedPrompts = [],
  context = '',
  dark = false,
  initialMessage = '',
}) {
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef(null);
  const initialMessageRef = useRef('');
  const { showToast, getChatMessages, setChatMessages, clearChat } = useStore();
  const messages = getChatMessages(chatType);
  const setMessages = (updater) => setChatMessages(chatType, updater);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, streaming]);

  const appendAssistantText = (chunk) => {
    setMessages((previous) => previous.map((item, index) => (
      index === previous.length - 1 ? { ...item, content: `${item.content}${chunk}` } : item
    )));
  };

  const appendAssistantReasoning = (step) => {
    setMessages((previous) => previous.map((item, index) => (
      index === previous.length - 1 ? { ...item, reasoning: [...(item.reasoning || []), step] } : item
    )));
  };

  const sendMessage = async (rawMessage) => {
    const message = String(rawMessage || '').trim();
    if (!message || streaming) return;
    const userMessage = { role: 'user', content: message };
    setMessages((previous) => [...previous, userMessage, { role: 'assistant', content: '', reasoning: [] }]);
    setInput('');
    setStreaming(true);
    try {
      await streamChat(
        chatType,
        userId,
        message,
        messages,
        (chunk) => appendAssistantText(chunk),
        (step) => appendAssistantReasoning(step),
        () => setStreaming(false),
        context,
      );
      setStreaming(false);
    } catch (error) {
      setStreaming(false);
      setMessages((previous) => previous.filter((item, index) => !(index === previous.length - 1 && item.role === 'assistant' && !item.content && !(item.reasoning || []).length)));
      showToast(error.message, 'error');
    }
  };

  useEffect(() => {
    if (!initialMessage || initialMessageRef.current === initialMessage) return;
    initialMessageRef.current = initialMessage;
    sendMessage(initialMessage);
  }, [initialMessage]);

  const shellClass = dark
    ? 'bg-slate-900 border-slate-800 text-slate-100'
    : 'bg-white/80 border-slate-200/60 text-slate-900';
  const helperClass = dark
    ? 'border-slate-800 bg-slate-950/70 text-slate-300'
    : 'border-slate-100 bg-slate-50/70 text-slate-600';
  const inputClass = dark
    ? 'border-slate-700 bg-slate-800 text-slate-100 placeholder:text-slate-500'
    : 'border-slate-300 bg-white text-slate-900 placeholder:text-slate-400';
  const assistantBubbleClass = dark
    ? 'bg-slate-800 border-slate-700 text-slate-200 prose-invert'
    : 'bg-white border-slate-200 text-slate-700 prose-slate';

  return (
    <div className={`rounded-2xl border shadow-sm backdrop-blur-sm flex flex-col ${shellClass} ${tall ? 'h-[640px]' : 'h-[560px]'}`}>
      <div className={`px-5 py-4 border-b font-semibold flex items-center justify-between ${dark ? 'border-slate-800 text-white' : 'border-slate-200/60 text-slate-900'}`}>
        {title}
        {messages.length > 0 && !streaming ? (
          <button
            type="button"
            onClick={() => { clearChat(chatType); initialMessageRef.current = ''; }}
            title="Reset chat"
            className={`rounded-lg p-1.5 transition ${dark ? 'hover:bg-slate-800 text-slate-400 hover:text-slate-200' : 'hover:bg-slate-100 text-slate-400 hover:text-slate-600'}`}
          >
            <RotateCcw size={15} />
          </button>
        ) : null}
      </div>
      {(helperText || suggestedPrompts.length > 0) && (
        <div className={`px-5 py-4 border-b ${helperClass}`}>
          {helperText ? <div className="text-sm leading-relaxed">{helperText}</div> : null}
          {suggestedPrompts.length > 0 ? (
            <div className="flex flex-wrap gap-2 mt-3">
              {suggestedPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => sendMessage(prompt)}
                  disabled={streaming}
                  className="group flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-600 hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 transition-all"
                >
                  <span className="text-slate-400 group-hover:text-emerald-500 transition">→</span>
                  {prompt}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      )}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-4">
        {!messages.length ? (
          <div className={`rounded-2xl border border-dashed px-4 py-6 text-sm ${dark ? 'border-slate-800 text-slate-400' : 'border-slate-200 text-slate-500'}`}>
            Start the conversation.
          </div>
        ) : null}
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            {message.role === 'user' ? (
              <div className="max-w-[80%] rounded-2xl rounded-br-md bg-emerald-500 text-white px-4 py-3 text-sm shadow-sm">
                {message.content}
              </div>
            ) : (
              <div className="max-w-[80%]">
                {message.reasoning?.length > 0 ? (
                  <details className="mb-2 group">
                    <summary className={`flex items-center gap-1.5 text-xs cursor-pointer select-none ${dark ? 'text-slate-400 hover:text-slate-200' : 'text-slate-400 hover:text-slate-600'}`}>
                      <ChevronRight size={14} className="group-open:rotate-90 transition-transform" />
                      Show reasoning ({message.reasoning.length} steps)
                    </summary>
                    <div className={`mt-2 ml-4 space-y-1.5 border-l-2 pl-3 ${dark ? 'border-slate-700' : 'border-slate-200'}`}>
                      {message.reasoning.map((step, stepIndex) => (
                        <div
                          key={stepIndex}
                          className={`text-xs py-1 px-2 rounded ${
                            step.type === 'thought'
                              ? 'bg-amber-50 text-amber-800'
                              : step.type === 'action'
                                ? 'bg-blue-50 text-blue-800'
                                : 'bg-emerald-50 text-emerald-800'
                          }`}
                        >
                          <span className="font-semibold capitalize">{step.type}:</span> {step.content}
                        </div>
                      ))}
                    </div>
                  </details>
                ) : null}
                <div className={`rounded-2xl rounded-bl-md border px-4 py-3 prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:my-2 prose-strong:text-slate-900 ${assistantBubbleClass}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || ' '}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        ))}
        {streaming && (!messages.length || messages[messages.length - 1]?.role !== 'assistant' || !messages[messages.length - 1]?.content) ? (
          <div className="flex justify-start">
            <TypingBubble dark={dark} />
          </div>
        ) : null}
      </div>
      <div className={`border-t p-4 flex gap-2 ${dark ? 'border-slate-800' : 'border-slate-200/60'}`}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              sendMessage(input);
            }
          }}
          placeholder={placeholder}
          aria-label={placeholder}
          className={`flex-1 border rounded-xl px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 ${inputClass}`}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={streaming}
          aria-label={`Send ${title} message`}
          className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl px-4 py-2 font-medium transition disabled:opacity-60"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
