import React, { useState, useEffect } from 'react';
import './styles/App.css';
import './styles/Fixes.css';
import './styles/Citations.css';
import './styles/ThinkingComponent.css';
import { useJediAgent } from './hooks/useJediAgent';
import LoginModal from './components/LoginModal';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';

function App() {
  const [theme, setTheme] = useState('light');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const jediAgent = useJediAgent();

  // Load theme from localStorage on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('jedi_agent_theme') || 'light';
    setTheme(savedTheme);
    document.body.dataset.theme = savedTheme;
    setIsLoading(false);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('jedi_agent_theme', newTheme);
    document.body.dataset.theme = newTheme;
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // Show loading screen while checking auth state
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        backgroundColor: 'var(--bg-primary)',
        color: 'var(--text-primary)'
      }}>
        <div>Loading...</div>
      </div>
    );
  }

  if (!jediAgent.currentUser) {
    return <LoginModal onLogin={jediAgent.login} />;
  }

  return (
    <div className="app-container">
      <Sidebar
        collapsed={sidebarCollapsed}
        conversations={jediAgent.conversations}
        currentConversationId={jediAgent.currentConversationId}
        onNewChat={() => jediAgent.setCurrentConversationId(null)}
        onSelectConversation={jediAgent.setCurrentConversationId}
        onDeleteConversation={jediAgent.deleteConversation}
      />
      
      <MainContent
        theme={theme}
        onToggleTheme={toggleTheme}
        onToggleSidebar={toggleSidebar}
        currentUser={jediAgent.currentUser}
        currentConversationId={jediAgent.currentConversationId}
        isStreaming={jediAgent.isStreaming}
        onLogout={jediAgent.logout}
        onStreamQuery={jediAgent.streamQuery}
        loadConversationMessages={jediAgent.loadConversationMessages}
        loadConversations={jediAgent.loadConversations}
        setCurrentConversationId={jediAgent.setCurrentConversationId}
        submitFeedback={jediAgent.submitFeedback} // pass feedback function
      />
    </div>
  );
}

export default App;
