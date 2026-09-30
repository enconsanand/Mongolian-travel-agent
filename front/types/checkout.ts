export type InstrumentType = 'qpay_qr' | 'card'

export interface PaymentView {
  id: string
  status: 'approved_by_user' | 'awaiting_payment' | 'paid' | 'expired' | 'failed' | 'cancelled' | 'refunded'
  provider: 'qpay' | 'bonum' | 'sim'
  sim_invoice_id: string | null
  amount_mnt: number
  checkout_id: string | null
  qr_text: string | null
  qr_image: string | null
  short_url: string | null
  deeplinks: { name: string; logo: string; link: string }[]
}

export interface CheckoutView {
  id: string
  trip_id: string
  status: 'open' | 'paid' | 'expired' | 'cancelled'
  total_mnt: number
  expires_at: string
  checkout_jwt: string
  checkout_hash: string
  payment: PaymentView | null
  bookings: { id: string; status: string; stay_id: string | null }[]
}

export interface MerchantJwks {
  merchant_id: string
  keys: JsonWebKey[]
}

/** Where the checkout screen is: review -> signing -> paying -> booked, or a stop state. */
export type CheckoutStage = 'loading' | 'review' | 'signing' | 'paying' | 'booked' | 'expired' | 'failed' | 'untrusted'
