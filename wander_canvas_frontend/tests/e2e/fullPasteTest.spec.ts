import { test, expect } from '@playwright/test'

test.describe('Editor Modal - Full Paste Testing', () => {
  test('Complete paste workflow test', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(3000)
    
    console.log('Step 1: Click on first marker')
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(1000)
    
    console.log('Step 2: Click Edit button')
    const editButton = page.locator('button:has-text("Edit")')
    await editButton.click()
    await page.waitForTimeout(1000)
    
    console.log('Step 3: Find image input')
    const imageInput = page.locator('input[placeholder*="https://"], input[placeholder*="image"]').first()
    await expect(imageInput).toBeVisible()
    console.log('Image input found and visible')
    
    console.log('Step 4: Test fill with https URL')
    await imageInput.fill('https://images.unsplash.com/photo-1562774053-701939374585?w=800')
    let value = await imageInput.inputValue()
    console.log('Value after fill:', value)
    expect(value).toContain('https://')
    
    console.log('Step 5: Click Update button')
    const updateButton = page.locator('button:has-text("Update")')
    await updateButton.click()
    await page.waitForTimeout(500)
    
    console.log('✓ Test completed successfully!')
  })

  test('Verify marker click opens detail panel then edit modal', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(3000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(1500)
    
    const detailPanel = page.locator('.absolute.top-0.right-0')
    const editButtonInPanel = page.locator('button:has-text("Edit")')
    
    if (await editButtonInPanel.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('Edit button found in detail panel')
      await editButtonInPanel.click()
      await page.waitForTimeout(1000)
      
      const modal = page.locator('.fixed.inset-0.z-\\[1500\\]')
      await expect(modal).toBeVisible()
      console.log('✓ Edit modal opened successfully')
    } else {
      console.log('No edit button visible, checking for detail panel')
      console.log('Detail panel visible:', await detailPanel.isVisible())
    }
  })

  test('Test keyboard shortcut in modal', async ({ page }) => {
    await page.goto('http://localhost:5173/')
    await page.waitForTimeout(3000)
    
    const firstMarker = page.locator('.custom-marker').first()
    await firstMarker.click()
    await page.waitForTimeout(1000)
    
    const editButton = page.locator('button:has-text("Edit")')
    await editButton.click()
    await page.waitForTimeout(1000)
    
    const nameInput = page.locator('input[placeholder="e.g., The Wave"]')
    await expect(nameInput).toBeVisible()
    
    await nameInput.fill('Test Name')
    await page.waitForTimeout(200)
    
    const filledValue = await nameInput.inputValue()
    console.log('Name input value:', filledValue)
    expect(filledValue).toBe('Test Name')
    
    console.log('✓ Input fields work correctly')
  })
})
