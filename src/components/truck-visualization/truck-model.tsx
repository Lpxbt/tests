import React, { useEffect, useRef } from 'react';

interface TruckModelProps {
  isAnimating: boolean;
}

export function TruckModel({ isAnimating }: TruckModelProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const requestIdRef = useRef<number | null>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Set canvas dimensions
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    
    // Load truck image
    const truckImage = new Image();
    truckImage.src = '/truck.png';
    
    let position = 0;
    let direction = 1;
    
    const draw = () => {
      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Draw background (road)
      ctx.fillStyle = '#f0f0f0';
      ctx.fillRect(0, canvas.height - 40, canvas.width, 40);
      
      // Draw truck if image is loaded
      if (truckImage.complete) {
        const truckWidth = canvas.width * 0.7;
        const truckHeight = truckWidth * (truckImage.height / truckImage.width);
        
        // Calculate position for animation
        if (isAnimating) {
          position += 0.5 * direction;
          
          // Change direction when reaching edges
          if (position > 20 || position < -20) {
            direction *= -1;
          }
        }
        
        // Draw truck with slight bouncing effect
        ctx.drawImage(
          truckImage,
          (canvas.width - truckWidth) / 2,
          canvas.height - truckHeight - 40 + Math.sin(position * 0.1) * 2, // Add slight bounce
          truckWidth,
          truckHeight
        );
      } else {
        // Placeholder if image is not loaded
        ctx.fillStyle = '#999';
        ctx.fillRect((canvas.width - 200) / 2, canvas.height - 100 - 40, 200, 100);
      }
      
      // Continue animation
      if (isAnimating) {
        requestIdRef.current = requestAnimationFrame(draw);
      }
    };
    
    // Start animation
    if (isAnimating) {
      requestIdRef.current = requestAnimationFrame(draw);
    } else {
      draw(); // Draw once if not animating
    }
    
    // Handle window resize
    const handleResize = () => {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
      draw();
    };
    
    window.addEventListener('resize', handleResize);
    
    // Cleanup
    return () => {
      if (requestIdRef.current) {
        cancelAnimationFrame(requestIdRef.current);
      }
      window.removeEventListener('resize', handleResize);
    };
  }, [isAnimating]);
  
  return (
    <canvas 
      ref={canvasRef} 
      className="w-full h-full"
      style={{ touchAction: 'none' }}
    />
  );
}
