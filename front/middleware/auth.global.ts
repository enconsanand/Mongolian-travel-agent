export default defineNuxtRouteMiddleware((to) => {
  const publicRoutes = ['/login', '/register']

  if (publicRoutes.includes(to.path)) return

  const isAuthenticatedRoute = to.meta.auth ?? true
  if (!isAuthenticatedRoute) {
    return
  }

  const isNotFoundPage = to.matched.length === 0
  if (isNotFoundPage) {
    return
  }

  if (!useAuth().isLoggedIn.value) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }
})
