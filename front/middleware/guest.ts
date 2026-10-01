export default defineNuxtRouteMiddleware((to) => {
  const auth = useAuth()

  if (auth.isLoggedIn.value) {
    // Keep the journey the visitor started (plan save, checkout) instead of dropping them on the home page
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : null
    return navigateTo(auth.safeRedirect(redirect))
  }
})
