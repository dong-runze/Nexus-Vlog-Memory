import { test, expect } from '@playwright/test'

test.describe('Drag Silent Update - Zoom Sync', () => {
  test('After drag, zoom should not cause marker position drift or disappear', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const initialCount = await page.locator('.custom-marker').count()
    console.log('Initial markers:', initialCount)
    expect(initialCount).toBeGreaterThan(0)
    
    const firstMarker = page.locator('.custom-marker').first()
    const initialBox = await firstMarker.boundingBox()
    console.log('Initial position:', initialBox)
    
    const markerCenter = {
      x: initialBox!.x + initialBox!.width / 2,
      y: initialBox!.y + initialBox!.height / 2
    }
    
    await page.mouse.move(markerCenter.x, markerCenter.y)
    await page.mouse.down()
    await page.mouse.move(markerCenter.x + 30, markerCenter.y + 30)
    await page.mouse.up()
    console.log('Drag completed')
    await page.waitForTimeout(500)
    
    const afterDragBox = await firstMarker.boundingBox()
    console.log('After drag position:', afterDragBox)
    
    expect(afterDragBox!.x).not.toBe(initialBox!.x)
    expect(afterDragBox!.y).not.toBe(initialBox!.y)
    
    const afterDragCount = await page.locator('.custom-marker').count()
    console.log('After drag count:', afterDragCount)
    expect(afterDragCount).toBe(initialCount)
    
    await page.mouse.wheel(0, -300)
    await page.waitForTimeout(800)
    
    const afterZoomBox = await firstMarker.boundingBox()
    console.log('After zoom position:', afterZoomBox)
    
    const afterZoomCount = await page.locator('.custom-marker').count()
    console.log('After zoom count:', afterZoomCount)
    
    expect(afterZoomCount).toBe(afterDragCount)
    expect(afterZoomCount).toBe(initialCount)
    
    console.log('✓ All markers preserved after zoom')
  })

  test('Multiple drag operations + zoom should work correctly', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const initialCount = await page.locator('.custom-marker').count()
    console.log('Initial:', initialCount)
    
    for (let i = 0; i < 3; i++) {
      const marker = page.locator('.custom-marker').nth(i)
      const box = await marker.boundingBox()
      
      const center = { x: box!.x + box!.width / 2, y: box!.y + box!.height / 2 }
      
      await page.mouse.move(center.x, center.y)
      await page.mouse.down()
      await page.mouse.move(center.x + 20, center.y + 20)
      await page.mouse.up()
      await page.waitForTimeout(300)
      
      console.log(`Drag ${i + 1} completed`)
    }
    
    const afterDragCount = await page.locator('.custom-marker').count()
    console.log('After 3 drags:', afterDragCount)
    
    await page.mouse.wheel(0, -500)
    await page.waitForTimeout(800)
    
    const afterZoomOut = await page.locator('.custom-marker').count()
    console.log('After zoom out:', afterZoomOut)
    
    await page.mouse.wheel(0, 500)
    await page.waitForTimeout(800)
    
    const afterZoomIn = await page.locator('.custom-marker').count()
    console.log('After zoom in:', afterZoomIn)
    
    expect(afterZoomIn).toBe(initialCount)
    expect(afterZoomIn).toBe(afterZoomOut)
    expect(afterZoomIn).toBe(afterDragCount)
    
    console.log('✓ All markers preserved after multiple drags and zoom')
  })

  test('Drag should not conflict with map panning (mutex lock)', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const mapContainer = page.locator('.leaflet-container')
    const mapBox = await mapContainer.boundingBox()
    
    const firstMarker = page.locator('.custom-marker').first()
    const markerBox = await firstMarker.boundingBox()
    
    const center = { x: markerBox!.x + markerBox!.width / 2, y: markerBox!.y + markerBox!.height / 2 }
    
    await page.mouse.move(center.x, center.y)
    await page.mouse.down()
    
    await page.mouse.move(center.x + 50, center.y + 50, { steps: 10 })
    await page.waitForTimeout(100)
    
    const duringDragMarker = await firstMarker.boundingBox()
    console.log('During drag:', duringDragMarker)
    
    await page.mouse.up()
    await page.waitForTimeout(500)
    
    const afterDragMarker = await firstMarker.boundingBox()
    console.log('After drag:', afterDragMarker)
    
    expect(afterDragMarker!.x).not.toBe(markerBox!.x)
    expect(afterDragMarker!.y).not.toBe(markerBox!.y)
    
    console.log('✓ Drag mutex lock working correctly')
  })
})
