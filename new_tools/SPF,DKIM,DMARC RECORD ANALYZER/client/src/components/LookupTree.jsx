import React from 'react';

export default function LookupTree({ tree }) {
  if (!tree || tree.length === 0) return null;

  return (
    <div className="tree-viewer">
      <div style={{ fontWeight: 700, fontSize: '0.8rem', color: '#94a3b8', letterSpacing: '0.05em', marginBottom: 8, textTransform: 'uppercase' }}>
        RECURSIVE SPF LOOKUP TREE & INCLUDES (RFC 7208 10-LOOKUP CAP TRACE):
      </div>
      <pre style={{ fontSize: '0.85rem', fontFamily: 'JetBrains Mono, monospace', color: '#38bdf8', overflowX: 'auto', margin: 0 }}>
        {JSON.stringify(tree, null, 2)}
      </pre>
    </div>
  );
}
