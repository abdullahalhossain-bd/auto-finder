import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../lib/api'

interface AuthContextType {
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, orgName: string, tosAccepted: boolean) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    setIsAuthenticated(!!token)
    setLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    const data = await api.login(email, password)
    localStorage.setItem('access_token', data.access_token)
    setIsAuthenticated(true)
  }

  const register = async (
    email: string,
    password: string,
    orgName: string,
    tosAccepted: boolean,
  ) => {
    if (!tosAccepted) {
      throw new Error('You must accept the Terms of Service')
    }
    const data = await api.register(email, password, orgName, tosAccepted)
    localStorage.setItem('access_token', data.access_token)
    setIsAuthenticated(true)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    setIsAuthenticated(false)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
