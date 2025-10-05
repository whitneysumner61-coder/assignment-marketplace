import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Assignment Marketplace',
  description: 'Two-sided marketplace for assignable purchase contracts',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
