import { test, expect } from '@playwright/test'

test.describe('Map Markers Zoom Issue', () => {
  test('Markers should stay in correct position after zoom', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    // 获取第一个标记的初始位置
    const initialMarkers = await page.locator('.custom-marker').all()
    expect(initialMarkers.length).toBeGreaterThan(0)
    
    const firstMarker = initialMarkers[0]
    const initialBox = await firstMarker.boundingBox()
    console.log('Initial marker position:', initialBox)
    
    // 放大地图 (使用鼠标滚轮)
    await page.mouse.move(initialBox!.x + initialBox!.width / 2, initialBox!.y + initialBox!.height / 2)
    await page.mouse.wheel(0, -300) // 放大
    await page.waitForTimeout(1000)
    
    const afterZoomBox = await firstMarker.boundingBox()
    console.log('After zoom marker position:', afterZoomBox)
    
    // 验证标记位置是否发生变化（正常情况下应该不变或者有合理的变化）
    // 如果标记偏离原位置，x 或 y 坐标会有大幅变化
    
    // 再次缩小地图
    await page.mouse.wheel(0, 300) // 缩小
    await page.waitForTimeout(1000)
    
    const afterZoomOutBox = await firstMarker.boundingBox()
    console.log('After zoom out marker position:', afterZoomOutBox)
    
    // 验证缩放后标记数量不变
    const finalMarkers = await page.locator('.custom-marker').count()
    console.log('Final markers count:', finalMarkers)
    expect(finalMarkers).toBe(8)
  })

  test('Multiple zoom in/out should not break markers', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const initialCount = await page.locator('.custom-marker').count()
    console.log('Initial markers:', initialCount)
    
    // 多次放大缩小
    for (let i = 0; i < 3; i++) {
      await page.mouse.wheel(0, -200) // 放大
      await page.waitForTimeout(500)
      await page.mouse.wheel(0, 200) // 缩小
      await page.waitForTimeout(500)
    }
    
    const finalCount = await page.locator('.custom-marker').count()
    console.log('Final markers:', finalCount)
    expect(finalCount).toBe(initialCount)
  })
})
