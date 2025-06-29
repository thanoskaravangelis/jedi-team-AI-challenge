import React, { useState } from 'react';
import ThinkingComponent from './ThinkingComponent';
import Citations from './Citations';
import CollapsibleSection from './CollapsibleSection';
import '../styles/Citations.css';
import '../styles/ThinkingComponent.css';
import '../styles/MessageFeedback.css';

const Message = ({ message, currentUser, onFeedback, messageFeedback }) => {
  // Local UI state for submission
  const [submitting, setSubmitting] = useState(false);
  const [showFeedbackMessage, setShowFeedbackMessage] = useState(false);

  // Only show feedback for assistant messages with a valid id (but not for initial thinking)
  const showFeedback = message.role === 'assistant' && 
                      !message.isThinking && 
                      !message.isInitialThinking && 
                      message.id && 
                      !message.streaming;

  // Get feedback status from props (loaded from backend)
  const feedbackType = messageFeedback?.type || null;

  const formatMessageText = (text) => {
    if (typeof text !== 'string') return '';
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  };

  const formatTime = (dateString) => {
    return new Date(dateString).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const avatar = message.role === 'user' 
    ? currentUser.charAt(0).toUpperCase()
    : 'AI';

  const intermediateStepsHtml = message.metadata?.intermediate_steps?.length > 0 && (
    <div className="intermediate-steps">
      <strong>Research Steps:</strong>
      {message.metadata.intermediate_steps.map((step, index) => (
        <div key={index} className="step-item">
          <div className="step-action">Step {index + 1}: {step.action || 'Processing'}</div>
          {step.thought && <div className="step-thought">{step.thought}</div>}
        </div>
      ))}
    </div>
  );

  const handleFeedback = async (type) => {
    if (submitting || feedbackType) return;
    
    setSubmitting(true);
    console.log('Submitting feedback:', { messageId: message.id, type });
    
    if (onFeedback) {
      const success = await onFeedback(message.id, type);
      if (success) {
        setShowFeedbackMessage(true);
        // Hide feedback message after 3 seconds
        setTimeout(() => setShowFeedbackMessage(false), 3000);
      }
    }
    setSubmitting(false);
  };

  if (message.isThinking) {
    console.log('🤖 RENDERING THINKING COMPONENT:', message.content, message.tool);
    return <ThinkingComponent message={message.content} tool={message.tool} />;
  }

  return (
    <div className={`message ${message.role} ${message.isInitialThinking ? 'initial-thinking' : ''}`}>
      <div className="message-avatar">{avatar}</div>
      <div className="message-content">
        {/* Show initial thinking header only if this is purely initial thinking */}
        {message.isInitialThinking && (
          <div className="initial-thinking-header">
            <i className="fas fa-brain"></i>
            <span>Initial Analysis</span>
          </div>
        )}
        <div className="message-bubble">
          {/* Only render the cleaned response, no summary/final answer */}
          {message.contentChunks ? (
            <div className="content-chunks">
              {message.contentChunks.map((chunk, index) => (
                <div key={index} className={`content-chunk ${chunk.section}`}>
                  {chunk.section === 'summary' ? (
                    // Key Insights - show normally without container
                    <div 
                      className="key-insights-content"
                      dangerouslySetInnerHTML={{ __html: formatMessageText(chunk.content) }}
                    />
                  ) : (
                    // Tool sections - show as collapsible
                    <CollapsibleSection
                      title={chunk.content.split('\n\n')[0]} // First line as title
                      content={chunk.content.split('\n\n').slice(1).join('\n\n')} // Rest as content
                      citations={chunk.citations || []}
                      toolsUsed={chunk.toolsUsed || []}
                      section={chunk.section}
                    />
                  )}
                </div>
              ))}
              {/* Don't show overall citations - only individual chunk citations to avoid duplication */}
              {message.streaming && (
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              )}
            </div>
          ) : (
            /* Regular message format */
            <div>
              <div 
                className="message-text"
                dangerouslySetInnerHTML={{ __html: formatMessageText(message.content) }}
              />
              {intermediateStepsHtml}
              {/* Add Citations for assistant messages */}
              {message.role === 'assistant' && !message.isThinking && (
                <Citations 
                  citations={message.citations || []} 
                  toolsUsed={message.toolsUsed || []} 
                />
              )}
            </div>
          )}
        </div>
        <div className="message-meta">{formatTime(message.created_at)}</div>
        {/* Like/Dislike feedback for assistant messages only */}
        {showFeedback && (
          <div className="message-feedback">
            <button
              className={`feedback-btn thumbs-up${feedbackType === 'thumbs_up' ? ' selected' : ''}`}
              onClick={() => handleFeedback('thumbs_up')}
              disabled={!!feedbackType || submitting}
              title="Like this response"
            >
              <i className={`fas fa-thumbs-up${feedbackType === 'thumbs_up' ? '' : ' fa-regular'}`}></i>
            </button>
            <button
              className={`feedback-btn thumbs-down${feedbackType === 'thumbs_down' ? ' selected' : ''}`}
              onClick={() => handleFeedback('thumbs_down')}
              disabled={!!feedbackType || submitting}
              title="Dislike this response"
            >
              <i className={`fas fa-thumbs-down${feedbackType === 'thumbs_down' ? '' : ' fa-regular'}`}></i>
            </button>
            {submitting && (
              <span className="feedback-status submitting">
                <i className="fas fa-spinner fa-spin"></i> Submitting...
              </span>
            )}
            {showFeedbackMessage && feedbackType && (
              <span className="feedback-status success">
                <i className="fas fa-check"></i> Feedback submitted!
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Message;
