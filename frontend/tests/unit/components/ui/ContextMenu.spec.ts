import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

describe('ContextMenu', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  async function mountContextMenu(props = {}) {
    const ContextMenu = (await import('../../../../src/components/ui/ContextMenu.vue')).default
    return mount(ContextMenu, {
      props: {
        x: 100,
        y: 200,
        items: [{ label: 'Find in Graph', action: vi.fn() }],
        ...props,
      },
      attachTo: document.body,
    })
  }

  it('renders menu items', async () => {
    await mountContextMenu()
    const menuItem = document.querySelector('[role="menuitem"]')
    expect(menuItem?.textContent).toBe('Find in Graph')
  })

  it('is positioned at x/y coordinates', async () => {
    await mountContextMenu({ x: 150, y: 300 })
    const menu = document.querySelector('[role="menu"]')
    expect(menu?.getAttribute('style')).toContain('left: 150px')
    expect(menu?.getAttribute('style')).toContain('top: 300px')
  })

  it('calls item action and emits close when item is clicked', async () => {
    const action = vi.fn()
    const wrapper = await mountContextMenu({
      items: [{ label: 'Find in Graph', action }],
    })
    const menuItem = document.querySelector('[role="menuitem"]') as HTMLElement
    await menuItem.click()
    expect(action).toHaveBeenCalledOnce()
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close on Escape key', async () => {
    const wrapper = await mountContextMenu()
    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close when clicking outside the menu', async () => {
    const wrapper = await mountContextMenu()
    await document.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
