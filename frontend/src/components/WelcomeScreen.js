import React from 'react';

const WelcomeScreen = ({ onSelectTemplate }) => {
  const templateQueries = [
    {
      title: "Consumer Behavior Analysis",
      query: "What are the latest consumer behavior trends for Gen Z in 2024?"
    },
    {
      title: "Social Media Impact",
      query: "How has social media influenced purchasing decisions across different demographics?"
    },
    {
      title: "Brand Loyalty Research",
      query: "What are the key factors driving brand loyalty in the food and beverage industry?"
    },
    {
      title: "Geographic Market Analysis",
      query: "Compare market research insights between Nashville and other major cities for retail preferences."
    }
  ];

  return (
    <div className="welcome-screen">
      <h1 className="welcome-title">Welcome to Jedi Agent</h1>
      <p className="welcome-subtitle">
        Your AI-powered market research assistant. Ask me anything about consumer behavior, 
        market trends, or get insights from our comprehensive research database.
      </p>
      
      <div className="template-queries">
        {templateQueries.map((template, index) => (
          <div
            key={index}
            className="template-query"
            onClick={() => onSelectTemplate(template.query)}
          >
            <div className="template-query-title">{template.title}</div>
            <div className="template-query-text">{template.query}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WelcomeScreen;
