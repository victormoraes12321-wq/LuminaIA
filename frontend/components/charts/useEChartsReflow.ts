import ReactECharts from 'echarts-for-react'
import { useRef, useEffect, useState } from 'react'

export function useEChartsReflow() {
  const chartRef = useRef<ReactECharts>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(600)
  const [height, setHeight] = useState(340)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let rafId: number
    const observer = new ResizeObserver((entries) => {
      if (!entries || entries.length === 0) return
      const { width: newWidth, height: newHeight } = entries[0].contentRect
      
      window.cancelAnimationFrame(rafId)
      rafId = window.requestAnimationFrame(() => {
        setWidth(newWidth || 600)
        setHeight(newHeight || 340)
        if (chartRef.current) {
          try {
            const instance = chartRef.current.getEchartsInstance()
            if (instance) {
              instance.resize()
            }
          } catch (_err) {
            // ECharts instance not ready yet
          }
        }
      })
    })

    observer.observe(container)
    return () => {
      observer.disconnect()
      window.cancelAnimationFrame(rafId)
    }
  }, [])

  return { chartRef, containerRef, width, height }
}
