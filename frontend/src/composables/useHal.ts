import { computed, type ComputedRef } from 'vue'
import { halClient } from '@/services/hal'
import type { HalResource, HalLink } from '@/types'

export function useHal<T extends HalResource>(resource: ComputedRef<T | null>) {
  const links = computed(() => {
    if (!resource.value) return {}
    return halClient.extractLinks(resource.value)
  })

  const hasLink = computed(() => (rel: string): boolean => {
    if (!resource.value) return false
    return halClient.hasLink(resource.value, rel)
  })

  const getLink = computed(() => (rel: string): HalLink | null => {
    if (!resource.value) return null
    return halClient.getLink(resource.value, rel)
  })

  const getLinkHref = computed(() => (rel: string): string | null => {
    if (!resource.value) return null
    return halClient.getLinkHref(resource.value, rel)
  })

  const availableActions = computed(() => {
    if (!resource.value) return []
    return halClient.extractAvailableActions(resource.value)
  })

  const canPerformAction = computed(() => (action: string): boolean => {
    return availableActions.value.includes(action)
  })

  const followLink = async <R>(
    rel: string,
    data?: Record<string, unknown>
  ): Promise<R & HalResource | null> => {
    if (!resource.value) return null
    return halClient.followLink<R>(resource.value, rel, data)
  }

  return {
    links,
    hasLink,
    getLink,
    getLinkHref,
    availableActions,
    canPerformAction,
    followLink
  }
}

// Utility composable for working with HAL collections
export function useHalCollection<T>(collection: ComputedRef<{ items: T[]; links: Record<string, HalLink> } | null>) {
  const hasNextPage = computed(() => {
    if (!collection.value) return false
    return 'next' in collection.value.links
  })

  const hasPreviousPage = computed(() => {
    if (!collection.value) return false
    return 'prev' in collection.value.links
  })

  const hasFirstPage = computed(() => {
    if (!collection.value) return false
    return 'first' in collection.value.links
  })

  const hasLastPage = computed(() => {
    if (!collection.value) return false
    return 'last' in collection.value.links
  })

  const getNextPageUrl = computed(() => {
    if (!collection.value || !hasNextPage.value) return null
    return collection.value.links.next?.href || null
  })

  const getPreviousPageUrl = computed(() => {
    if (!collection.value || !hasPreviousPage.value) return null
    return collection.value.links.prev?.href || null
  })

  const getFirstPageUrl = computed(() => {
    if (!collection.value || !hasFirstPage.value) return null
    return collection.value.links.first?.href || null
  })

  const getLastPageUrl = computed(() => {
    if (!collection.value || !hasLastPage.value) return null
    return collection.value.links.last?.href || null
  })

  return {
    hasNextPage,
    hasPreviousPage,
    hasFirstPage,
    hasLastPage,
    getNextPageUrl,
    getPreviousPageUrl,
    getFirstPageUrl,
    getLastPageUrl
  }
}