import { test, expect } from '@playwright/test'

test.describe('US4 - Sidebar collapse and expand', () => {
  test('starts extended and toggles collapsed/extended from sidebar header', async ({ page }) => {
    await page.goto('/')

    const sidebar = page.locator('[data-testid="sidebar"]')
    await expect(sidebar).toHaveClass(/is-extended/)

    await page.getByTestId('sidebar-toggle').click()
    await expect(sidebar).toHaveClass(/is-collapsed/)

    await page.getByTestId('sidebar-toggle').click()
    await expect(sidebar).toHaveClass(/is-extended/)
  })

  test('auto-collapses after selecting a project card', async ({ page }) => {
    await page.goto('/')

    const projectCardLink = page.locator('.project-card .card-title').first()
    await expect(projectCardLink).toBeVisible()
    await projectCardLink.click()

    await expect(page).toHaveURL(/\/projects\//)
    await expect(page.getByTestId('sidebar')).toHaveClass(/is-collapsed/)
  })

  test('shows icon tooltip metadata in collapsed mode', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('sidebar-toggle').click()

    const projectNav = page.getByTestId('nav-item-project')
    await expect(projectNav).toHaveAttribute('aria-label', 'Project')
    await expect(projectNav).toHaveAttribute('title', 'Project')
  })
})
