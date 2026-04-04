import { motion } from 'framer-motion';

interface GlassToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  label?: string;
  disabled?: boolean;
}

export function GlassToggle({ enabled, onChange, label, disabled = false }: GlassToggleProps) {
  return (
    <label className={`flex items-center gap-3 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        disabled={disabled}
        onClick={() => !disabled && onChange(!enabled)}
        className={`
          relative w-12 h-6 rounded-full
          transition-all duration-300
          ${enabled 
            ? 'bg-gradient-to-r from-neutral-500 to-neutral-400 border-neutral-400/50' 
            : 'bg-white/10 border-white/20'
          }
          border backdrop-filter backdrop-blur-md
          focus:outline-none focus:ring-2 focus:ring-neutral-400/50
        `}
      >
        <motion.span
          className={`
            absolute top-0.5 w-5 h-5 rounded-full
            bg-white shadow-lg
          `}
          animate={{
            left: enabled ? '1.5rem' : '0.125rem',
          }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      </button>
      {label && (
        <span className="text-sm font-medium text-white/80">{label}</span>
      )}
    </label>
  );
}

export default GlassToggle;
