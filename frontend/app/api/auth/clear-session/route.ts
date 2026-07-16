import { NextResponse } from 'next/server'

const AUTH_COOKIE_NAME = 'lumina-token'

export async function POST() {
  const response = NextResponse.json({ success: true })
  response.cookies.set(AUTH_COOKIE_NAME, '', {
    path: '/',
    maxAge: 0,
    httpOnly: true,
    sameSite: 'lax',
  })
  return response
}
