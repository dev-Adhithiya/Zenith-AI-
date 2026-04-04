import { motion } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';

export function MeshGradient() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDarkMode, setIsDarkMode] = useState(true);

  useEffect(() => {
    // Check initial theme
    const checkTheme = () => {
      setIsDarkMode(!document.documentElement.classList.contains('light'));
    };
    
    checkTheme();
    
    // Watch for theme changes
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let time = 0;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    const createGradient = (x: number, y: number, radius: number, color: string) => {
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
      gradient.addColorStop(0, color);
      gradient.addColorStop(1, 'transparent');
      return gradient;
    };

    const animate = () => {
      time += 0.002;

      // Background color based on theme
      ctx.fillStyle = isDarkMode ? '#141414' : '#f0f0f0';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Animated gradient blobs with grey tones
      const blobs = isDarkMode ? [
        {
          x: canvas.width * 0.3 + Math.sin(time * 0.7) * 100,
          y: canvas.height * 0.4 + Math.cos(time * 0.5) * 80,
          radius: 400,
          color: 'rgba(80, 80, 80, 0.25)', // Dark grey
        },
        {
          x: canvas.width * 0.7 + Math.cos(time * 0.6) * 120,
          y: canvas.height * 0.6 + Math.sin(time * 0.8) * 100,
          radius: 350,
          color: 'rgba(60, 60, 60, 0.3)', // Darker grey
        },
        {
          x: canvas.width * 0.5 + Math.sin(time * 0.5) * 80,
          y: canvas.height * 0.3 + Math.cos(time * 0.7) * 60,
          radius: 300,
          color: 'rgba(50, 50, 50, 0.35)', // Very dark grey
        },
        {
          x: canvas.width * 0.2 + Math.cos(time * 0.4) * 60,
          y: canvas.height * 0.8 + Math.sin(time * 0.6) * 50,
          radius: 250,
          color: 'rgba(70, 70, 70, 0.25)', // Medium dark grey
        },
      ] : [
        {
          x: canvas.width * 0.3 + Math.sin(time * 0.7) * 100,
          y: canvas.height * 0.4 + Math.cos(time * 0.5) * 80,
          radius: 400,
          color: 'rgba(200, 200, 200, 0.4)', // Light grey
        },
        {
          x: canvas.width * 0.7 + Math.cos(time * 0.6) * 120,
          y: canvas.height * 0.6 + Math.sin(time * 0.8) * 100,
          radius: 350,
          color: 'rgba(180, 180, 180, 0.35)', // Slightly darker
        },
        {
          x: canvas.width * 0.5 + Math.sin(time * 0.5) * 80,
          y: canvas.height * 0.3 + Math.cos(time * 0.7) * 60,
          radius: 300,
          color: 'rgba(220, 220, 220, 0.5)', // Very light grey
        },
        {
          x: canvas.width * 0.2 + Math.cos(time * 0.4) * 60,
          y: canvas.height * 0.8 + Math.sin(time * 0.6) * 50,
          radius: 250,
          color: 'rgba(190, 190, 190, 0.3)', // Medium light grey
        },
      ];

      blobs.forEach(blob => {
        ctx.fillStyle = createGradient(blob.x, blob.y, blob.radius, blob.color);
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      });

      animationId = requestAnimationFrame(animate);
    };

    resize();
    window.addEventListener('resize', resize);
    animate();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, [isDarkMode]);

  return (
    <motion.canvas
      ref={canvasRef}
      className="fixed inset-0 -z-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1 }}
    />
  );
}

export default MeshGradient;
