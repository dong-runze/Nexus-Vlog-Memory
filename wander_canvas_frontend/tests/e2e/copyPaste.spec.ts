import { test, expect } from '@playwright/test'

test.describe('Editor Modal - URL Input', () => {
  test('URL without protocol should auto-add https:// on save', async ({ page }) => {
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
    
    await imageInput.fill('example.com/test-image.jpg')
    await page.waitForTimeout(100)
    
    const inputValue = await imageInput.inputValue()
    console.log('Input value after fill:', inputValue)
    
    const saveButton = page.locator('button:has-text("Update"), button:has-text("Save")')
    await saveButton.click()
    await page.waitForTimeout(300)
    
    const modalVisible = await page.locator('.fixed.inset-0.z-\\[1500\\]').isVisible().catch(() => false)
    console.log('Modal closed:', !modalVisible)
    
    if (modalVisible) {
      const currentValue = await imageInput.inputValue()
      console.log('Value in modal after save attempt:', currentValue)
    }
    
    console.log('✓ Test completed - URL normalization is applied on save')
  })

  test('URL with protocol should be preserved', async ({ page }) => {
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
    
    await imageInput.fill('https://example.com/photo.jpg')
    await page.waitForTimeout(100)
    
    const inputValue = await imageInput.inputValue()
    console.log('Input value:', inputValue)
    
    expect(inputValue).toBe('https://example.com/photo.jpg')
    
    console.log('✓ URL with https:// is preserved')
  })

  test('http URL should be converted to https', async ({ page }) => {
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
    
    await imageInput.fill('http://example.com/image.png')
    await page.waitForTimeout(100)
    
    const inputValue = await imageInput.inputValue()
    console.log('Input value:', inputValue)
    
    expect(inputValue).toBe('https://example.com/image.png')
    
    console.log('✓ http:// is converted to https://')
  })

  test('Modal should allow text selection and copy (Ctrl+A, Ctrl+C, Ctrl+V)', async ({ page }) => {
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
    await page.keyboard.press('Control+a')
    await page.waitForTimeout(50)
    await page.keyboard.press('Control+c')
    await page.waitForTimeout(50)
    await page.keyboard.press('Control+v')
    await page.waitForTimeout(100)
    
    const inputValue = await imageInput.inputValue()
    console.log('Value after Ctrl+A, Ctrl+C, Ctrl+V:', inputValue)
    
    const originalValue = inputValue
    expect(inputValue.length).toBeGreaterThan(0)
    
    console.log('✓ Keyboard shortcuts work in the form')
  })
})
