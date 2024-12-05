import React, { useState } from 'react';
import styles from '../styles/LoginForm.module.css';
import { userInfo } from 'os';
// API service
import { login } from './../api/ApiService';
// Security service
import { hashPassword } from '../api/security/securityService';

interface LoginFormProps {
  onLogin: (username: string, token: string, role: string, site: string) => void;  
}

const LoginForm: React.FC<LoginFormProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('');
  const [site, setSite] = useState('');
  const [token, setToken] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Check if is an email
      const isEmail = username.includes('@'); // Determina se l'input è un'email
      // Call the login API
      // Pass the username, isEmail and hashed password
      const loginResponse = await login(username, isEmail, await hashPassword(password));
      // If the login is successful, call the onLogin function
      if (loginResponse.outcome) {
        if(loginResponse.userInfo != null){
          if (loginResponse.userInfo.username && loginResponse.userInfo.access_token && 
              loginResponse.userInfo.role && loginResponse.userInfo.site) {
                // Call the onLogin function
                // Pass the user information to the parent component
                onLogin(loginResponse.userInfo.username,      // Username
                        loginResponse.userInfo.access_token,  // Token
                        loginResponse.userInfo.role,          // Role
                        loginResponse.userInfo.site);         // Site
          } else {
            setError('User information is incomplete.');
          }
        }
      } else {
        setError('Invalid credentials');
      }
    } catch (err) {
      setError('Error during login. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.loginContainer}>
      <form onSubmit={handleSubmit} className={styles.loginForm}>
        <h2 className={styles.title}>Login</h2>
        {error && <div className={styles.errorMessage}>{error}</div>}
        <div className={styles.inputGroup}>
          <label>Username:</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className={styles.input}
          />
        </div>
        <div className={styles.inputGroup}>
          <label>Password:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={styles.input}
          />
        </div>
        <button type="submit" className={styles.loginButton} disabled={loading}>
          {loading ? 'Loading...' : 'Login'}
        </button>
      </form>
    </div>
  );
};

export default LoginForm;
