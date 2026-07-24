"use client";

// Turn-by-turn call playback: renders a transcript like a call log and, when
// turns carry synthesized audio, plays them in sequence with the active turn
// highlighted. Turns without audio (voice degraded to text, hold-music
// markers) are shown for a beat and skipped — playback never blocks on a
// missing clip, mirroring the backend's "audio failures degrade to text"
// contract.

import { useEffect, useRef, useState } from "react";
import type { VoicedTurn } from "@/lib/types";

const SPEAKER_LABEL: Record<VoicedTurn["speaker"], string> = {
  agent: "Meridian agent",
  patient: "Patient",
  ivr: "Payer IVR",
  caller: "Agent keypad",
  system: "",
};

const SPEAKER_STYLE: Record<VoicedTurn["speaker"], string> = {
  agent:
    "border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950/40",
  patient:
    "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900",
  ivr: "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40",
  caller:
    "border-slate-200 bg-slate-50 font-mono dark:border-slate-800 dark:bg-slate-900",
  system:
    "border-dashed border-slate-200 bg-transparent italic dark:border-slate-800",
};

const TEXT_ONLY_TURN_MS = 900;

export default function CallPlayback({ turns }: { turns: VoicedTurn[] }) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelledRef = useRef(false);
  const activeItemRef = useRef<HTMLLIElement | null>(null);

  const hasAudio = turns.some((t) => t.audio_b64);

  useEffect(() => {
    activeItemRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeIndex]);

  useEffect(() => stop, []); // stop playback on unmount

  function stop() {
    cancelledRef.current = true;
    audioRef.current?.pause();
    audioRef.current = null;
    if (timerRef.current) clearTimeout(timerRef.current);
    setPlaying(false);
    setActiveIndex(null);
  }

  function play() {
    cancelledRef.current = false;
    setPlaying(true);
    playTurn(0);
  }

  function playTurn(index: number) {
    if (cancelledRef.current) return;
    if (index >= turns.length) {
      setPlaying(false);
      setActiveIndex(null);
      return;
    }
    setActiveIndex(index);
    const turn = turns[index];
    if (turn.audio_b64 && turn.mime) {
      const audio = new Audio(`data:${turn.mime};base64,${turn.audio_b64}`);
      audioRef.current = audio;
      audio.onended = () => playTurn(index + 1);
      audio.onerror = () => playTurn(index + 1);
      void audio.play().catch(() => playTurn(index + 1));
    } else {
      timerRef.current = setTimeout(() => playTurn(index + 1), TEXT_ONLY_TURN_MS);
    }
  }

  return (
    <div>
      <div className="mb-3 flex items-center gap-3">
        {playing ? (
          <button
            onClick={stop}
            className="rounded-md bg-slate-700 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
          >
            ■ Stop
          </button>
        ) : (
          <button
            onClick={play}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            ▶ Play call
          </button>
        )}
        {!hasAudio && (
          <span className="text-xs text-slate-400">
            No audio synthesized (voice unavailable) — playing as captions.
          </span>
        )}
      </div>
      <ul className="max-h-96 space-y-2 overflow-y-auto pr-1">
        {turns.map((turn, i) => (
          <li
            key={i}
            ref={i === activeIndex ? activeItemRef : null}
            className={`rounded-lg border px-4 py-2.5 text-sm transition-shadow ${SPEAKER_STYLE[turn.speaker]} ${
              i === activeIndex ? "ring-2 ring-blue-500" : ""
            }`}
          >
            {SPEAKER_LABEL[turn.speaker] && (
              <span className="mr-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {SPEAKER_LABEL[turn.speaker]}
                {turn.audio_b64 ? " 🔊" : ""}
              </span>
            )}
            <span className="text-slate-800 dark:text-slate-200">{turn.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
