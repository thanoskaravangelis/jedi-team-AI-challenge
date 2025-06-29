import { useState, useEffect, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const useJediAgent = () => {
  const [currentUser, setCurrentUser] = useState(null);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Load user from localStorage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('jedi_agent_user');
    if (savedUser) {
      setCurrentUser(savedUser);
    }
  }, []);

  const loadConversations = useCallback(async () => {
    if (!currentUser) return;
    
    try {
      const response = await fetch(`${API_BASE}/conversations/${currentUser}`);
      if (response.ok) {
        const data = await response.json();
        setConversations(data);
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  }, [currentUser]);

  // Load conversations when user changes
  useEffect(() => {
    if (currentUser) {
      loadConversations();
    }
  }, [currentUser, loadConversations]);

  const login = useCallback((userId) => {
    setCurrentUser(userId);
    localStorage.setItem('jedi_agent_user', userId);
    // Force conversations reload after login
    setTimeout(() => {
      loadConversations();
    }, 100);
  }, [loadConversations]);

  const logout = useCallback(() => {
    localStorage.removeItem('jedi_agent_user');
    setCurrentUser(null);
    setCurrentConversationId(null);
    setConversations([]);
  }, []);

  const loadConversationMessages = useCallback(async (conversationId) => {
    // Prevent fetching messages for temp conversation IDs
    if (typeof conversationId === 'string' && conversationId.startsWith('temp-')) {
      return [];
    }
    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}/messages`);
      if (response.ok) {
        const messages = await response.json();
        // Transform messages to match the streaming format, filter out null/undefined
        return (messages || []).filter(Boolean).map(message => {
          const safeContent =
            (message && (
              message.content ||
              message.message ||
              message.data ||
              message.text
            )) || '';
          return {
            id: message.id, // ensure id is preserved
            role: message.role || 'assistant',
            content: typeof safeContent === 'string' ? safeContent : '',
            created_at: message.created_at || new Date().toISOString(),
            citations: message.citations || [],
            toolsUsed: message.tools_used || [],
            metadata: message.metadata || {},
            isThinking: message.isThinking || false,
            contentChunks: message.contentChunks || undefined,
            tool: message.tool || undefined,
            // add any other fields you use in the UI
          };
        });
      }
    } catch (error) {
      console.error('Error loading conversation messages:', error);
    }
    return [];
  }, []);

  const deleteConversation = useCallback(async (conversationId) => {
    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        setConversations(prev => prev.filter(c => c.id !== conversationId));
        if (currentConversationId === conversationId) {
          setCurrentConversationId(null);
        }
        return true;
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
    return false;
  }, [currentConversationId]);

  const streamQuery = useCallback(async (query, onMessage) => {
    if (!currentUser) return;

    // Use current conversation ID, but filter out temp IDs when sending to backend
    let conversationIdToSend = currentConversationId;
    if (conversationIdToSend && typeof conversationIdToSend === 'number') {
      conversationIdToSend = conversationIdToSend.toString();
    }
    if (conversationIdToSend && typeof conversationIdToSend === 'string' && conversationIdToSend.startsWith('temp-')) {
      conversationIdToSend = null; // Let backend create new conversation
    }

    setIsStreaming(true);
    
    try {
      const requestBody = {
        query: query,
        user_id: currentUser,
        conversation_id: conversationIdToSend
      };

      const response = await fetch(`${API_BASE}/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Stream response error:', response.status, errorText);
        throw new Error(`HTTP error! status: ${response.status}, details: ${errorText}`);
      }

      const reader = response.body.getReader();
      let citations = [];
      let toolsUsed = [];

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = new TextDecoder().decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'thinking') {
                  onMessage({ type: 'thinking', data: data.data, tool: data.tool || 'system' });
                } else if (data.type === 'content_chunk') {
                  // Handle streaming content chunks
                  onMessage({ 
                    type: 'content_chunk', 
                    section: data.section,
                    data: data.data,
                    citations: data.citations || [],
                    toolsUsed: data.tools_used || []
                  });
                } else if (data.type === 'title_update') {
                  // Update conversation title and set conversation ID
                  setCurrentConversationId(data.conversation_id);
                  onMessage({ type: 'title_update', data: data });
                  await loadConversations();
                } else if (data.type === 'conversation_update') {
                  // Update conversation ID from backend
                  console.log('🔄 Conversation update:', data.conversation_id);
                  setCurrentConversationId(data.conversation_id);
                  await loadConversations();
                } else if (data.type === 'message_id_update') {
                  // Update the last assistant message with the real database ID
                  onMessage({ type: 'message_id_update', message_id: data.message_id });
                } else if (data.type === 'content') {
                  citations = data.citations || [];
                  toolsUsed = data.tools_used || [];
                  // Only update conversation ID if it was a temp ID
                  if (currentConversationId && currentConversationId.toString().startsWith('temp-') && data.metadata?.conversation_id) {
                    setCurrentConversationId(data.metadata.conversation_id);
                    // Do NOT reload conversations or messages here to avoid UI disruption
                  }
                  onMessage({ 
                    type: 'content', 
                    data: {
                      content: data.data,
                      citations: citations,
                      toolsUsed: toolsUsed,
                      metadata: data.metadata
                    }
                  });
                } else if (data.type === 'done') {
                  // Stream complete
                  onMessage({ type: 'done' });
                } else if (data.type === 'error') {
                  onMessage({ type: 'error', data: data.message });
                } else if (data.type === 'simple_response') {
                  // Handle simple response type
                  onMessage({ 
                    type: 'content', 
                    data: {
                      content: data.data,
                      citations: [],
                      toolsUsed: [],
                      metadata: data.metadata || {}
                    }
                  });
                }
              } catch (parseError) {
                console.warn('Failed to parse SSE data:', parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      console.error('Error streaming query:', error);
      onMessage({ type: 'error', data: 'Sorry, there was an error processing your request. Please try again.' });
    } finally {
      setIsStreaming(false);
    }
  }, [currentUser, currentConversationId, loadConversations]);

  // Add feedback (like/dislike) functionality
  const submitFeedback = useCallback(async (messageId, feedbackType, comment = null) => {
    try {
      const response = await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: messageId,
          feedback_type: feedbackType, // 'thumbs_up' or 'thumbs_down'
          comment: comment
        })
      });
      if (response.ok) {
        const result = await response.json();
        console.log('Feedback submitted:', result);
        return true;
      } else {
        const errorText = await response.text();
        console.error('Error submitting feedback:', response.status, errorText);
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
    return false;
  }, []);

  return {
    currentUser,
    conversations,
    currentConversationId,
    setCurrentConversationId,
    isStreaming,
    login,
    logout,
    loadConversations,
    loadConversationMessages,
    deleteConversation,
    streamQuery,
    submitFeedback
  };
};
