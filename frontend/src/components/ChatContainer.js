import React, { useEffect, useRef } from 'react';
import Message from './Message';
import '../styles/FeedbackWidget.css'; // Create this CSS file for styling

const ChatContainer = ({ messages, currentUser, onFeedback, feedbackState }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="messages-container active">
      {messages.map((message, index) => (
        <Message
          key={index}
          message={message}
          currentUser={currentUser}
          onFeedback={onFeedback} // pass feedback handler
          messageFeedback={feedbackState[message.id] || null} // pass feedback for this specific message
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatContainer;
