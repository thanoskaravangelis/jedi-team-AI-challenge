import React, { useState } from 'react';

const LoginModal = ({ onLogin }) => {
  const [userId, setUserId] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmedUserId = userId.trim();
    if (trimmedUserId) {
      onLogin(trimmedUserId);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2 className="modal-title">Welcome to Jedi Agent</h2>
        <p className="modal-subtitle">Enter your user ID to get started</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="userId" className="form-label">User ID</label>
            <input
              type="text"
              id="userId"
              className="form-input"
              placeholder="Enter your user ID (can be random)"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn-primary">Sign In</button>
        </form>
      </div>
    </div>
  );
};

export default LoginModal;
