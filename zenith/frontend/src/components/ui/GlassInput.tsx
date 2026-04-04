import { forwardRef } from 'react';
import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';

interface GlassInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const GlassInput = forwardRef<HTMLInputElement, GlassInputProps>(
  ({ className = '', label, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-white/70 mb-1.5">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`
            w-full px-4 py-3 rounded-xl
            bg-white/5 border border-white/10
            backdrop-filter backdrop-blur-md
            text-white placeholder-white/40
            transition-all duration-300
            focus:bg-white/10 focus:border-neutral-400/50
            focus:ring-2 focus:ring-neutral-400/20
            disabled:opacity-50 disabled:cursor-not-allowed
            ${error ? 'border-red-400/50 focus:border-red-400/50' : ''}
            ${className}
          `}
          {...props}
        />
        {error && (
          <p className="mt-1.5 text-sm text-red-400">{error}</p>
        )}
      </div>
    );
  }
);

GlassInput.displayName = 'GlassInput';

interface GlassTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const GlassTextarea = forwardRef<HTMLTextAreaElement, GlassTextareaProps>(
  ({ className = '', label, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-white/70 mb-1.5">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={`
            w-full px-4 py-3 rounded-xl
            bg-white/5 border border-white/10
            backdrop-filter backdrop-blur-md
            text-white placeholder-white/40
            transition-all duration-300
            focus:bg-white/10 focus:border-neutral-400/50
            focus:ring-2 focus:ring-neutral-400/20
            disabled:opacity-50 disabled:cursor-not-allowed
            resize-none
            ${error ? 'border-red-400/50 focus:border-red-400/50' : ''}
            ${className}
          `}
          {...props}
        />
        {error && (
          <p className="mt-1.5 text-sm text-red-400">{error}</p>
        )}
      </div>
    );
  }
);

GlassTextarea.displayName = 'GlassTextarea';

export default GlassInput;
