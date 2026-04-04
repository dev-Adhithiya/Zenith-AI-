import { motion } from 'framer-motion';
import type { HTMLMotionProps } from 'framer-motion';

interface GlassPanelProps extends HTMLMotionProps<'div'> {
  variant?: 'default' | 'strong' | 'subtle';
  hover?: boolean;
}

export function GlassPanel({
  children,
  className = '',
  variant = 'default',
  hover = false,
  ...props
}: GlassPanelProps) {
  const baseClasses = {
    default: 'glass',
    strong: 'glass-strong',
    subtle: 'glass-subtle',
  };

  const hoverClass = hover ? 'glass-hover' : '';

  return (
    <motion.div
      className={`${baseClasses[variant]} ${hoverClass} ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export default GlassPanel;
