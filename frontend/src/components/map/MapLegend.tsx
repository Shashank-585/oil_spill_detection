import React, { useState } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

export const MapLegend: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [showSecondary, setShowSecondary] = useState(false);

  // Default Contextual Layers (Deep Ocean + Warm Sand Palette)
  const defaultItems = [
    {
      label: 'Incident',
      symbol: (
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: 'var(--color-warning-rust)',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Detected slick',
      symbol: (
        <span
          style={{
            width: '10px',
            height: '6px',
            borderRadius: '1px',
            border: '1px solid #E0C994',
            backgroundColor: 'rgba(209, 178, 124, 0.65)',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Selected vessel',
      symbol: (
        <span
          style={{
            width: '14px',
            height: '2.5px',
            backgroundColor: '#D1B27C',
            borderRadius: '1px',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Selected drift',
      symbol: (
        <span
          style={{
            width: '14px',
            height: '2px',
            backgroundColor: '#5F918A',
            borderRadius: '1px',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Source hypothesis',
      symbol: (
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: '#B86F52',
            border: '1.5px solid #ffffff',
            display: 'inline-block',
          }}
        />
      ),
    },
  ];

  // Secondary Layers (Restrained, Muted)
  const secondaryItems = [
    {
      label: 'Other vessels',
      symbol: (
        <span
          style={{
            width: '12px',
            height: '1.5px',
            backgroundColor: 'rgba(78, 107, 105, 0.65)',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Lagrangian particles',
      symbol: (
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: '#78AFA5',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Forward simulation plume',
      symbol: (
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: '#78AFA5',
            display: 'inline-block',
          }}
        />
      ),
    },
    {
      label: 'Centroid offset error',
      symbol: (
        <span
          style={{
            width: '12px',
            height: '2px',
            backgroundColor: '#B86F52',
            display: 'inline-block',
          }}
        />
      ),
    },
  ];

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '10px',
        right: '12px',
        zIndex: 10,
        backgroundColor: 'rgba(16, 35, 38, 0.94)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-xs)',
        boxShadow: 'var(--shadow-md)',
        userSelect: 'none',
        backdropFilter: 'blur(6px)',
      }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 8px',
          fontSize: '10px',
          fontWeight: 700,
          color: isOpen ? 'var(--color-accent-teal)' : 'var(--color-text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          cursor: 'pointer',
          background: 'none',
          border: 'none',
        }}
        title="Toggle Map Legend"
      >
        <span>LEGEND</span>
        {isOpen ? <ChevronDown size={11} /> : <ChevronUp size={11} />}
      </button>

      {isOpen && (
        <div
          style={{
            padding: '5px 8px 6px 8px',
            borderTop: '1px solid var(--color-border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            fontSize: '11px',
            minWidth: '160px',
          }}
        >
          {defaultItems.map((item, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '16px', display: 'flex', justifyContent: 'center' }}>
                {item.symbol}
              </div>
              <span style={{ color: 'var(--color-text-primary)' }}>{item.label}</span>
            </div>
          ))}

          {/* Secondary layers toggle */}
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', marginTop: '4px', paddingTop: '4px' }}>
            <button
              onClick={() => setShowSecondary(!showSecondary)}
              style={{
                fontSize: '9px',
                fontWeight: 600,
                color: 'var(--color-accent-seafoam)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 0',
              }}
            >
              <span>{showSecondary ? 'Hide secondary layers' : '+ Secondary layers'}</span>
            </button>
            {showSecondary && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
                {secondaryItems.map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '16px', display: 'flex', justifyContent: 'center' }}>
                      {item.symbol}
                    </div>
                    <span style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>{item.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
