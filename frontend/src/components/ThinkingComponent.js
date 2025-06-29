import React from 'react';

const ThinkingComponent = ({ message = 'Thinking...', tool = 'system' }) => {
  console.log('🤖 THINKING COMPONENT RENDERING:', { message, tool });
  
  const getToolIcon = (toolName) => {
    switch (toolName) {
      // case 'internal_data_search':  // Commented out
      //   return '🗂️';
      case 'similarity_search':
        return '🗂️';  // Now uses internal research icon
      case 'web_search':
        return '🌐';
      // case 'answer_quality_classifier':  // Commented out
      //   return '⚡';
      case 'system':
        return '🤖';
      default:
        return '🔧';
    }
  };

  const getToolDisplayName = (toolName) => {
    switch (toolName) {
      // case 'internal_data_search':  // Commented out
      //   return 'Internal Research';
      case 'similarity_search':
        return 'Internal Research';  // Now displays as internal research
      case 'web_search':
        return 'Web Search';
      // case 'answer_quality_classifier':  // Commented out
      //   return 'Quality Check';
      case 'system':
        return 'System';
      default:
        return toolName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
  };

  const getToolColor = (toolName) => {
    switch (toolName) {
      // case 'internal_data_search':  // Commented out
      //   return '#2563eb'; // blue
      case 'similarity_search':
        return '#2563eb'; // blue (same as internal research)
      case 'web_search':
        return '#16a34a'; // green
      // case 'answer_quality_classifier':  // Commented out
      //   return '#ea580c'; // orange
      case 'system':
        return '#6b7280'; // gray
      default:
        return '#6b7280';
    }
  };

  return (
    <div className="thinking-component enhanced">
      <div className="thinking-avatar-enhanced">
        <div 
          className="tool-icon-container"
          style={{ borderColor: getToolColor(tool) }}
        >
          <span className="tool-icon">{getToolIcon(tool)}</span>
          <div className="thinking-spinner-enhanced"></div>
        </div>
      </div>
      <div className="thinking-content-enhanced">
        <div className="tool-name" style={{ color: getToolColor(tool) }}>
          {getToolDisplayName(tool)}
        </div>
        <div className="thinking-text-enhanced">{message}</div>
      </div>
    </div>
  );
};

export default ThinkingComponent;
