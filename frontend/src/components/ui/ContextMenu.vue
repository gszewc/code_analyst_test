<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'

export interface ContextMenuItem {
  label: string
  action: () => void | Promise<void>
}

const props = defineProps<{
  x: number
  y: number
  items: ContextMenuItem[]
}>()

const emit = defineEmits<{
  close: []
}>()

function clampedX(): number {
  return Math.min(props.x, window.innerWidth - 200)
}

function clampedY(): number {
  return Math.min(props.y, window.innerHeight - props.items.length * 36 - 8)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

function onMousedown(e: MouseEvent) {
  const target = e.target as Element | null
  if (!target || !(target instanceof Element) || !target.closest('.context-menu')) {
    emit('close')
  }
}

async function handleItemClick(item: ContextMenuItem) {
  try {
    await item.action()
  } catch (err) {
    console.error('[ContextMenu] action error', err)
  } finally {
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  document.addEventListener('mousedown', onMousedown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('mousedown', onMousedown)
})
</script>

<template>
  <Teleport to="body">
    <div
      class="context-menu"
      role="menu"
      :style="{ left: `${clampedX()}px`, top: `${clampedY()}px` }"
    >
      <button
        v-for="item in items"
        :key="item.label"
        type="button"
        class="context-menu-item"
        role="menuitem"
        @click="() => handleItemClick(item)"
      >
        {{ item.label }}
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 9000;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  overflow: hidden;
  min-width: 180px;
}

.context-menu-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 8px 14px;
  background: none;
  border: none;
  font-size: 13px;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.context-menu-item:hover {
  background: var(--color-bg-overlay);
}
</style>
