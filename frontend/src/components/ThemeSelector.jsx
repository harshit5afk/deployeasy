import React, { useState, useRef, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';

export function ThemeSelector({ style, compact = false }) {
  const { theme, setTheme, themes } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const currentTheme = themes.find((t) => t.id === theme) || themes[0];

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div ref={dropdownRef} style={{ position: 'relative', display: 'inline-block', ...style }}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        title="Change dashboard theme"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.45rem',
          padding: compact ? '0.35rem 0.65rem' : '0.45rem 0.85rem',
          fontSize: '0.82rem',
          fontWeight: 600,
          color: 'var(--text-main)',
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          cursor: 'pointer',
          transition: 'all 0.15s ease',
        }}
      >
        <span style={{ fontSize: '1rem' }}>{currentTheme.icon}</span>
        {!compact && <span>{currentTheme.name}</span>}
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: currentTheme.color,
            boxShadow: `0 0 8px ${currentTheme.color}`,
            display: 'inline-block',
          }}
        />
        <svg
          width="12"
          height="12"
          viewBox="0 0 16 16"
          fill="currentColor"
          style={{
            transform: isOpen ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.2s ease',
            color: 'var(--text-muted)',
          }}
        >
          <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z" />
        </svg>
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            right: 0,
            zIndex: 100,
            minWidth: '210px',
            background: 'var(--bg-card-hover)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '0.4rem',
            boxShadow: '0 12px 30px rgba(0, 0, 0, 0.5)',
          }}
        >
          <div
            style={{
              padding: '0.35rem 0.65rem 0.45rem',
              fontSize: '0.72rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              color: 'var(--text-dim)',
              letterSpacing: '0.05em',
              borderBottom: '1px solid var(--border)',
              marginBottom: '0.3rem',
            }}
          >
            Select Theme ({themes.length})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            {themes.map((t) => {
              const isActive = t.id === theme;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => {
                    setTheme(t.id);
                    setIsOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    padding: '0.5rem 0.65rem',
                    fontSize: '0.82rem',
                    color: isActive ? '#fff' : 'var(--text-main)',
                    background: isActive ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                    border: isActive ? '1px solid var(--primary)' : '1px solid transparent',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
                    <span>{t.icon}</span>
                    <div>
                      <div style={{ fontWeight: isActive ? 700 : 500, lineHeight: 1.2 }}>{t.name}</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{t.desc}</div>
                    </div>
                  </div>
                  <span
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      backgroundColor: t.color,
                      boxShadow: isActive ? `0 0 10px ${t.color}` : 'none',
                      flexShrink: 0,
                    }}
                  />
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
