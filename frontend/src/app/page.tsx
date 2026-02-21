'use client';

import { useChat } from 'ai/react';
import { useRef, useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from 'ai';

// ── Types ───────────────────────────────────────────────────────────────────

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: number;
}

// ── localStorage ─────────────────────────────────────────────────────────────

const STORAGE_KEY = 'aegis_conversations';

function loadConversations(): Conversation[] {
  if (typeof window === 'undefined') return [];
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]'); }
  catch { return []; }
}

function persist(convs: Conversation[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(convs));
}

function deriveTitle(msgs: Message[]): string {
  const first = msgs.find(m => m.role === 'user');
  if (!first) return 'New chat';
  const clean = first.content.replace(/\[FILE:.*?\]\n[\s\S]*?\n\n/, '').trim();
  return clean.slice(0, 60) + (clean.length > 60 ? '…' : '');
}

// ── Icons ────────────────────────────────────────────────────────────────────

function IconSearch() {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>;
}
function IconMenu() {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>;
}
function IconPlus() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>;
}
function IconSend() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>;
}
function IconMic() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>;
}
function IconAttach() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>;
}
function IconShieldCheck() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>;
}
function IconX() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>;
}
function IconStar() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>;
}
function IconTrash() {
  return <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>;
}

// ── Gemini Star ──────────────────────────────────────────────────────────────

function GeminiStar({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="gs-grad" x1="14" y1="2" x2="14" y2="26" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#89B4F8" />
          <stop offset="100%" stopColor="#4285F4" />
        </linearGradient>
      </defs>
      <path d="M14 2C14 2 14 10.5 6 14C14 17.5 14 26 14 26C14 26 14 17.5 22 14C14 10.5 14 2 14 2Z" fill="url(#gs-grad)" />
    </svg>
  );
}

// ── Gemini loading animation ─────────────────────────────────────────────────

function GeminiLoading() {
  return (
    <div style={{ position: 'relative', width: 28, height: 28, flexShrink: 0 }}>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <GeminiStar size={20} />
      </div>
      <svg width="28" height="28" viewBox="0 0 28 28" style={{ position: 'absolute', inset: 0, animation: 'gemini-spin 1.4s linear infinite' }}>
        <defs>
          <linearGradient id="arc-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#4285F4" stopOpacity="0" />
            <stop offset="60%" stopColor="#89B4F8" stopOpacity="1" />
            <stop offset="100%" stopColor="#4285F4" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        <circle cx="14" cy="14" r="12" fill="none" stroke="url(#arc-grad)" strokeWidth="1.8" strokeLinecap="round" strokeDasharray="56 19" />
      </svg>
      <style>{`@keyframes gemini-spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }`}</style>
    </div>
  );
}

// ── Starter chips ─────────────────────────────────────────────────────────────

const STARTERS = [
  { label: 'Scan for PII', desc: 'Check a document for personal information' },
  { label: 'Analyze API keys', desc: 'Detect exposed credentials in config files' },
  { label: 'Privacy audit', desc: 'Review code for data leakage risks' },
  { label: 'Classify data', desc: 'Label sensitivity levels in a dataset' },
];

// ── Main component ────────────────────────────────────────────────────────────

