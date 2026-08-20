import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    service: 'luminaai-frontend',
    checked_at: new Date().toISOString(),
  })
}
