import React, { useEffect, useRef, useState, useLayoutEffect } from 'react'
import { createPortal } from 'react-dom'

interface PortalOverlayProps {
  isOpen: boolean
  onClose: () => void
  triggerRef: React.RefObject<HTMLElement | null>
  children: React.ReactNode
  className?: string
  placement?: 'bottom-start' | 'bottom-end' | 'bottom-center'
  offsetY?: number
  maxWidth?: number
}

export const PortalOverlay: React.FC<PortalOverlayProps> = ({
  isOpen,
  onClose,
  triggerRef,
  children,
  className = '',
  placement = 'bottom-start',
  offsetY = 8,
  maxWidth,
}) => {
  const [mounted, setMounted] = useState(false)
  const [coords, setCoords] = useState<{ top: number; left: number; width?: number }>({ top: 0, left: 0 })
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setMounted(true)
  }, [])

  const updatePosition = () => {
    if (!triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    let top = rect.bottom + offsetY
    let left = rect.left

    const popoverWidth = overlayRef.current ? overlayRef.current.offsetWidth : (maxWidth || 340)
    const viewportWidth = window.innerWidth

    if (placement === 'bottom-end') {
      left = rect.right - popoverWidth
    } else if (placement === 'bottom-center') {
      left = rect.left + (rect.width - popoverWidth) / 2
    }

    // Viewport boundary guard
    if (left + popoverWidth > viewportWidth - 16) {
      left = Math.max(16, viewportWidth - popoverWidth - 16)
    }
    if (left < 16) {
      left = 16
    }

    setCoords({ top, left, width: rect.width })
  }

  useLayoutEffect(() => {
    if (isOpen) {
      updatePosition()
    }
  }, [isOpen, placement, offsetY])

  useEffect(() => {
    if (!isOpen) return

    const handleScrollOrResize = () => {
      updatePosition()
    }

    const handleClickOutside = (e: MouseEvent) => {
      if (
        overlayRef.current &&
        !overlayRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        onClose()
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('scroll', handleScrollOrResize, true)
    window.addEventListener('resize', handleScrollOrResize)
    document.addEventListener('mousedown', handleClickOutside, true)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('scroll', handleScrollOrResize, true)
      window.removeEventListener('resize', handleScrollOrResize)
      document.removeEventListener('mousedown', handleClickOutside, true)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!mounted || !isOpen) return null

  return createPortal(
    <div
      ref={overlayRef}
      role="dialog"
      aria-modal="false"
      data-testid="portal-overlay-root"
      style={{
        position: 'fixed',
        top: `${coords.top}px`,
        left: `${coords.left}px`,
        zIndex: 99999,
        maxWidth: maxWidth ? `${maxWidth}px` : undefined,
      }}
      className={`lumina-portal-overlay animate-in fade-in zoom-in-95 duration-150 ${className}`}
    >
      {children}
    </div>,
    document.body
  )
}
