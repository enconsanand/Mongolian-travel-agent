export default defineNuxtRouteMiddleware((to: any) => {
  const publicRoutes = ['/login']

  if (publicRoutes.includes(to.path)) return

  const isAuthenticatedRoute = to.meta.auth ?? true
  if (!isAuthenticatedRoute) {
    return
  }

  const isNotFoundPage = to.matched.length === 0
  if (isNotFoundPage) {
    return
  }

  const auth = useAuth()

  if (!auth.checkAuthStatus()) {
    return navigateTo('/login')
  }
})