export default function Chat() {
  // ── All conversations in localStorage ──
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => { setConversations(loadConversations()); }, []);

  // ── The messages we display — driven by us, not useChat ──
  const [displayMessages, setDisplayMessages] = useState<Message[]>([]);

  // Keep displayMessages in sync when switching conversations
  const activeConv = conversations.find(c => c.id === activeId) ?? null;

  // ── useChat: only used for streaming. initialMessages kept empty. ──
  const { messages: streamMessages, input, handleInputChange, handleSubmit,
    setInput, isLoading, setMessages: resetStream } = useChat({
    api: 'http://localhost:8000/api/chat',
  });

  // When streamMessages updates (new tokens streaming in), update display
  useEffect(() => {
    if (streamMessages.length > 0) {
      setDisplayMessages(streamMessages);
    }
  }, [streamMessages]);

  // ── Switch conversation ──
  const switchTo = useCallback((conv: Conversation) => {
    setActiveId(conv.id);
    setDisplayMessages(conv.messages);
    resetStream(conv.messages); // seed useChat so next submit sends correct history
    setInput('');
    setFileName(null);
  }, [resetStream, setInput]);

  // ── New chat ──
  const newChat = useCallback(() => {
    const newId = crypto.randomUUID();
    setActiveId(newId);
    setDisplayMessages([]);
    resetStream([]);
    setInput('');
    setFileName(null);
  }, [resetStream, setInput]);

  // ── Delete conversation ──
  const deleteConv = useCallback((e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    setConversations(prev => {
      const next = prev.filter(c => c.id !== convId);
      persist(next);
      return next;
    });
    if (activeId === convId) {
      // Switch to the next available conversation or blank
      setConversations(prev => {
        const remaining = prev.filter(c => c.id !== convId);
        if (remaining.length > 0) {
          const next = remaining.sort((a, b) => b.updatedAt - a.updatedAt)[0];
          setActiveId(next.id);
          setDisplayMessages(next.messages);
          resetStream(next.messages);
        } else {
          setActiveId(null);
          setDisplayMessages([]);
          resetStream([]);
        }
        return remaining;
      });
    }
  }, [activeId, resetStream]);

  // ── AI title generation ──
  const aiTitledRef = useRef<Set<string>>(new Set());

  const fetchAiTitle = useCallback(async (convId: string, firstUserContent: string) => {
    if (aiTitledRef.current.has(convId)) return;
    aiTitledRef.current.add(convId);
    try {
      const res = await fetch('http://localhost:8000/api/title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: firstUserContent.replace(/\[FILE:.*?\]\n[\s\S]*?\n\n/, '').trim() }),
      });
      const data = await res.json();
      if (data.title) {
        setConversations(prev => {
          const next = prev.map(c => c.id === convId ? { ...c, title: data.title } : c);
          persist(next);
          return next;
        });
      }
    } catch { /* fall back to derived title */ }
  }, []);

  // ── Save displayMessages to localStorage whenever they settle ──
  // We capture activeId and convId in the effect, not in a callback, so it's always fresh
  useEffect(() => {
    if (displayMessages.length === 0) return;
    const convId = activeId;
    if (!convId) return;

    const timer = setTimeout(() => {
      const title = deriveTitle(displayMessages);
      setConversations(prev => {
        let next: Conversation[];
        if (prev.find(c => c.id === convId)) {
          next = prev.map(c => c.id === convId
            ? { ...c, title: aiTitledRef.current.has(convId) ? c.title : title, messages: displayMessages, updatedAt: Date.now() }
            : c);
        } else {
          next = [{ id: convId, title, messages: displayMessages, updatedAt: Date.now() }, ...prev];
        }
        persist(next);
        return next;
      });

      // Fetch AI title once we have both user + assistant messages
      const firstUser = displayMessages.find(m => m.role === 'user');
      const hasAssistant = displayMessages.some(m => m.role === 'assistant');
      if (firstUser && hasAssistant) fetchAiTitle(convId, firstUser.content);
    }, 400);

    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayMessages, activeId]);

  // ── UI state ──
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [hoveredConvId, setHoveredConvId] = useState<string | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayMessages, isLoading]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
  }, [input]);

  // Ensure activeId is set when a new message is submitted
  const submitMessage = useCallback((e: { preventDefault: () => void }) => {
    if (!activeId) {
      const newId = crypto.randomUUID();
      setActiveId(newId);
    }
    handleSubmit(e as unknown as React.SyntheticEvent<HTMLFormElement>);
    setFileName(null);
  }, [activeId, handleSubmit]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        submitMessage({ preventDefault: () => {} });
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => {
      setInput(`[FILE: ${file.name}]\n${ev.target?.result as string}\n\nAnalyze this file for privacy risks.`);
    };
    reader.readAsText(file);
  };

  const hasMessages = displayMessages.length > 0;
  const headerTitle = activeConv?.title ?? (hasMessages ? deriveTitle(displayMessages) : null);
  const sortedConvs = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--bg-sidebar)', overflow: 'hidden' }}>

      {/* ── Sidebar ── */}
      {sidebarOpen && (
        <aside style={{
          width: 'var(--sidebar-width)', flexShrink: 0,
          background: 'var(--bg-sidebar)', display: 'flex', flexDirection: 'column',
          padding: '8px 0', borderRight: '1px solid var(--border-subtle)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px 4px' }}>
            <button onClick={() => setSidebarOpen(false)} style={ghostBtn}><IconMenu /></button>
            <button style={ghostBtn}><IconSearch /></button>
          </div>

          <div style={{ padding: '12px 12px 8px' }}>
            <button onClick={newChat} style={{
              display: 'flex', alignItems: 'center', gap: 10, width: '100%',
              padding: '10px 14px', background: 'var(--bg-surface-hover)',
              border: 'none', borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)', cursor: 'pointer',
              fontSize: 14, fontWeight: 500, transition: 'background 0.15s', fontFamily: 'inherit',
            }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.1)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-surface-hover)')}
            >
              <IconPlus />New chat
            </button>
          </div>

          <div style={{ padding: '4px 12px' }}>
            <button style={{ ...navItem, gap: 10 }}><IconStar /><span>My Stuff</span></button>
          </div>

          <div style={{ marginTop: 16, padding: '0 12px', flex: 1, overflowY: 'auto' }}>
            {sortedConvs.length > 0 && (
              <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-tertiary)', padding: '4px 8px', marginBottom: 4 }}>
                Chats
              </p>
            )}
            {sortedConvs.map(conv => {
              const isActive = conv.id === activeId;
              const isHovered = conv.id === hoveredConvId;
              return (
                <div
                  key={conv.id}
                  style={{ position: 'relative', display: 'flex', alignItems: 'center' }}
                  onMouseEnter={() => setHoveredConvId(conv.id)}
                  onMouseLeave={() => setHoveredConvId(null)}
                >
                  <button
                    onClick={() => switchTo(conv)}
                    style={{
                      ...navItem,
                      flex: 1,
                      paddingRight: isHovered ? 32 : 10,
                      background: isActive ? '#1b3a6b' : isHovered ? 'rgba(255,255,255,0.07)' : 'none',
                      color: isActive ? '#c2d9ff' : 'var(--text-secondary)',
                    }}
                  >
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {conv.title}
                    </span>
                  </button>
                  {isHovered && (
                    <button
                      onClick={(e) => deleteConv(e, conv.id)}
                      title="Delete conversation"
                      style={{
                        position: 'absolute', right: 4,
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--text-tertiary)', display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                        padding: 5, borderRadius: 6,
                        transition: 'color 0.15s',
                      }}
                      onMouseEnter={e => (e.currentTarget.style.color = '#ff6b6b')}
                      onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-tertiary)')}
                    >
                      <IconTrash />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </aside>
      )}

      {/* ── Main ── */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--bg-main)', overflow: 'hidden', position: 'relative' }}>
        <header style={{ display: 'flex', alignItems: 'center', padding: '8px 16px', borderBottom: 'none', flexShrink: 0, minHeight: 56 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
            {!sidebarOpen && (
              <button onClick={() => setSidebarOpen(true)} style={ghostBtn}><IconMenu /></button>
            )}
            <span style={{ fontSize: 22, fontWeight: 500, color: 'var(--text-primary)', fontFamily: "'Google Sans', sans-serif", letterSpacing: '-0.01em', marginRight: 4 }}>
              Gemini
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, background: 'var(--bg-surface)', borderRadius: 999, padding: '4px 12px', fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#34A853', display: 'inline-block' }} />
              FunctionGemma · Local
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: 2 }}><polyline points="6 9 12 15 18 9"/></svg>
            </div>
          </div>

          {headerTitle && hasMessages && (
            <div style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', fontSize: 15, fontWeight: 400, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 360, pointerEvents: 'none' }}>
              {headerTitle}
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, justifyContent: 'flex-end' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#34A853', background: 'rgba(52,168,83,0.1)', borderRadius: 999, padding: '4px 12px' }}>
              <IconShieldCheck />Privacy layer active
            </div>
            <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'linear-gradient(135deg, #4285F4, #8A6FF0)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 600, color: '#fff', cursor: 'pointer' }}>
              A
            </div>
          </div>
        </header>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          {!hasMessages ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 24px', gap: 24 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                <GeminiStar size={52} />
                <h1 style={{ fontSize: '2rem', fontWeight: 400, margin: 0, background: 'linear-gradient(135deg, #4285F4 0%, #8A6FF0 50%, #EA4335 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
                  How can Aegis help?
                </h1>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', margin: 0, textAlign: 'center', maxWidth: 360 }}>
                  Your local privacy shield for agentic AI. Files never leave your machine without your approval.
                </p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, width: '100%', maxWidth: 560 }}>
                {STARTERS.map(s => (
                  <button key={s.label} onClick={() => setInput(s.desc)} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', padding: '14px 16px', cursor: 'pointer', textAlign: 'left', transition: 'background 0.15s', fontFamily: 'inherit' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.07)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-surface)')}
                  >
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{s.label}</p>
                    <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--text-secondary)' }}>{s.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ width: '100%', maxWidth: 740, margin: '0 auto', padding: '24px 24px 0' }}>
              {displayMessages.map(m => (
                <div key={m.id} style={{ display: 'flex', flexDirection: m.role === 'user' ? 'row-reverse' : 'row', alignItems: 'flex-start', marginBottom: 28, gap: 12 }}>
                  {m.role === 'assistant' && <div style={{ flexShrink: 0, marginTop: 2 }}><GeminiStar size={22} /></div>}
                  {m.role === 'user' ? (
                    <div style={{ background: 'var(--bg-user-bubble)', borderRadius: '20px 20px 4px 20px', padding: '12px 18px', maxWidth: '75%', fontSize: 14, lineHeight: 1.6, color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }}>
                      {m.content}
                    </div>
                  ) : (
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="prose-gemini" style={{ fontSize: 14 }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 28 }}>
                  <GeminiLoading />
                </div>
              )}
              <div ref={messagesEndRef} />
              <div style={{ height: 24 }} />
            </div>
          )}
        </div>

        <div style={{ padding: hasMessages ? '12px 24px 20px' : '0 24px 32px', maxWidth: 740, width: '100%', margin: '0 auto', flexShrink: 0 }}>
          {fileName && (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'var(--bg-surface)', border: '1px solid var(--border-input)', borderRadius: 999, padding: '4px 12px', marginBottom: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
              <IconAttach />{fileName}
              <button onClick={() => { setFileName(null); setInput(''); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', display: 'flex', padding: 0, marginLeft: 2 }}>
                <IconX />
              </button>
            </div>
          )}

          <form onSubmit={submitMessage}>
            <div style={{ background: 'var(--bg-input)', border: '1px solid var(--border-input)', borderRadius: 'var(--radius-xl)', padding: '12px 12px 8px 16px', display: 'flex', flexDirection: 'column', gap: 8, boxShadow: '0 1px 8px rgba(0,0,0,0.3)' }}>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Ask Aegis..."
                rows={1}
                style={{ background: 'none', border: 'none', outline: 'none', color: 'var(--text-primary)', fontSize: 15, lineHeight: 1.6, resize: 'none', width: '100%', fontFamily: 'inherit', padding: 0, caretColor: '#4285F4' }}
              />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} style={{ display: 'none' }} />
                  <button type="button" onClick={() => fileInputRef.current?.click()} style={inputIconBtn} title="Attach file"><IconAttach /></button>
                  <button type="button" style={{ ...inputIconBtn, display: 'flex', alignItems: 'center', gap: 5, padding: '6px 10px', borderRadius: 999, fontSize: 12, fontWeight: 500 }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                    Tools
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4285F4', display: 'inline-block' }} />
                  </button>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {!input && <button type="button" style={inputIconBtn}><IconMic /></button>}
                  {input && (
                    <button type="submit" disabled={isLoading} style={{ width: 36, height: 36, borderRadius: '50%', background: isLoading ? 'rgba(255,255,255,0.1)' : '#4285F4', border: 'none', cursor: isLoading ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', transition: 'background 0.15s', flexShrink: 0 }}>
                      <IconSend />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </form>

          <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-tertiary)', marginTop: 8 }}>
            Secured by FunctionGemma · Cactus Compute · Data stays on your device
          </p>
        </div>
      </main>
    </div>
  );
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const ghostBtn: React.CSSProperties = {
  background: 'none', border: 'none', borderRadius: 8, padding: 8,
  cursor: 'pointer', color: 'var(--text-secondary)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'background 0.15s',
};

const navItem: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8, width: '100%',
  padding: '8px 10px', background: 'none', border: 'none', borderRadius: 10,
  cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 13, fontWeight: 400,
  textAlign: 'left', transition: 'background 0.15s', fontFamily: 'inherit',
};

const inputIconBtn: React.CSSProperties = {
  background: 'none', border: 'none', borderRadius: 999, padding: '6px 8px',
  cursor: 'pointer', color: 'var(--text-secondary)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'background 0.15s',
};
