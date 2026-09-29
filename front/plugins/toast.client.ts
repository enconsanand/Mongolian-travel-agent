import Vue3Toastify, { toast } from 'vue3-toastify'
// @ts-ignore
import 'vue3-toastify/dist/index.css'

export default defineNuxtPlugin((nuxtApp: any) => {
  nuxtApp.vueApp.use(Vue3Toastify, {
    autoClose: 2200,
    clearOnUrlChange: false,
    position: 'bottom-right',
    transition: 'slide',
    theme: 'colored',
  })

  return {
    provide: { toast },
  }
})
