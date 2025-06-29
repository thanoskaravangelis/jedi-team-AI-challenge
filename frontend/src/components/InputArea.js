import React, { useState, useRef, useEffect } from 'react';

const InputArea = ({ onSendMessage, isStreaming }) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef(null);

  const autoResizeTextarea = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  };

  useEffect(() => {
    autoResizeTextarea();
  }, [message]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isStreaming) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="input-container">
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          className="message-input"
          placeholder="Ask me about market research, consumer behavior, or industry trends..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          rows="1"
        />
        <button
          className="send-button"
          onClick={handleSubmit}
          disabled={isStreaming || !message.trim()}
        >
          <i className="fas fa-paper-plane"></i>
        </button>
      </div>
    </div>
  );
};

export default InputArea;
