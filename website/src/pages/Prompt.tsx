import React, { useRef } from 'react';
import Layout from '@theme/Layout';
import { useState } from 'react';

const promptText = `
`;

export default function PromptPage() {
  const preRef = useRef<HTMLPreElement>(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (preRef.current) {
      navigator.clipboard.writeText(promptText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <Layout title="LLMBrick Prompt">
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1rem' }}>
        <h1>LLMBrick Prompt</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <button
            onClick={handleCopy}
            style={{
              padding: '0.5rem 1.2rem',
              fontSize: '1rem',
              cursor: 'pointer',
              background: '#3578e5',
              color: 'white',
              border: 'none',
              borderRadius: 4,
            }}
          >
            一鍵複製
          </button>
          {copied && (
            <span style={{ color: '#3578e5', fontWeight: 600, fontSize: '1rem' }}>
              已複製!
            </span>
          )}
        </div>
        <pre
          ref={preRef}
          style={{
            background: '#222',
            color: '#fff',
            padding: '1.5rem',
            borderRadius: 8,
            overflowX: 'auto',
            fontSize: '0.95rem',
            lineHeight: 1.5,
            maxHeight: 600,
          }}
        >
          {promptText}
        </pre>
      </div>
    </Layout>
  );
}