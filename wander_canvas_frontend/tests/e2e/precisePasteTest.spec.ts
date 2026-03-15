import { test, expect } from '@playwright/test'

test.describe('Precise Paste Flow Testing', () => {
  test('Click directly on input then type URL', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(500)
    
    const editButton = page.locator('button:has-text("Edit")')
    await editButton.click()
    await page.waitForTimeout(500)
    
    const imageInput = page.locator('input').nth(2)
    
    const box = await imageInput.boundingBox()
    console.log('Input box:', box)
    
    if (box) {
      await page.mouse.click(box.x + 10, box.y + box.height / 2)
      await page.waitForTimeout(100)
    }
    
    await page.keyboard.insertText('https://example.com/new-image.jpg')
    await page.waitForTimeout(200)
    
    const value = await imageInput.inputValue()
    console.log('Input value:', value)
    
    expect(value).toBe('https://example.com/new-image.jpg')
  })

  test('Double click to select then type', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(500)
    
    const editButton = page.locator('button:has-text("Edit")')
    await editButton.click()
    await page.waitForTimeout(500)
    
    const imageInput = page.locator('input').nth(2)
    
    await imageInput.dblclick()
    await page.waitForTimeout(100)
    
    await page.keyboard.press('Backspace')
    await page.waitForTimeout(100)
    
    await page.keyboard.type('http://test.com/image.png')
    await page.waitForTimeout(200)
    
    const value = await imageInput.inputValue()
    console.log('Value after dblclick + type:', value)
  })
})
