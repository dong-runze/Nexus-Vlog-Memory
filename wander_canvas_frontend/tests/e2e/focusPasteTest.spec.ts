import { test, expect } from '@playwright/test'

test.describe('Focus then Paste Testing', () => {
  test('Focus input then paste', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(500)
    
    const editButton = page.locator('button:has-text("Edit")')
    await editButton.click()
    await page.waitForTimeout(500)
    
    const imageInput = page.locator('input[type="text"]').first()
    
    await imageInput.focus()
    await page.waitForTimeout(100)
    
    const isFocused = await imageInput.evaluate(el => el === document.activeElement)
    console.log('Input is focused:', isFocused)
    
    await page.keyboard.type('https://test-image.com/photo.png')
    await page.waitForTimeout(200)
    
    const value = await imageInput.inputValue()
    console.log('Value after typing:', value)
    
    expect(value).toContain('https://')
  })

  test('Click to focus then paste with http', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(500)
    
    const editButton = page.locator('button:has-text("Edit")')
    await editButton.click()
    await page.waitForTimeout(500)
    
    const imageInput = page.locator('input[type="text"]').first()
    const box = await imageInput.boundingBox()
    
    if (box) {
      await page.mouse.click(box.x + 5, box.y + box.height / 2)
      await page.waitForTimeout(100)
    }
    
    await page.keyboard.type('http://example.com/image.jpg')
    await page.waitForTimeout(200)
    
    const value = await imageInput.inputValue()
    console.log('Value after click + type:', value)
    
    expect(value).toContain('http://')
  })
})
