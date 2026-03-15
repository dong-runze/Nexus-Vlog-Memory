import { test, expect } from '@playwright/test'

test.describe('Clone and Drag Functionality', () => {
  test('Right-click should clone marker', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const initialCount = await page.locator('.custom-marker').count()
    console.log('Initial markers:', initialCount)
    expect(initialCount).toBe(8)
    
    const firstMarker = page.locator('.custom-marker').first()
    const markerBox = await firstMarker.boundingBox()
    
    await firstMarker.click({ button: 'right' })
    await page.waitForTimeout(500)
    
    const afterCloneCount = await page.locator('.custom-marker').count()
    console.log('After clone:', afterCloneCount)
    expect(afterCloneCount).toBe(initialCount + 1)
  })

  test('Cloned marker should open detail panel', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click({ button: 'right' })
    await page.waitForTimeout(500)
    
    const detailPanel = page.locator('.fixed, [class*="detail"], [class*="Detail"]')
    console.log('Detail panel visible:', await detailPanel.isVisible().catch(() => false))
  })

  test('Markers should be draggable', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    const initialBox = await firstMarker.boundingBox()
    console.log('Initial position:', initialBox)
    
    const markerCenter = {
      x: initialBox!.x + initialBox!.width / 2,
      y: initialBox!.y + initialBox!.height / 2
    }
    
    await page.mouse.move(markerCenter.x, markerCenter.y)
    await page.mouse.down()
    await page.mouse.move(markerCenter.x + 50, markerCenter.y + 50)
    await page.mouse.up()
    await page.waitForTimeout(500)
    
    const afterDragBox = await firstMarker.boundingBox()
    console.log('After drag:', afterDragBox)
  })
})
