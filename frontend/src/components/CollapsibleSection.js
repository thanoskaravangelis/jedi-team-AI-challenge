import React, { useState } from 'react';
import Citations from './Citations';

const CollapsibleSection = ({ title, content, citations = [], toolsUsed = [], section }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  // Function to format markdown text
  const formatMarkdownText = (text) => {
    if (typeof text !== 'string') return '';
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/### (.*?)$/gm, '<h3>$1</h3>')
      .replace(/## (.*?)$/gm, '<h2>$1</h2>')
      .replace(/# (.*?)$/gm, '<h1>$1</h1>')
      .replace(/\n/g, '<br>');
  };

  return (
    <div className={`collapsible-section ${section}`}>
      <button 
        className="section-toggle"
        onClick={toggleExpanded}
        aria-expanded={isExpanded}
      >
        <span className={`toggle-icon ${isExpanded ? 'expanded' : ''}`}>
          ▶
        </span>
        <span className="section-title" dangerouslySetInnerHTML={{ __html: formatMarkdownText(title) }} />
      </button>
      
      {isExpanded && (
        <div className="section-content">
          <div 
            className="section-text"
            dangerouslySetInnerHTML={{ __html: formatMarkdownText(content) }}
          />
          {citations && citations.length > 0 && (
            <Citations 
              citations={citations} 
              toolsUsed={toolsUsed} 
            />
          )}
        </div>
      )}
    </div>
  );
};

export default CollapsibleSection;
