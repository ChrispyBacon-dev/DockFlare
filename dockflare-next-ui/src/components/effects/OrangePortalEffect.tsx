// src/components/effects/OrangePortalEffect.tsx - PORTAL ... :)
'use client';

import React, { useEffect, useRef } from 'react';
import styles from './PortalEffects.module.css';
import { MiniContainer, MINI_PORTAL_CONFIG } from './MiniContainer'; 

interface PortalEffectProps {
  isVisible: boolean;
  size?: number; 
}

const OVAL_ASPECT_RATIO_WIDTH_FACTOR = 50 / 70; 

const ORANGE_THEME_COLORS = ['#b45309', '#d97706', '#f59e0b']; 

const OrangePortalEffect: React.FC<PortalEffectProps> = ({ isVisible, size = 40 }) => { 
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameId = useRef<number | null>(null);
  const containersRef = useRef<MiniContainer[]>([]);
  const timeoutsRef = useRef<NodeJS.Timeout[]>([]);

  const ovalHeight = size;
  const ovalWidth = Math.round(size * OVAL_ASPECT_RATIO_WIDTH_FACTOR);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');

    const cleanupAnimation = () => {
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
        animationFrameId.current = null;
      }
      timeoutsRef.current.forEach(clearTimeout);
      timeoutsRef.current = [];
      containersRef.current = [];
      if (canvas && ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    };

    if (!isVisible) {
      cleanupAnimation();
      return; 
    }

    if (!canvas || !ctx) {
      return cleanupAnimation; 
    }

    canvas.width = ovalWidth;   
    canvas.height = ovalHeight; 

    const portalRadiusX = ovalWidth / 2; 
    const portalRadiusY = ovalHeight / 2;
    const portalCenterX = ovalWidth / 2;
    if (containersRef.current.length === 0) {
      for (let i = 0; i < MINI_PORTAL_CONFIG.NUM_CONTAINERS_PER_EFFECT; i++) {
        const timeoutId = setTimeout(() => {
          if (canvasRef.current) { 
            containersRef.current.push(
              new MiniContainer(
                'orange', 
                canvas.width, 
                canvas.height, 
                portalCenterX, 
                portalRadiusX, 
                portalRadiusY, 
                ORANGE_THEME_COLORS
              )
            );
          }
        }, i * MINI_PORTAL_CONFIG.STAGGER_SPAWN_DELAY + MINI_PORTAL_CONFIG.STAGGER_SPAWN_DELAY / 2); 
        timeoutsRef.current.push(timeoutId);
      }
    }
    
    const animate = () => {
      if (!canvasRef.current || !canvasRef.current.getContext('2d') || !isVisible) {
        if (animationFrameId.current) cancelAnimationFrame(animationFrameId.current);
        animationFrameId.current = null;
        return;
      }
      const currentCtx = canvasRef.current.getContext('2d');
      if(!currentCtx) return;

      currentCtx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
      containersRef.current.forEach(container => {
        container.update(); 
        container.draw(currentCtx);
      });
      animationFrameId.current = requestAnimationFrame(animate);
    };

    if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
    }
    animationFrameId.current = requestAnimationFrame(animate);

    return cleanupAnimation; 
  }, [isVisible, ovalWidth, ovalHeight]); 

  return (
    <div 
      className={`${styles.portalBase} ${isVisible ? styles.portalVisible : styles.portalHidden} ${styles.tableOrangePortal}`}
      style={{ width: `${ovalWidth}px`, height: `${ovalHeight}px` }} 
    >
      <canvas ref={canvasRef} width={ovalWidth} height={ovalHeight} className={styles.portalCanvas}></canvas>
    </div>
  );
};

export default OrangePortalEffect;