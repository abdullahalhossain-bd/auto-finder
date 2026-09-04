import { useEffect, useState } from 'react'

const COLORS = ['#0ea5e9', '#22c55e', '#f59e0b', '#ec4899', '#8b5cf6']

/**
 * Fires a short-lived burst of confetti pieces from the center-top of the
 * viewport. Pure CSS animation, no external deps. Mount conditionally with
 * a `key` that changes each time you want a fresh burst.
 */
export function Confetti({ pieces = 40 }: { pieces?: number }) {
  const [items] = useState(() =>
    Array.from({ length: pieces }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 0.3,
      duration: 1.4 + Math.random() * 1.1,
      rotate: Math.random() * 360,
      color: COLORS[i % COLORS.length],
      size: 6 + Math.random() * 6,
      drift: (Math.random() - 0.5) * 160,
    })),
  )

  useEffect(() => {
    // no-op effect just to satisfy hooks lint; component is meant to be
    // unmounted by the parent ~2s after mounting
  }, [])

  return (
    <div
      className="pointer-events-none fixed inset-0 z-[200] overflow-hidden"
      aria-hidden
    >
      {items.map((p) => (
        <span
          key={p.id}
          style={{
            position: 'absolute',
            top: '-5%',
            left: `${p.left}%`,
            width: p.size,
            height: p.size * 0.4,
            backgroundColor: p.color,
            borderRadius: 2,
            transform: `rotate(${p.rotate}deg)`,
            animation: `confetti-fall ${p.duration}s ease-in ${p.delay}s forwards`,
            // custom property consumed by the keyframes below
            ['--drift' as any]: `${p.drift}px`,
          }}
        />
      ))}
      <style>{`
        @keyframes confetti-fall {
          0% {
            opacity: 1;
            transform: translate3d(0, 0, 0) rotate(0deg);
          }
          100% {
            opacity: 0;
            transform: translate3d(var(--drift), 110vh, 0) rotate(540deg);
          }
        }
      `}</style>
    </div>
  )
}
