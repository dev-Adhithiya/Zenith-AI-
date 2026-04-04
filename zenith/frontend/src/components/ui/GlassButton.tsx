import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

interface GlassButtonProps {
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'primary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  onClick?: () => void;
  title?: string;
}

export function GlassButton({
  children,
  className = '',
  variant = 'default',
  size = 'md',
  isLoading = false,
  disabled,
  type = 'button',
  onClick,
  title,
}: GlassButtonProps) {
  const baseStyles = `
    relative overflow-hidden font-medium transition-all duration-300
    backdrop-filter backdrop-blur-md
    disabled:opacity-50 disabled:cursor-not-allowed
    focus:outline-none focus:ring-2 focus:ring-neutral-400/50
    flex items-center justify-center
  `;

  const variantStyles = {
    default: `
      bg-white/5 border border-white/10
      hover:bg-white/10 hover:border-white/20
      active:bg-white/15
    `,
    primary: `
      bg-gradient-to-r from-neutral-600/80 to-neutral-500/80
      border border-neutral-400/30
      hover:from-neutral-500/90 hover:to-neutral-400/90
      hover:border-neutral-400/50
      active:from-neutral-600/90 active:to-neutral-500/90
      shadow-lg shadow-neutral-500/20
      text-white
    `,
    ghost: `
      bg-transparent border border-transparent
      hover:bg-white/5 hover:border-white/10
      active:bg-white/10
    `,
  };

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-sm rounded-lg',
    md: 'px-4 py-2 text-sm rounded-xl',
    lg: 'px-6 py-3 text-base rounded-xl',
  };

  return (
    <motion.button
      type={type}
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      disabled={disabled || isLoading}
      onClick={onClick}
      title={title}
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
    >
      {isLoading ? (
        <span className="flex items-center justify-center gap-2">
          <motion.span
            className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          />
          Loading...
        </span>
      ) : (
        children
      )}
    </motion.button>
  );
}

export default GlassButton;
