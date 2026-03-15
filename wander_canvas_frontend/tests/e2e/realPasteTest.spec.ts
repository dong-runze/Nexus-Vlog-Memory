import { test, expect } from '@playwright/test'

test.describe('Real Paste Events Testing', () => {
  test('Test actual paste event with http URL', async ({ page }) => {
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
    
    await page.evaluate(() => {
      const input = document.querySelector('input[type="text"]') as HTMLInputElement
      const clipboardData = new DataTransfer()
      clipboardData.setData('text/plain', 'https://example.com/test.jpg')
      const pasteEvent = new ClipboardEvent('paste', {
        bubbles: true,
        cancelable: true,
        clipboardData: clipboardData
      })
      input.dispatchEvent(pasteEvent)
    })
    
    await page.waitForTimeout(200)
    
    const value = await imageInput.inputValue()
    console.log('Value after paste event:', value)
    
    expect(value).toContain('https://')
  })

  test('Test keyboard Ctrl+V paste', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(2000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(500)
    
    const editButton = page.locator('button:has-text("Edit")')
    await editButton.click()
    await page.waitForTimeout(500)
    
    await page.evaluate(() => {
      navigator.clipboard.writeText('https://test-image.com/photo.png')
    })
    
    const imageInput = page.locator('input[type="text"]').first()
    await imageInput.focus()
    
    await page.keyboard.press('Control+v')
    await page.waitForTimeout(200)
    
    const value = await imageInput.inputValue()
    console.log('Value after Ctrl+V:', value)
    
    expect(value).toContain('https://')
  })

  test('Test right-click paste simulation', async ({ page }) => {
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
    
    await page.evaluate(() => {
      navigator.clipboard.writeText('http://example.com/image.jpg')
    })
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2, { button: 'right' })
      await page.waitForTimeout(300)
      
      const pasteMenuItem = page.locator('li:has-text("粘贴"), li:has-text("Paste")').first()
      if (await pasteMenuItem.isVisible({ timeout: 1000 }).catch(() => false)) {
        await pasteMenuItem.click()
        await page.waitForTimeout(200)
        
        const value = await imageInput.inputValue()
        console.log('Value after right-click paste:', value)
      } else {
        console.log('Paste menu not found, trying direct input')
        await page.keyboard.press('Control+v')
        await page.waitForTimeout(200)
        const value = await imageInput.inputValue()
        console.log('Value after Ctrl+V fallback:', value)
      }
    }
  })
})
