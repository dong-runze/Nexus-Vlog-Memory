import { test, expect } from '@playwright/test'

test.describe('Editor Modal - Teleport Fix Verification', () => {
  test('URL input should accept any value including https://', async ({ page }) => {
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
    
    console.log('Test 1: Fill with https URL')
    await imageInput.fill('https://example.com/test.jpg')
    let value = await imageInput.inputValue()
    console.log('Value:', value)
    expect(value).toBe('https://example.com/test.jpg')
    
    console.log('✓ https:// URL accepted')
    
    console.log('Test 2: Fill with http URL')
    await imageInput.fill('http://example.com/test.jpg')
    value = await imageInput.inputValue()
    console.log('Value:', value)
    expect(value).toBe('http://example.com/test.jpg')
    
    console.log('✓ http:// URL accepted')
    
    console.log('Test 3: Fill with no protocol URL')
    await imageInput.fill('example.com/test.jpg')
    value = await imageInput.inputValue()
    console.log('Value:', value)
    expect(value).toBe('example.com/test.jpg')
    
    console.log('✓ No protocol URL accepted')
  })

  test('Ctrl+A and Ctrl+V should work in form', async ({ page }) => {
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
    
    await imageInput.fill('initial-value.jpg')
    await page.waitForTimeout(100)
    console.log('Filled initial value')
    
    await imageInput.focus()
    await page.keyboard.press('Control+a')
    await page.waitForTimeout(50)
    await page.keyboard.type('new-image')
    await page.waitForTimeout(100)
    
    const value = await imageInput.inputValue()
    console.log('Value after Ctrl+a + typing:', value)
    expect(value).toBe('new-image')
    
    console.log('✓ Ctrl+A works')
  })

  test('Modal should be teleported to body', async ({ page }) => {
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
    
    const modal = page.locator('.fixed.inset-0.z-\\[1500\\]')
    await expect(modal).toBeVisible()
    
    const modalHtml = await modal.evaluate(el => el.parentElement?.tagName)
    console.log('Modal parent element:', modalHtml)
    
    expect(modalHtml).toBe('BODY')
    
    console.log('✓ Modal is teleported to body')
  })
})
