import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { fmt } from "@/lib/owner";
import { Btn } from "@/components/gtex/ui";
import { PlayerCard } from "@/components/gtex/PlayerCard";

function SealedPack({ count, onOpen }: { count: number; onOpen: () => void }) {
  return (
    <motion.button type="button" data-testid="pack-sealed" onClick={onOpen}
      initial={{ scale: 0.6, opacity: 0, rotate: -6 }} animate={{ scale: 1, opacity: 1, rotate: [0, -3, 3, -2, 2, 0] }}
      transition={{ duration: 0.9, rotate: { repeat: Infinity, duration: 1.6, repeatDelay: 0.6 } }}
      className="relative flex h-80 w-56 flex-col items-center justify-center overflow-hidden rounded-md border border-emerald-300/60 bg-gradient-to-b from-[#043a2a] via-[#0b7a57] to-[#021a12] shadow-[0_0_60px_-10px_rgba(16,185,129,0.8)]">
      <div className="absolute inset-0 bg-[repeating-linear-gradient(135deg,rgba(255,255,255,0.06)_0_2px,transparent_2px_14px)]" />
      <Sparkles className="relative text-emerald-200" size={40} />
      <p className="gx-display relative mt-4 text-3xl font-black uppercase tracking-wider text-white">GTEX</p>
      <p className="relative mt-1 text-xs font-bold uppercase tracking-[0.3em] text-emerald-200">Academy pack</p>
      <p className="gx-mono relative mt-6 text-sm text-white/80">{count} prospect{count > 1 ? "s" : ""}</p>
      <p className="relative mt-8 text-[11px] uppercase tracking-widest text-white/60">Tap to open</p>
    </motion.button>
  );
}

function Burst() {
  return (
    <motion.div className="pointer-events-none absolute inset-0 rounded-full bg-[radial-gradient(circle,rgba(110,231,183,0.7),transparent_60%)]"
      initial={{ scale: 0.2, opacity: 1 }} animate={{ scale: 2.4, opacity: 0 }} transition={{ duration: 0.8, ease: "easeOut" }} />
  );
}

export interface PackRevealProps {
  regens?: any[];
  players?: any[];
  onClose?: () => void;
  onDismiss?: () => void;
}

export function PackReveal({ regens, players, onClose, onDismiss }: PackRevealProps) {
  const items = regens ?? players ?? [];
  const handleClose = onClose ?? onDismiss ?? (() => {});
  const [step, setStep] = useState(-1);
  const done = step >= items.length;
  const current = items[step];
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") handleClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleClose]);
  if (!items.length) return null;
  const star = current && current.potential - current.rating >= 15;
  return (
    <div className="fixed inset-0 z-[60] flex flex-col items-center justify-center bg-black/85 px-4 backdrop-blur-md" data-testid="pack-reveal">
      <AnimatePresence mode="wait">
        {step === -1 && <SealedPack key="pack" count={items.length} onOpen={() => setStep(0)} />}
        {current && (
          <motion.div key={current.id} className="relative flex flex-col items-center" data-testid={`pack-reveal-card-${current.id}`}
            initial={{ rotateY: 90, scale: 0.7, opacity: 0 }} animate={{ rotateY: 0, scale: 1, opacity: 1 }} exit={{ x: -120, opacity: 0, scale: 0.8 }}
            transition={{ type: "spring", stiffness: 140, damping: 14 }} style={{ perspective: 1000 }}>
            <Burst />
            {star && <motion.p initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.4 }} className="gx-display mb-3 text-xl font-black uppercase tracking-widest text-amber-300" data-testid="pack-wonderkid-banner">Wonderkid pulled</motion.p>}
            <div className="w-56">
              <PlayerCard name={current.name} rating={current.rating} potential={current.potential} position={current.position} age={current.age} regen badge={star ? "Wonderkid" : "Academy"}
                stats={[{ k: "Ceiling", v: `+${Math.max(0, current.potential - current.rating)}` }, { k: "Morale", v: current.morale }, { k: "Value", v: fmt(current.value_coin) }]} />
            </div>
            <p className="gx-mono mt-4 text-xs text-slate-400">{step + 1} / {items.length}</p>
          </motion.div>
        )}
        {done && (
          <motion.div key="summary" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-4xl text-center" data-testid="pack-summary">
            <p className="gx-display mb-5 text-2xl font-black uppercase text-white">Your new academy intake</p>
            <div className="mx-auto grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {items.map((r, i) => (
                <motion.div key={r.id} initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
                  <PlayerCard name={r.name} rating={r.rating} potential={r.potential} position={r.position} age={r.age} regen />
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <div className="mt-8 flex gap-3">
        {step >= 0 && !done && <Btn onClick={() => setStep(step + 1)} data-testid="pack-next">{step + 1 === items.length ? "See all" : "Next prospect"}</Btn>}
        {step >= 0 && !done && <Btn variant="ghost" onClick={() => setStep(items.length)} data-testid="pack-skip">Skip</Btn>}
        {(done || step === -1) && <Btn variant={done ? "primary" : "ghost"} onClick={handleClose} data-testid="pack-close">{done ? "Welcome them to the club" : "Later"}</Btn>}
      </div>
    </div>
  );
}
