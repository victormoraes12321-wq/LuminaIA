import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { ThemeProvider } from '@/context/ThemeContext'
import { AuthProvider } from '@/context/AuthContext'
import '@/styles/globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

// ── SEO Metadata ───────────────────────────────────────────────

export const metadata: Metadata = {
  title: {
    default: 'LuminaAI — Business Intelligence Inteligente',
    template: '%s | LuminaAI',
  },
  description:
    'Plataforma corporativa de Business Intelligence com Motor de Intenção baseado em IA. ' +
    'Consulte seus dados em linguagem natural e obtenha visualizações automáticas.',
  keywords: ['Business Intelligence', 'BI', 'Inteligência Artificial', 'Dashboard', 'Analytics'],
  authors: [{ name: 'LuminaAI Engineering' }],
  robots: 'noindex, nofollow',
  icons: {
    icon: '/favicon.ico',
  },
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: dark)',  color: '#09090b' },
    { media: '(prefers-color-scheme: light)', color: '#f8fafc' },
  ],
  width: 'device-width',
  initialScale: 1,
}

// ── Root Layout ────────────────────────────────────────────────

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR" data-theme="dark" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} antialiased`} suppressHydrationWarning>
        <AuthProvider>
          <ThemeProvider>
            {children}
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
