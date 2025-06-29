import React, { useState } from 'react';

const Citations = ({ citations = [], toolsUsed = [] }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Always show if we have citations or tools
  if (!citations.length && !toolsUsed.length) return null;

  console.log('Citations component received:', { citations: citations.length, toolsUsed, types: citations.map(c => c.type) });

  const getCitationIcon = (type) => {
    switch (type) {
      case 'internal':
        return '🗂️';
      case 'web':
        return '🌐';
      case 'quality':
        return '⚡';
      case 'similarity':  // Legacy support if any old data exists
        return '🗂️';  // Treat as internal
      default:
        return '📄';
    }
  };

  const getCitationColor = (type) => {
    switch (type) {
      case 'internal':
        return 'blue';
      case 'web':
        return 'green';
      case 'quality':
        return 'orange';
      case 'similarity':  // Legacy support
        return 'blue';  // Treat as internal
      default:
        return 'gray';
    }
  };

  return (
    <div className="citations-container">
      <button
        className="citations-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="toggle-icon">
          {isExpanded ? '▼' : '▶'}
        </span>
        <span className="citations-label">
          Sources & Citations ({citations.length})
        </span>
        {toolsUsed.length > 0 && (
          <div className="tools-used">
            {toolsUsed.map((tool, idx) => (
              <span key={idx} className="tool-badge">
                {tool.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </span>
            ))}
          </div>
        )}
      </button>
      
      {isExpanded && (
        <div className="citations-content">
          {citations.map((citation, index) => (
            <div key={index} className={`citation-item ${getCitationColor(citation.type)}`}>
              <div className="citation-header">
                <span className="citation-icon">
                  {getCitationIcon(citation.type)}
                </span>
                <span className="citation-source">{citation.source}</span>
                <span className={`citation-type-badge ${citation.type}`}>
                  {citation.type}
                </span>
              </div>
              
              {citation.snippet && (
                <div className="citation-snippet">
                  "{citation.snippet}"
                </div>
              )}
              
              {citation.data && (
                <div className="citation-data">
                  {citation.data}
                </div>
              )}
              
              {citation.relevance && (
                <div className="citation-relevance">
                  <em>{citation.relevance}</em>
                </div>
              )}
              
              {citation.url && (
                <div className="citation-url">
                  <a href={citation.url} target="_blank" rel="noopener noreferrer">
                    View Source ↗
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Citations;
