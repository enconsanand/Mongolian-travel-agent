import { API_ENDPOINTS } from '~/constants'
import { CHECKOUT_POLL_MS, MERCHANT_NAME } from '~/constants/checkout'
import type { CheckoutStage, CheckoutView, InstrumentType, MerchantJwks, PaymentView } from '~/types/checkout'
import { signPaymentMandate, verifyCheckout, type VerifiedCheckout } from '~/utils/ap2'

/**
 * The trusted surface's state: load the checkout, verify the merchant signature, let the user sign the Payment
 * Mandate, show the invoice and follow it until the booking is confirmed or released.
 */
export const useCheckoutPayment = (checkoutId: string) => {
  const api = useApi()
  const signingKey = useSigningKey()
  const config = useRuntimeConfig()

  const stage = ref<CheckoutStage>('loading')
  const checkout = shallowRef<CheckoutView | null>(null)
  const verified = shallowRef<VerifiedCheckout | null>(null)
  const payment = shallowRef<PaymentView | null>(null)
  const errorMessage = ref<string | null>(null)
  let timer: ReturnType<typeof setInterval> | null = null

  const nowSec = () => Math.floor(Date.now() / 1000)

  /** The API's error code ({detail: {code}}) when there is one, else the message. */
  function errorCode(err: unknown): string {
    const detail = (err as { data?: { detail?: { code?: string; detail?: string } | string } })?.data?.detail
    if (detail && typeof detail === 'object') return [detail.code, detail.detail].filter(Boolean).join(': ')
    return (err as Error)?.message ?? 'error'
  }

  function stageFrom(view: CheckoutView): CheckoutStage {
    if (view.bookings.length && view.bookings.every((b) => b.status === 'confirmed')) return 'booked'
    if (view.status === 'expired') return 'expired'
    if (view.status === 'cancelled' || view.payment?.status === 'failed') return 'failed'
    if (view.payment && ['awaiting_payment', 'paid'].includes(view.payment.status)) return 'paying'
    return 'review'
  }

  async function refresh(): Promise<void> {
    const { data, error } = await api.get<CheckoutView>(API_ENDPOINTS.BOOKINGS.CHECKOUT(checkoutId))
    if (error || !data) {
      errorMessage.value = errorCode(error ?? new Error('not found'))
      return
    }
    checkout.value = data
    if (data.payment) payment.value = data.payment
    if (stage.value !== 'untrusted' && stage.value !== 'signing') stage.value = stageFrom(data)
    if (!['paying'].includes(stage.value)) stopPolling()
  }

  async function load(): Promise<void> {
    stage.value = 'loading'
    await refresh()
    const view = checkout.value
    if (!view) return
    const { data: jwks } = await api.get<MerchantJwks>(API_ENDPOINTS.PAYMENTS.MERCHANT_JWKS)
    try {
      if (!jwks?.keys[0]) throw new Error('no merchant key')
      verified.value = await verifyCheckout({
        checkoutJwt: view.checkout_jwt,
        checkoutId,
        serverHash: view.checkout_hash,
        merchantJwk: jwks.keys[0],
        merchantId: jwks.merchant_id,
        // An expired checkout still renders (read only); only an open one must be within its time
        nowSec: view.status === 'open' ? nowSec() : 0,
      })
    } catch (err) {
      stage.value = 'untrusted'
      errorMessage.value = (err as Error).message
      return
    }
    if (stageFrom(view) === 'paying') startPolling()
  }

  async function approve(instrument: InstrumentType): Promise<void> {
    if (!verified.value || stage.value !== 'review') return
    stage.value = 'signing'
    errorMessage.value = null
    try {
      const pay = async () => {
        const { privateKey, kid } = await signingKey.ensureKey()
        const mandate = await signPaymentMandate({
          checkout: verified.value as VerifiedCheckout,
          merchantName: MERCHANT_NAME,
          instrument,
          key: privateKey,
          kid,
          nowSec: nowSec(),
        })
        return api.post<PaymentView>(API_ENDPOINTS.PAYMENTS.PAY(checkoutId), {
          payment_mandate: mandate,
          kid,
          instrument,
        })
      }
      let { data, error } = await pay()
      if (errorCode(error).startsWith('key_not_found')) {
        await signingKey.reRegister()
        ;({ data, error } = await pay())
      }
      if (error || !data) throw error ?? new Error('payment failed')
      payment.value = data
      stage.value = 'paying'
      startPolling()
    } catch (err) {
      stage.value = 'review'
      errorMessage.value = errorCode(err)
    }
  }

  /** Demo only: press "pay" on the QPay simulator, as a bank app would. */
  async function simulatePayment(): Promise<void> {
    const invoice = payment.value?.sim_invoice_id
    const base = config.public.qpaySimBase
    if (!invoice || !base) return
    await $fetch(`${base}/_sim/invoices/${invoice}/pay`, { method: 'POST' })
  }

  function startPolling() {
    stopPolling()
    timer = setInterval(refresh, CHECKOUT_POLL_MS)
  }

  function stopPolling() {
    if (timer) clearInterval(timer)
    timer = null
  }

  onUnmounted(stopPolling)

  const canSimulate = computed(() => Boolean(payment.value?.sim_invoice_id && config.public.qpaySimBase))

  return { stage, checkout, verified, payment, errorMessage, canSimulate, load, approve, simulatePayment }
}
