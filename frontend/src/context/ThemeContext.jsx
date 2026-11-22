import React, { createContext, useContext, useState, useEffect } from 'react';

export const THEMES = [
  { id: 'cosmic', name: 'Cosmic Violet', icon: '🌌', color: '#8b5cf6', desc: 'Default Violet & Indigo' },
  { id: 'cyberpunk', name: 'Cyberpunk Neon', icon: '⚡', color: '#00f0ff', desc: 'Cyan & Neon Glow' },
  { id: 'emerald', name: 'Emerald Matrix', icon: '🌲', color: '#10b981', desc: 'Mint & Terminal Green' },
  { id: 'crimson', name: 'Crimson Sunset', icon: '🔥', color: '#f43f5e', desc: 'Rose & Warm Ember' },
  { id: 'ocean', name: 'Deep Ocean', icon: '🌊', color: '#38bdf8', desc: 'Sapphire & Nordic Blue' },
  { id: 'amber', name: 'Obsidian Gold', icon: '✨', color: '#f59e0b', desc: 'Amber & Solar Gold' }
];

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    return localStorage.getItem('deployeasy_theme') || 'cosmic';
  });

  const setTheme = (newTheme) => {
    setThemeState(newTheme);
    localStorage.setItem('deployeasy_theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  useEffect(() => {
    const saved = localStorage.getItem('deployeasy_theme') || 'cosmic';
    document.documentElement.setAttribute('data-theme', saved);
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, themes: THEMES }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
  return ctx;
}
