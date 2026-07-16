import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// â”€â”€ JWT Decode Helper (Edge Runtime Compatible) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface JwtPayload {
  sub: string
  tenant_id: string
  role: 'ADMIN' | 'GESTOR' | 'CONSULTA'
  must_change_password: boolean
  exp: number
}

function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payloadBase64 = parts[1]
    
    // Converte de Base64Url para Base64 padrão
    const base64 = payloadBase64.replace(/-/g, '+').replace(/_/g, '/')
    
    // Decodifica usando atob nativa (disponível no Edge Runtime)
    const jsonStr = atob(base64)
    return JSON.parse(jsonStr)
  } catch (_err) {
    return null
  }
}

// â”€â”€ Middleware Core Logic â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  
  // 1. Obtém o token do cookie
  const tokenCookie = request.cookies.get('lumina-token')
  const token = tokenCookie?.value
  
  // 2. Decodifica e valida o payload
  let payload: JwtPayload | null = null
  let isTokenValid = false
  
  if (token) {
    payload = decodeJwtPayload(token)
    if (payload && payload.exp * 1000 > Date.now()) {
      isTokenValid = true
    }
  }

  // 3. Gerencia as rotas com base no estado do token
  
  // A. Rotas de Dashboard (/dashboard)
  if (pathname.startsWith('/dashboard')) {
    if (!isTokenValid) {
      // Sem token válido -> Login
      const loginUrl = new URL('/login', request.url)
      return NextResponse.redirect(loginUrl)
    }
    
    if (payload?.must_change_password) {
      // Token válido mas precisa trocar a senha -> Primeiro Acesso
      const firstAccessUrl = new URL('/auth/first-access', request.url)
      return NextResponse.redirect(firstAccessUrl)
    }
  }
  
  // B. Rota de Primeiro Acesso (/auth/first-access)
  if (pathname === '/auth/first-access') {
    if (!isTokenValid) {
      // Tentou entrar no reset sem estar autenticado -> Login
      const loginUrl = new URL('/login', request.url)
      return NextResponse.redirect(loginUrl)
    }
    
    if (payload && !payload.must_change_password) {
      // Usuário já redefiniu a senha -> Dashboard
      const dashboardUrl = new URL('/dashboard', request.url)
      return NextResponse.redirect(dashboardUrl)
    }
  }
  
  // C. Rota de Login (/login)
  if (pathname === '/login') {
    if (isTokenValid) {
      if (payload?.must_change_password) {
        // Logado mas precisa redefinir -> Primeiro Acesso
        const firstAccessUrl = new URL('/auth/first-access', request.url)
        return NextResponse.redirect(firstAccessUrl)
      } else {
        // Logado e senha em ordem -> Dashboard
        const dashboardUrl = new URL('/dashboard', request.url)
        return NextResponse.redirect(dashboardUrl)
      }
    }
  }
  
  // Para qualquer outra rota ou se atender aos requisitos, deixa prosseguir
  return NextResponse.next()
}

// Configura em quais caminhos o middleware será executado
export const config = {
  matcher: [
    '/dashboard/:path*',
    '/auth/first-access',
    '/login'
  ]
}

