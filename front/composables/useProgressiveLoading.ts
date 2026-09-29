export function useProgressiveLoading() {
  const showSkeleton = ref(true)
  const showContent = ref(false)
  const isDataLoaded = ref(false)

  const minLoadingTime = 800

  const startLoading = () => {
    showSkeleton.value = true
    showContent.value = false
    isDataLoaded.value = false
  }

  const finishLoading = async () => {
    isDataLoaded.value = true

    await new Promise((resolve) => setTimeout(resolve, minLoadingTime))

    showSkeleton.value = false

    await new Promise((resolve) => setTimeout(resolve, 150))
    showContent.value = true
  }

  const resetLoading = () => {
    showSkeleton.value = false
    showContent.value = true
    isDataLoaded.value = true
  }

  return {
    showSkeleton: readonly(showSkeleton),
    showContent: readonly(showContent),
    isDataLoaded: readonly(isDataLoaded),
    startLoading,
    finishLoading,
    resetLoading,
  }
}
