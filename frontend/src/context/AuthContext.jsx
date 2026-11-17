import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const data = await api.getCurrentUser();
      setUser(data);
      return data;
    } catch (_) {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (username, password) => {
    const res = await api.login(username, password);
    await refreshUser();
    return res;
  };

  const register = async (username, email, password) => {
    const res = await api.register(username, email, password);
    await refreshUser();
    return res;
  };

  const demoLogin = async () => {
    const res = await api.demoLogin();
    await refreshUser();
    return res;
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (_) {}
    finally {
      setUser(null);
      try {
        localStorage.clear();
        sessionStorage.clear();
        document.cookie = 'deployeasy_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
        document.cookie = 'deployeasy_csrf=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
        document.cookie = 'deployeasy_mode=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
      } catch (_) {}
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, demoLogin, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
