import React from 'react';

const Sidebar = ({ 
  collapsed, 
  conversations, 
  currentConversationId, 
  onNewChat, 
  onSelectConversation, 
  onDeleteConversation 
}) => {
  const formatTimeAgo = (date) => {
    const now = new Date();
    const diff = now - new Date(date);
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return 'Just now';
  };

  const handleDeleteConversation = async (conversationId, e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      await onDeleteConversation(conversationId);
    }
  };

  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo">
          <i className="fas fa-robot"></i>
          <span>Jedi Agent</span>
        </div>
      </div>
      
      <button className="new-chat-btn" onClick={onNewChat}>
        <i className="fas fa-plus"></i>
        New Chat
      </button>
      
      <div className="conversations-list">
        {conversations.map((conversation) => (
          <div
            key={conversation.id}
            className={`conversation-item ${currentConversationId === conversation.id ? 'active' : ''}`}
            onClick={() => onSelectConversation(conversation.id)}
          >
            <div className="conversation-title">
              {conversation.title || 'New Conversation'}
            </div>
            <div className="conversation-meta">
              {formatTimeAgo(conversation.updated_at)} • {conversation.message_count} messages
            </div>
            <button
              className="delete-conversation"
              onClick={(e) => handleDeleteConversation(conversation.id, e)}
            >
              <i className="fas fa-trash"></i>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Sidebar;
