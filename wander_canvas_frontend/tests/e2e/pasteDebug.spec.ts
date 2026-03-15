import { test, expect } from '@playwright/test'

test.describe('Editor Modal - Paste URL Debug', () => {
  test('Debug: can paste https URL after clearing input', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(500)
    
    const editButton = page.locator('button:has-text("Edit")')
    if (await editButton.isVisible()) {
      await editButton.click()
    } else {
      await page.keyboard.press('Enter')
    }
    await page.waitForTimeout(500)
    
    const imageInput = page.locator('input[type="text"]').first()
    await expect(imageInput).toBeVisible()
    
    const placeholder = await imageInput.getAttribute('placeholder')
    console.log('Placeholder:', placeholder)
    
    await imageInput.click()
    await page.waitForTimeout(100)
    
    const initialValue = await imageInput.inputValue()
    console.log('Initial value:', initialValue)
    
    console.log('Testing: Fill with https URL...')
    await imageInput.fill('https://example.com/test.jpg')
    await page.waitForTimeout(200)
    
    const afterFill = await imageInput.inputValue()
    console.log('After fill:', afterFill)
    
    expect(afterFill).toBe('https://example.com/test.jpg')
    console.log('✓ Fill works!')
  })

  test('Debug: paste after Ctrl+A', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(500)
    
    const editButton = page.locator('button:has-text("Edit")')
    if (await editButton.isVisible()) {
      await editButton.click()
    } else {
      await page.keyboard.press('Enter')
    }
    await page.waitForTimeout(500)
    
    const imageInput = page.locator('input[type="text"]').first()
    await expect(imageInput).toBeVisible()
    
    await imageInput.fill('existing-image-url.jpg')
    await page.waitForTimeout(100)
    console.log('Filled initial value')
    
    await imageInput.focus()
    await page.waitForTimeout(50)
    
    await page.keyboard.press('Control+a')
    await page.waitForTimeout(50)
    console.log('Pressed Ctrl+A')
    
    await page.keyboard.press('Control+v')
    await page.waitForTimeout(100)
    console.log('Pressed Ctrl+V')
    
    const value = await imageInput.inputValue()
    console.log('Value after Ctrl+A + Ctrl+V:', value)
    
    console.log('✓ Test completed')
  })

  test('Debug: paste after Backspace', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(500)
    
    const editButton = page.locator('button:has-text("Edit")')
    if (await editButton.isVisible()) {
      await editButton.click()
    } else {
      await page.keyboard.press('Enter')
    }
    await page.waitForTimeout(500)
    
    const imageInput = page.locator('input[type="text"]').first()
    await expect(imageInput).toBeVisible()
    
    await imageInput.fill('old-value.jpg')
    await page.waitForTimeout(100)
    console.log('Filled initial value')
    
    await imageInput.focus()
    await page.waitForTimeout(50)
    
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press('Backspace')
    }
    await page.waitForTimeout(50)
    console.log('Pressed Backspace multiple times')
    
    await page.keyboard.press('Control+v')
    await page.waitForTimeout(100)
    console.log('Pressed Ctrl+V')
    
    const value = await imageInput.inputValue()
    console.log('Value after Backspace + Ctrl+V:', value)
    
    console.log('✓ Test completed')
  })

  test('Debug: direct keyboard typing of https URL', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(500)
    
    const editButton = page.locator('button:has-text("Edit")')
    if (await editButton.isVisible()) {
      await editButton.click()
    } else {
      await page.keyboard.press('Enter')
    }
    await page.waitForTimeout(500)
    
    const imageInput = page.locator('input[type="text"]').first()
    await expect(imageInput).toBeVisible()
    
    await imageInput.focus()
    await page.waitForTimeout(50)
    
    await page.keyboard.type('https://example.com/image.png', { delay: 50 })
    await page.waitForTimeout(200)
    
    const value = await imageInput.inputValue()
    console.log('Value after typing:', value)
    
    expect(value).toBe('https://example.com/image.png')
    console.log('✓ Typing works!')
  })
})
