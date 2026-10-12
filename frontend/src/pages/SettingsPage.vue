<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, ApiRequestError } from '@/api/client'
import { useAppStore } from '@/stores/useAppStore'
import type { LLMProvider } from '@/api/types'
import AppLayout from '@/layouts/AppLayout.vue'
import { CheckCircleIcon, XCircleIcon, LoaderIcon } from 'lucide-vue-next'

const appStore = useAppStore()

const provider = ref<LLMProvider | ''>('')
const model = ref('')
const apiKey = ref('')
const baseUrl = ref('')
const isLoading = ref(false)
const isSaving = ref(false)
const isTesting = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)

const showApiKey = computed(() => provider.value === 'openai' || provider.value === 'anthropic')
const showBaseUrl = computed(() => provider.value === 'ollama')

onMounted(async () => {
  isLoading.value = true
  try {
    const config = await api.llm.getConfig()
    provider.value = config.provider ?? ''
    model.value = config.model ?? ''
    baseUrl.value = config.base_url ?? ''
    // API key is write-only — field stays blank unless user enters a new one
  } catch {
    // ignore — settings page still usable
  } finally {
    isLoading.value = false
  }
})

async function save() {
  if (!provider.value || !model.value) return
  isSaving.value = true
  saveError.value = ''
  saveSuccess.value = false
  try {
    const updated = await api.llm.updateConfig({
      provider: provider.value as LLMProvider,
      model: model.value,
      ...(apiKey.value ? { api_key: apiKey.value } : {}),
      ...(baseUrl.value ? { base_url: baseUrl.value } : {}),
    })
    appStore.setLLMConfigured(updated.is_configured)
    saveSuccess.value = true
    apiKey.value = '' // clear key field after save
  } catch (err) {
    saveError.value = err instanceof ApiRequestError ? err.detail : 'Failed to save configuration'
  } finally {
    isSaving.value = false
  }
}

async function testConnection() {
  isTesting.value = true
  testResult.value = null
  try {
    testResult.value = await api.llm.testConnection()
  } catch (err) {
    testResult.value = {
      success: false,
      message: err instanceof ApiRequestError ? err.detail : 'Connection test failed',
    }
  } finally {
    isTesting.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="page">
      <header class="page-header">
        <h1 class="page-title">
          Settings
        </h1>
        <p class="page-subtitle">
          Configure LLM provider for AI documentation generation
        </p>
      </header>

      <div
        v-if="isLoading"
        class="loading"
      >
        Loading settings…
      </div>

      <form
        v-else
        class="settings-form"
        @submit.prevent="save"
      >
        <div class="form-card">
          <h2 class="card-title">
            LLM Provider
          </h2>

          <div class="field">
            <label
              class="field-label"
              for="provider"
            >Provider</label>
            <select
              id="provider"
              v-model="provider"
              class="field-input"
            >
              <option value="">
                — Select provider —
              </option>
              <option value="openai">
                OpenAI
              </option>
              <option value="anthropic">
                Anthropic
              </option>
              <option value="ollama">
                Ollama (local)
              </option>
            </select>
          </div>

          <div class="field">
            <label
              class="field-label"
              for="model"
            >Model</label>
            <input
              id="model"
              v-model="model"
              type="text"
              class="field-input"
              placeholder="e.g. gpt-4o, claude-3-5-sonnet, llama3.2"
              :disabled="!provider"
            >
          </div>

          <div
            v-if="showApiKey"
            class="field"
          >
            <label
              class="field-label"
              for="api-key"
            >
              API Key
              <span class="field-hint">(write-only — leave blank to keep existing)</span>
            </label>
            <input
              id="api-key"
              v-model="apiKey"
              type="password"
              class="field-input"
              placeholder="sk-…"
              autocomplete="new-password"
            >
          </div>

          <div
            v-if="showBaseUrl"
            class="field"
          >
            <label
              class="field-label"
              for="base-url"
            >Base URL</label>
            <input
              id="base-url"
              v-model="baseUrl"
              type="url"
              class="field-input"
              placeholder="http://localhost:11434"
            >
          </div>

          <div
            v-if="saveError"
            class="form-error"
          >
            {{ saveError }}
          </div>
          <div
            v-if="saveSuccess"
            class="form-success"
          >
            <CheckCircleIcon :size="14" /> Configuration saved
          </div>

          <div class="form-footer">
            <button
              type="button"
              class="btn-ghost"
              :disabled="isTesting || !provider"
              @click="testConnection"
            >
              <LoaderIcon
                v-if="isTesting"
                :size="14"
                class="spin"
              />
              Test connection
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="isSaving || !provider || !model"
            >
              {{ isSaving ? 'Saving…' : 'Save' }}
            </button>
          </div>

          <div
            v-if="testResult"
            :class="['test-result', testResult.success ? 'success' : 'failure']"
          >
            <CheckCircleIcon
              v-if="testResult.success"
              :size="14"
            />
            <XCircleIcon
              v-else
              :size="14"
            />
            {{ testResult.message }}
          </div>
        </div>
      </form>
    </div>
  </AppLayout>
</template>

<style scoped>
.page {
  padding: 32px;
  max-width: 600px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
}

.loading {
  color: var(--color-text-muted);
  font-size: 14px;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 400;
  margin-left: 6px;
}

.field-input {
  background: var(--color-bg-overlay);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: 14px;
  padding: 8px 12px;
  outline: none;
  transition: border-color var(--transition-fast);
  font-family: inherit;
  box-sizing: border-box;
  width: 100%;
}

.field-input:focus {
  border-color: var(--color-accent);
}

.field-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-input option {
  background: var(--color-bg-overlay);
}

.form-error {
  font-size: 13px;
  color: var(--color-error);
  background: rgba(248, 81, 73, 0.09);
  border: 1px solid rgba(248, 81, 73, 0.2);
  border-radius: var(--radius-md);
  padding: 8px 12px;
}

.form-success {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-success);
  background: rgba(86, 211, 100, 0.09);
  border: 1px solid rgba(86, 211, 100, 0.2);
  border-radius: var(--radius-md);
  padding: 8px 12px;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  padding-top: 4px;
}

.test-result {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
}

.test-result.success {
  color: var(--color-success);
  background: rgba(86, 211, 100, 0.09);
  border: 1px solid rgba(86, 211, 100, 0.2);
}

.test-result.failure {
  color: var(--color-error);
  background: rgba(248, 81, 73, 0.09);
  border: 1px solid rgba(248, 81, 73, 0.2);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--color-accent);
  color: #000;
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
