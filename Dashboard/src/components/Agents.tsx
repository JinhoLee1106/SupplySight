import { useMemo, useRef, useState } from 'react';
import {
  Bot,
  CheckCircle2,
  MessageSquare,
  RotateCcw,
  Send,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';
import { postAgentChat } from '../lib/api';

type MessageRole = 'user' | 'assistant';

type ChatMessage = {
  id: number;
  role: MessageRole;
  content: string;
};

type RiskPreferences = {
  importWeight: number;
  priceStressWeight: number;
  volatilityPenalty: number;
  oilImpactCap: number;
  atRiskThreshold: number;
  criticalThreshold: number;
  includeNewsSignal: boolean;
  conservativeMode: boolean;
};

const DEFAULT_PREFS: RiskPreferences = {
  importWeight: 1.1,
  priceStressWeight: 0.85,
  volatilityPenalty: 0.65,
  oilImpactCap: 1.5,
  atRiskThreshold: 5.0,
  criticalThreshold: 2.5,
  includeNewsSignal: true,
  conservativeMode: false,
};

const QUICK_PROMPTS = [
  'Why is shrimp risk high this month?',
  'Show key drivers behind the score',
  'What if oil price rises by 10%?',
  'Suggest actions to avoid stockout',
];

export function Agents() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: 'assistant',
      content:
        'Hi, I am your SupplySight agent. Ask me about risk drivers, scenario changes, or recommendations. You can tune the model controls on the right and I will explain impact in plain language.',
    },
  ]);
  const [draft, setDraft] = useState('');
  const [prefs, setPrefs] = useState<RiskPreferences>(DEFAULT_PREFS);
  const [lastAppliedAt, setLastAppliedAt] = useState<string | null>(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const isAnimatingRef = useRef(false);

  const estimatedHealthIndex = useMemo(() => {
    const base = 7.2;
    const direction = prefs.conservativeMode ? -0.35 : 0;
    const newsBonus = prefs.includeNewsSignal ? 0.1 : -0.15;
    const weighted =
      base +
      (prefs.importWeight - 1.0) * 0.55 -
      (prefs.priceStressWeight - 0.8) * 0.35 -
      prefs.volatilityPenalty * 0.25 -
      prefs.oilImpactCap * 0.08 +
      newsBonus +
      direction;

    return Math.max(0, Math.min(10, Number(weighted.toFixed(2))));
  }, [prefs]);

  const animateAssistantMessage = async (fullText: string) => {
    const messageId = Date.now() + 1;
    const words = fullText.trim().split(/\s+/).filter(Boolean);
    const baseDelayMs = 38;

    isAnimatingRef.current = true;
    setMessages((prev) => [...prev, { id: messageId, role: 'assistant', content: '' }]);

    for (let i = 0; i < words.length; i += 1) {
      const chunk = words.slice(0, i + 1).join(' ');
      setMessages((prev) =>
        prev.map((msg) => (msg.id === messageId ? { ...msg, content: chunk } : msg)),
      );
      // Slight jitter avoids robotic cadence and feels more natural.
      const jitter = Math.floor(Math.random() * 16);
      await new Promise((resolve) => setTimeout(resolve, baseDelayMs + jitter));
    }

    isAnimatingRef.current = false;
  };

  const sendMessage = async (value?: string) => {
    const text = (value ?? draft).trim();
    if (!text || chatLoading || isAnimatingRef.current) return;

    setChatError(null);

    const userMessage: ChatMessage = { id: Date.now(), role: 'user', content: text };
    const history = [...messages, userMessage];

    setMessages(history);
    setDraft('');

    try {
      setChatLoading(true);
      const response = await postAgentChat({
        messages: history.map((m) => ({ role: m.role, content: m.content })),
        preferenceContext: {
          ...prefs,
          estimatedHealthIndex,
        },
        temperature: 0.3,
      });

      await animateAssistantMessage(response.message);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Chat request failed';
      setChatError(message);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content:
            'something went wrong.',
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const applyPreset = (preset: 'balanced' | 'cost' | 'resilience') => {
    if (preset === 'balanced') {
      setPrefs({ ...DEFAULT_PREFS });
      return;
    }

    if (preset === 'cost') {
      setPrefs({
        importWeight: 0.95,
        priceStressWeight: 1.15,
        volatilityPenalty: 0.55,
        oilImpactCap: 1.9,
        atRiskThreshold: 4.8,
        criticalThreshold: 2.2,
        includeNewsSignal: false,
        conservativeMode: false,
      });
      return;
    }

    setPrefs({
      importWeight: 1.35,
      priceStressWeight: 0.75,
      volatilityPenalty: 0.9,
      oilImpactCap: 1.2,
      atRiskThreshold: 5.4,
      criticalThreshold: 2.9,
      includeNewsSignal: true,
      conservativeMode: true,
    });
  };

  const applyPreferences = () => {
    setLastAppliedAt(new Date().toLocaleTimeString());
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + 2,
        role: 'assistant',
        content:
          'Preferences applied. I will now evaluate risk with your selected constants and thresholds in this session preview.',
      },
    ]);
  };

  const resetPreferences = () => {
    setPrefs({ ...DEFAULT_PREFS });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-slate-900 mb-1">Agents</h1>
          <p className="text-slate-600">Chat with LLM agents and tune risk settings in one place.</p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
          <Sparkles className="h-4 w-4" />
          <span>Interactive Control Mode</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="xl:col-span-2 rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
            <MessageSquare className="h-4 w-4 text-blue-600" />
            <h2 className="text-sm font-semibold text-slate-900">Agent Chatbox</h2>
          </div>

          <div className="h-[420px] space-y-3 overflow-y-auto px-4 py-4">
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'border border-slate-200 bg-slate-50 text-slate-700'
                  }`}
                >
                  {m.role === 'assistant' && (
                    <div className="mb-1 flex items-center gap-1 text-xs text-slate-500">
                      <Bot className="h-3.5 w-3.5" />
                      <span>Supply Agent</span>
                    </div>
                  )}
                  {m.content}
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-slate-200 p-4">
            <div className="mb-3 flex flex-wrap gap-2">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => sendMessage(prompt)}
                  disabled={chatLoading || isAnimatingRef.current}
                  className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
            {chatError && (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                {chatError}
              </div>
            )}
            <div className="flex gap-2">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Ask an agent about risk, scenario impact, or recommended action..."
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-200 focus:ring"
                disabled={chatLoading || isAnimatingRef.current}
              />
              <button
                onClick={() => sendMessage()}
                disabled={chatLoading || isAnimatingRef.current}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                <Send className="h-4 w-4" />
                {chatLoading ? 'Sending...' : isAnimatingRef.current ? 'Typing...' : 'Send'}
              </button>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
            <SlidersHorizontal className="h-4 w-4 text-blue-600" />
            <h2 className="text-sm font-semibold text-slate-900">Risk Preference Controls</h2>
          </div>

          <div className="space-y-4 p-4">
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => applyPreset('balanced')}
                className="rounded-md border border-slate-300 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
              >
                Balanced
              </button>
              <button
                onClick={() => applyPreset('cost')}
                className="rounded-md border border-slate-300 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
              >
                Cost-first
              </button>
              <button
                onClick={() => applyPreset('resilience')}
                className="rounded-md border border-slate-300 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
              >
                Resilience
              </button>
            </div>

            <label className="block text-xs text-slate-600">Import signal weight: {prefs.importWeight.toFixed(2)}</label>
            <input
              type="range"
              min={0.7}
              max={1.6}
              step={0.05}
              value={prefs.importWeight}
              onChange={(e) => setPrefs((p) => ({ ...p, importWeight: Number(e.target.value) }))}
              className="w-full"
            />

            <label className="block text-xs text-slate-600">Price stress weight: {prefs.priceStressWeight.toFixed(2)}</label>
            <input
              type="range"
              min={0.5}
              max={1.4}
              step={0.05}
              value={prefs.priceStressWeight}
              onChange={(e) => setPrefs((p) => ({ ...p, priceStressWeight: Number(e.target.value) }))}
              className="w-full"
            />

            <label className="block text-xs text-slate-600">Volatility penalty: {prefs.volatilityPenalty.toFixed(2)}</label>
            <input
              type="range"
              min={0.2}
              max={1.2}
              step={0.05}
              value={prefs.volatilityPenalty}
              onChange={(e) => setPrefs((p) => ({ ...p, volatilityPenalty: Number(e.target.value) }))}
              className="w-full"
            />

            <label className="block text-xs text-slate-600">Oil impact cap: {prefs.oilImpactCap.toFixed(2)}</label>
            <input
              type="range"
              min={0.5}
              max={2.2}
              step={0.1}
              value={prefs.oilImpactCap}
              onChange={(e) => setPrefs((p) => ({ ...p, oilImpactCap: Number(e.target.value) }))}
              className="w-full"
            />

            <label className="block text-xs text-slate-600">At Risk threshold: {prefs.atRiskThreshold.toFixed(1)}</label>
            <input
              type="range"
              min={4.0}
              max={6.0}
              step={0.1}
              value={prefs.atRiskThreshold}
              onChange={(e) => setPrefs((p) => ({ ...p, atRiskThreshold: Number(e.target.value) }))}
              className="w-full"
            />

            <label className="block text-xs text-slate-600">Critical threshold: {prefs.criticalThreshold.toFixed(1)}</label>
            <input
              type="range"
              min={1.5}
              max={3.5}
              step={0.1}
              value={prefs.criticalThreshold}
              onChange={(e) => setPrefs((p) => ({ ...p, criticalThreshold: Number(e.target.value) }))}
              className="w-full"
            />

            <label className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-xs text-slate-700">
              Include news sentiment signal
              <input
                type="checkbox"
                checked={prefs.includeNewsSignal}
                onChange={(e) => setPrefs((p) => ({ ...p, includeNewsSignal: e.target.checked }))}
              />
            </label>

            <label className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-xs text-slate-700">
              Conservative mode
              <input
                type="checkbox"
                checked={prefs.conservativeMode}
                onChange={(e) => setPrefs((p) => ({ ...p, conservativeMode: e.target.checked }))}
              />
            </label>

            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <p className="text-xs text-slate-500">Preview health index</p>
              <p className="text-lg font-semibold text-slate-900">{estimatedHealthIndex}/10</p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={applyPreferences}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                <CheckCircle2 className="h-4 w-4" />
                Apply
              </button>
              <button
                onClick={resetPreferences}
                className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
              >
                <RotateCcw className="h-4 w-4" />
                Reset
              </button>
            </div>

            {lastAppliedAt && (
              <div className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-800">
                Preferences last applied at {lastAppliedAt}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
