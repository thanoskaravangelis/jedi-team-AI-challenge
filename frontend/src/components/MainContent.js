import React, { useState, useEffect } from 'react';
import WelcomeScreen from './WelcomeScreen';
import ChatContainer from './ChatContainer';
import InputArea from './InputArea';

const MainContent = ({
  theme,
  onToggleTheme,
  onToggleSidebar,
  currentUser,
  currentConversationId,
  isStreaming,
  onLogout,
  onStreamQuery,
  loadConversationMessages,
  loadConversations,
  setCurrentConversationId,
  submitFeedback // <-- add this prop
}) => {
  const [messages, setMessages] = useState([]);
  const [showWelcome, setShowWelcome] = useState(true);
  const [feedbackState, setFeedbackState] = useState({}); // Map of messageId -> feedback

  // Load messages when conversation changes
  useEffect(() => {
    if (currentConversationId) {
      loadConversationMessages(currentConversationId).then((loadedMessages) => {
        setMessages(loadedMessages || []);
        setShowWelcome(false);
        
        // Extract feedback state from loaded messages
        const newFeedbackState = {};
        (loadedMessages || []).forEach(message => {
          if (message.metadata?.user_feedback) {
            newFeedbackState[message.id] = message.metadata.user_feedback;
          }
        });
        setFeedbackState(newFeedbackState);
      });
    } else {
      setMessages([]);
      setShowWelcome(true);
      setFeedbackState({});
    }
  }, [currentConversationId, loadConversationMessages]);

  const handleUserMenuClick = () => {
    if (window.confirm('Do you want to log out?')) {
      onLogout();
    }
  };

  const handleSendMessage = async (query) => {
    if (!query.trim() || isStreaming) return;

    setShowWelcome(false);
    
    // Add user message to UI immediately with unique ID
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    // Handle new conversation case
    if (!currentConversationId) {
      // Create a temporary conversation ID for UI purposes only
      const tempConversationId = `temp-${Date.now()}`;
      setCurrentConversationId(tempConversationId);
    }

    // Add initial thinking indicator
    const initialThinkingMessage = {
      id: 'initial-thinking-indicator',
      role: 'assistant',
      content: 'Analyzing your query...',
      isThinking: true,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, initialThinkingMessage]);

    // Stream the response
    await onStreamQuery(query, (messageData) => {
      setMessages(prev => {
        
        if (messageData.type === 'initial_thinking') {
          // Remove initial thinking indicator, add actual initial thinking
          const filteredMessages = prev.filter(msg => msg.id !== 'initial-thinking-indicator');
          return [...filteredMessages, {
            id: `initial-thinking-${Date.now()}`,
            role: 'assistant',
            content: messageData.data,
            created_at: new Date().toISOString(),
            isInitialThinking: true,
            streaming: true
          }];
        } else if (messageData.type === 'thinking') {
          
          // SIMPLE APPROACH: Just add the thinking message, no complex filtering
          const thinkingMessage = {
            id: 'thinking',
            role: 'assistant',
            content: messageData.data,
            tool: messageData.tool || 'system',
            isThinking: true,
            created_at: new Date().toISOString()
          };
          
          // Remove any existing thinking message and add the new one
          const withoutThinking = prev.filter(msg => msg.id !== 'thinking');
          const result = [...withoutThinking, thinkingMessage];
          
          return result;
        } else if (messageData.type === 'content_chunk') {
          // Handle streaming content chunks - find the initial thinking message to append to
          const existingMessage = prev.find(msg => 
            msg.role === 'assistant' && !msg.isThinking && (msg.streaming || msg.isInitialThinking)
          );
          if (existingMessage) {
            // Keep ALL messages including thinking - don't filter anything
            const updatedMessage = {
              ...existingMessage,
              content: existingMessage.content + '\n\n' + messageData.data,
              contentChunks: [
                ...(existingMessage.contentChunks || []),
                {
                  section: messageData.section,
                  content: messageData.data,
                  citations: messageData.citations || [],
                  toolsUsed: messageData.toolsUsed || [],
                  timestamp: Date.now()
                }
              ],
              // Don't accumulate citations in the main message - only in chunks
              toolsUsed: Array.from(new Set([
                ...(existingMessage.toolsUsed || []),
                ...(messageData.toolsUsed || [])
              ])),
              isInitialThinking: false, // No longer just initial thinking
              streaming: true
            };
            return [...prev.filter(msg => msg !== existingMessage), updatedMessage];
          } else {
            // Create new message with first chunk (don't remove thinking)
            const newMessage = {
              role: 'assistant',
              content: messageData.data,
              contentChunks: [{
                section: messageData.section,
                content: messageData.data,
                citations: messageData.citations || [],
                toolsUsed: messageData.toolsUsed || [],
                timestamp: Date.now()
              }],
              citations: messageData.citations || [],
              toolsUsed: messageData.toolsUsed || [],
              created_at: new Date().toISOString(),
              streaming: true
            };
            return [...prev, newMessage];
          }
        } else if (messageData.type === 'final_answer') {
          // Find existing streaming message and append final summary
          const existingMessage = prev.find(msg => 
            msg.role === 'assistant' && !msg.isThinking && msg.streaming
          );
          if (existingMessage) {
            const updatedMessage = {
              ...existingMessage,
              content: existingMessage.content + '\n\n**Summary**\n\n' + messageData.response,
              streaming: true
            };
            return [...prev.filter(msg => msg !== existingMessage), updatedMessage];
          } else {
            // Create new message with final answer
            return [...prev, {
              role: 'assistant',
              content: messageData.response,
              created_at: new Date().toISOString(),
              streaming: true
            }];
          }
        } else if (messageData.type === 'simple_response') {
          // Handle simple responses (for simple queries)
          const existingMessage = prev.find(msg => 
            msg.role === 'assistant' && !msg.isThinking && msg.streaming
          );
          if (existingMessage) {
            const updatedMessage = {
              ...existingMessage,
              content: existingMessage.content + '\n\n' + messageData.data,
              streaming: true
            };
            return [...prev.filter(msg => msg !== existingMessage), updatedMessage];
          } else {
            return [...prev, {
              role: 'assistant',
              content: messageData.data,
              created_at: new Date().toISOString(),
              streaming: true
            }];
          }
        } else if (messageData.type === 'title_update') {
          // Update conversation ID from title update
          if (messageData.data.conversation_id) {
            setCurrentConversationId(messageData.data.conversation_id);
          }
          loadConversations();
          return prev; // Don't filter thinking for title updates
        } else if (messageData.type === 'message_id_update') {
          // Update the last assistant message with the real database ID
          return prev.map((msg, index) => {
            if (msg.role === 'assistant' && index === prev.length - 1 && (!msg.id || msg.id.toString().startsWith('temp'))) {
              return { ...msg, id: messageData.message_id };
            }
            return msg;
          });
        } else if (messageData.type === 'content') {
          // Handle regular content (not initial thinking)
          const newMessages = prev;
          if (messageData.data.metadata?.conversation_id && 
              currentConversationId && 
              currentConversationId.toString().startsWith('temp-')) {
            setCurrentConversationId(messageData.data.metadata.conversation_id);
          }
          
          // Check if there's an existing streaming message to append to
          const existingStreamingMessage = newMessages.find(msg => 
            msg.role === 'assistant' && msg.streaming
          );
          
          if (existingStreamingMessage) {
            // Append to existing streaming message
            const updatedMessage = {
              ...existingStreamingMessage,
              content: existingStreamingMessage.content + '\n\n' + messageData.data.content,
              citations: [
                ...(existingStreamingMessage.citations || []),
                ...(messageData.data.citations || [])
              ],
              toolsUsed: Array.from(new Set([
                ...(existingStreamingMessage.toolsUsed || []),
                ...(messageData.data.toolsUsed || [])
              ])),
              metadata: { ...existingStreamingMessage.metadata, ...messageData.data.metadata },
              isInitialThinking: false // No longer just initial thinking
            };
            return [...newMessages.filter(msg => msg !== existingStreamingMessage), updatedMessage];
          } else {
            // Create new message
            return [...newMessages, {
              role: 'assistant',
              content: messageData.data.content,
              citations: messageData.data.citations || [],
              toolsUsed: messageData.data.toolsUsed || [],
              metadata: messageData.data.metadata || {},
              created_at: new Date().toISOString(),
              streaming: true
            }];
          }
        } else if (messageData.type === 'done') {
          // Mark streaming as complete and remove any remaining thinking
          const newMessages = prev.filter(msg => msg.id !== 'thinking' && msg.id !== 'initial-thinking-indicator');
          return newMessages.map(msg => {
            if (msg.role === 'assistant' && msg.streaming) {
              return { 
                ...msg, 
                streaming: false,
                isInitialThinking: false // Final message is no longer just initial thinking
              };
            }
            return msg;
          });
        } else if (messageData.type === 'error') {
          const newMessages = prev.filter(msg => msg.id !== 'thinking');
          return [...newMessages, {
            role: 'assistant',
            content: `⚠️ ${messageData.data}`,
            created_at: new Date().toISOString()
          }];
        }
        
        return prev; // Default case - no changes
      });
    });
  };

  // Feedback handler for messages
  const handleFeedback = async (messageId, feedbackType) => {
    if (submitFeedback) {
      const success = await submitFeedback(messageId, feedbackType);
      if (success) {
        // Update local feedback state
        setFeedbackState(prev => ({
          ...prev,
          [messageId]: {
            type: feedbackType,
            created_at: new Date().toISOString()
          }
        }));
      }
      return success;
    }
    return false;
  };

  return (
    <div className="main-content">
      
      {/* Header */}
      <div className="main-header">
        <div className="header-left">
          <button className="sidebar-toggle" onClick={onToggleSidebar}>
            <i className="fas fa-bars"></i>
          </button>
          <h1 className="header-title">Market Research Assistant</h1>
        </div>
        <div className="header-controls">
          <button className="theme-toggle" onClick={onToggleTheme}>
            <i className={`fas ${theme === 'dark' ? 'fa-sun' : 'fa-moon'}`}></i>
          </button>
          <div className="user-menu" onClick={handleUserMenuClick}>
            <div className="user-avatar">
              {currentUser.charAt(0).toUpperCase()}
            </div>
            <span>{currentUser}</span>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="chat-container">
        {showWelcome ? (
          <WelcomeScreen onSelectTemplate={handleSendMessage} />
        ) : (
          <ChatContainer 
            messages={messages} 
            currentUser={currentUser} 
            onFeedback={handleFeedback} // pass feedback handler
            feedbackState={feedbackState} // pass feedback state
          />
        )}
      </div>

      {/* Input Area */}
      <InputArea 
        onSendMessage={handleSendMessage}
        isStreaming={isStreaming}
      />
    </div>
  );
};

export default MainContent;
