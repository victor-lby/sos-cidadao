import { ref, type Ref } from 'vue'
import type { ApiError, AppError } from '@/types'

interface ErrorHandlerOptions {
  successMessage?: string
  errorMessage?: string
  retryable?: boolean
}

export function useErrorHandler() {
  const error = ref<AppError | null>(null)
  const isLoading = ref(false)
  const lastAction = ref<(() => Promise<unknown>) | null>(null)

  const handleAsyncAction = async <T>(
    action: () => Promise<T>,
    options: ErrorHandlerOptions = {}
  ): Promise<T | null> => {
    isLoading.value = true
    error.value = null
    lastAction.value = options.retryable ? action : null

    try {
      const result = await action()

      if (options.successMessage) {
        // TODO: Show success toast when we implement notifications
        console.log(options.successMessage)
      }

      return result
    } catch (err) {
      const errorMessage = options.errorMessage || extractErrorMessage(err)

      error.value = {
        message: errorMessage,
        retryable: options.retryable || false,
        originalError: err as Error | ApiError
      }

      return null
    } finally {
      isLoading.value = false
    }
  }

  const clearError = (): void => {
    error.value = null
  }

  const retryLastAction = async (): Promise<void> => {
    if (lastAction.value) {
      await handleAsyncAction(lastAction.value, { retryable: true })
    }
  }

  return {
    error: error as Readonly<Ref<AppError | null>>,
    isLoading: isLoading as Readonly<Ref<boolean>>,
    handleAsyncAction,
    clearError,
    retryLastAction
  }
}

function extractErrorMessage(error: unknown): string {
  if (typeof error === 'string') {
    return error
  }

  if (error && typeof error === 'object') {
    // Handle API errors (RFC 7807 format)
    if ('detail' in error && typeof error.detail === 'string') {
      return error.detail
    }

    // Handle standard Error objects
    if ('message' in error && typeof error.message === 'string') {
      return error.message
    }

    // Handle validation errors
    if ('errors' in error && Array.isArray(error.errors)) {
      const validationErrors = error.errors as Array<{ field: string; message: string }>
      return validationErrors.map(e => `${e.field}: ${e.message}`).join(', ')
    }
  }

  return 'An unexpected error occurred'
}