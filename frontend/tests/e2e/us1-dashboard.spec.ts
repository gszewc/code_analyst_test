import { test, expect } from '@playwright/test'

test.describe('US1 - Dashboard', () => {
  test('loads dashboard and shows project list or empty state', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(/Projects/i)).toBeVisible()
    // Shows either empty state or project cards
    const emptyState = page.getByText(/No projects yet/i)
    const projectGrid = page.locator('.project-grid')
    await expect(emptyState.or(projectGrid)).toBeVisible()
  })

  test('can open new project dialog', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /New Project/i }).first().click()
    await expect(page.getByRole('heading', { name: /New Project/i })).toBeVisible()
  })

  test('validates project name field', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /New Project/i }).first().click()
    await page.getByRole('button', { name: /^Create$/ }).click()
    await expect(page.getByText(/required/i)).toBeVisible()
  })
})
