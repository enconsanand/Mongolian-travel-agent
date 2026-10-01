import { BRAND } from '~/constants/brand'
import type { AppLocale } from '~/types/trip-planner'

export const MERCHANT_NAME = BRAND.name
export const CHECKOUT_POLL_MS = 2500

export const UNIT_LABELS: Record<string, Record<AppLocale, string>> = {
  ger: { mn: 'Гэр', en: 'Ger' },
  double_room: { mn: 'Хоёр хүний өрөө', en: 'Double room' },
  family_room: { mn: 'Гэр бүлийн өрөө', en: 'Family room' },
  dorm_bed: { mn: 'Дотуур байрны ор', en: 'Dorm bed' },
  suite: { mn: 'Люкс өрөө', en: 'Suite' },
  whole_house: { mn: 'Бүтэн байшин', en: 'Whole house' },
  wooden_cabin: { mn: 'Модон байшин', en: 'Wooden cabin' },
}

export const CHECKOUT_MESSAGES = {
  mn: {
    title: 'Захиалгаа батлах',
    subtitle: 'Доорх сагс, дүнг зөвхөн энэ төхөөрөмж дээрх таны түлхүүрээр батална.',
    languageGroupLabel: 'Хэл',
    verified: 'Merchant-ийн гарын үсэг шалгагдсан',
    untrusted: 'Энэ checkout-ийн гарын үсэг таарахгүй байна. Батлах боломжгүй.',
    nights: 'шөнө',
    total: 'Нийт дүн',
    payee: 'Хүлээн авагч',
    expiresIn: 'Хугацаа дуусахад',
    instrument: 'Төлбөрийн хэлбэр',
    qpay: 'QPay (банкны апп)',
    card: 'Карт',
    approve: 'Батлах, төлбөр үүсгэх',
    approveNote: 'Та яг энэ сагсыг, яг энэ дүнгээр төлөхийг зөвшөөрч байна. Агент үүнийг өөрчилж чадахгүй.',
    signing: 'Гарын үсэг зурж байна…',
    payTitle: 'QPay-ээр төлөх',
    payHint: 'Банкны аппаараа QR уншуулах эсвэл доорх холбоосыг нээнэ үү.',
    waiting: 'Төлбөр хүлээж байна…',
    simPay: 'Sim Bank-аар төлөх (демо)',
    booked: 'Захиалга баталгаажлаа',
    bookedHint: 'Бүх шөнө баталгаажсан. Баримт болон дэлгэрэнгүйг аяллын хэсгээс харна уу.',
    expired: 'Хугацаа дууссан',
    expiredHint: 'Өрөөнүүд суллагдсан. Шинээр захиалга үүсгэнэ үү.',
    failed: 'Төлбөр амжилтгүй',
    failedHint: 'Өрөөнүүд суллагдсан. Дахин оролдоно уу.',
    loading: 'Ачаалж байна…',
    error: 'Алдаа гарлаа',
  },
  en: {
    title: 'Approve your booking',
    subtitle: 'You approve the basket and amount below with your key on this device only.',
    languageGroupLabel: 'Language',
    verified: 'Merchant signature verified',
    untrusted: 'The signature on this checkout does not match. It cannot be approved.',
    nights: 'nights',
    total: 'Total',
    payee: 'Payee',
    expiresIn: 'Expires in',
    instrument: 'Pay with',
    qpay: 'QPay (bank app)',
    card: 'Card',
    approve: 'Approve and create payment',
    approveNote: 'You authorise exactly this basket for exactly this amount. The agent cannot change it.',
    signing: 'Signing…',
    payTitle: 'Pay with QPay',
    payHint: 'Scan the QR with your bank app or open one of the links below.',
    waiting: 'Waiting for payment…',
    simPay: 'Pay with Sim Bank (demo)',
    booked: 'Booking confirmed',
    bookedHint: 'Every night is confirmed. See your trip for the receipt and details.',
    expired: 'Expired',
    expiredHint: 'The rooms were released. Please create a new booking.',
    failed: 'Payment failed',
    failedHint: 'The rooms were released. Please try again.',
    loading: 'Loading…',
    error: 'Something went wrong',
  },
} satisfies Record<AppLocale, Record<string, string>>

export type CheckoutMessages = (typeof CHECKOUT_MESSAGES)['mn']
