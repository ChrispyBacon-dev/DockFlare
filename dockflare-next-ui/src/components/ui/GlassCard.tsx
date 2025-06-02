import React from 'react';

export interface GlassCardProps { 
  children: React.ReactNode;
  className?: string;
  onClick?: () => void; 
  style?: React.CSSProperties; 
}

const GlassCard: React.FC<GlassCardProps> = ({ children, className = '', onClick, style }) => { // Destructure style
  return (
    <div
      className={`
        bg-slate-700/30 backdrop-blur-lg 
        border border-slate-500/40 
        rounded-xl 
        p-4 sm:p-6 
        shadow-xl 
        transition-all duration-300 ease-in-out
        hover:shadow-cyan-500/20 hover:border-cyan-500/60
        ${onClick ? 'cursor-pointer' : ''}
        ${className}
      `}
      onClick={onClick}
      style={style} 
    >
      {children}
    </div>
  );
};

export default GlassCard;