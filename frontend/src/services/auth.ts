import { halClient } from './hal'
import type {
  LoginRequest,
  LoginResponse,
  RefreshTokenRequest,
  RefreshTokenResponse,
  User
} from '@/types'

export class AuthService {
  private readonly ACCESS_TOKEN_KEY = 'accessToken'
  private readonly REFRESH_TOKEN_KEY = 'refreshToken'
  private readonly USER_KEY = 'user'

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await halClient.post<LoginResponse>('/auth/login', credentials as unknown as Record<string, unknown>)
    
    // Store tokens and user data
    this.setTokens(response.accessToken as string, response.refreshToken as string)
    this.setUser(response.user as User)
    
    return response as LoginResponse
  }

  async logout(): Promise<void> {
    try {
      // Call logout endpoint to invalidate tokens on server
      await halClient.post('/auth/logout')
    } catch (error) {
      // Continue with local logout even if server call fails
      console.warn('Server logout failed:', error)
    } finally {
      // Always clear local storage
      this.clearTokens()
      this.clearUser()
    }
  }

  async refreshToken(): Promise<RefreshTokenResponse | null> {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) {
      return null
    }

    try {
      const request: RefreshTokenRequest = { refreshToken }
      const response = await halClient.post<RefreshTokenResponse>('/auth/refresh', request as unknown as Record<string, unknown>)
      
      // Update stored tokens
      this.setTokens(response.accessToken as string, response.refreshToken as string)
      
      return response as RefreshTokenResponse
    } catch (error) {
      // Refresh failed - clear tokens and force re-login
      this.clearTokens()
      this.clearUser()
      throw error
    }
  }

  async getCurrentUser(): Promise<User | null> {
    const storedUser = this.getStoredUser()
    if (storedUser) {
      return storedUser
    }

    // If no stored user but we have a token, fetch from server
    if (this.getAccessToken()) {
      try {
        const response = await halClient.get<User>('/auth/me')
        this.setUser(response as unknown as User)
        return response as unknown as User
      } catch (error) {
        // Token might be invalid
        this.clearTokens()
        this.clearUser()
        return null
      }
    }

    return null
  }

  // Token management
  getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_TOKEN_KEY)
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY)
  }

  setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken)
  }

  clearTokens(): void {
    localStorage.removeItem(this.ACCESS_TOKEN_KEY)
    localStorage.removeItem(this.REFRESH_TOKEN_KEY)
  }

  // User data management
  getStoredUser(): User | null {
    const userData = localStorage.getItem(this.USER_KEY)
    return userData ? JSON.parse(userData) : null
  }

  setUser(user: User): void {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user))
  }

  clearUser(): void {
    localStorage.removeItem(this.USER_KEY)
  }

  // Token validation
  isTokenExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const currentTime = Math.floor(Date.now() / 1000)
      return payload.exp < currentTime
    } catch (error) {
      return true
    }
  }

  isAuthenticated(): boolean {
    const token = this.getAccessToken()
    return token !== null && !this.isTokenExpired(token)
  }

  // Auto-refresh token logic
  async ensureValidToken(): Promise<boolean> {
    const accessToken = this.getAccessToken()
    
    if (!accessToken) {
      return false
    }

    // If token is expired, try to refresh
    if (this.isTokenExpired(accessToken)) {
      try {
        await this.refreshToken()
        return true
      } catch (error) {
        return false
      }
    }

    return true
  }

  // Setup automatic token refresh
  setupTokenRefresh(): void {
    const checkInterval = 5 * 60 * 1000 // Check every 5 minutes

    setInterval(async () => {
      const accessToken = this.getAccessToken()
      if (!accessToken) {
        return
      }

      try {
        const payload = JSON.parse(atob(accessToken.split('.')[1]))
        const currentTime = Math.floor(Date.now() / 1000)
        const timeUntilExpiry = payload.exp - currentTime

        // Refresh if token expires in the next 10 minutes
        if (timeUntilExpiry < 10 * 60) {
          await this.refreshToken()
        }
      } catch (error) {
        console.warn('Token refresh check failed:', error)
      }
    }, checkInterval)
  }
}

// Create singleton instance
export const authService = new AuthService()