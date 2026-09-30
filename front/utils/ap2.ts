/**
 * AP2 v0.2 in the browser: verify the merchant-signed checkout, then sign the user's Payment Mandate.
 *
 * Mirrors back/app/ap2: ES256 compact JWS with a raw 64-byte r||s signature (what WebCrypto ECDSA returns), and
 * a mandate is an SD-JWT with no disclosures (`<jws>~`). The amount and payee are read from the *signed*
 * checkout, never from API JSON, and the checkout hash is computed here, so a tampered response cannot make the
 * user sign something other than what the merchant signed.
 */

const encoder = new TextEncoder()
const decoder = new TextDecoder()

export const MANDATE_TYP = 'dc+sd-jwt'
export const PAYMENT_VCT = 'mandate.payment.1'
const ECDSA_P256 = { name: 'ECDSA', namedCurve: 'P-256' } as const
const ECDSA_SHA256 = { name: 'ECDSA', hash: 'SHA-256' } as const

export interface Amount {
  amount: number
  currency: 'MNT'
}

export interface LocalizedText {
  mn: string
  en: string
}

export interface CheckoutClaimLine {
  kind: string
  ref_id: string
  qty: number
  unit_price_mnt: number
  total_mnt: number
  label: LocalizedText
  date?: string | null
  unit_type?: string | null
}

export interface CheckoutClaims {
  iss: string
  checkout_id: string
  trip_id: string
  lines: CheckoutClaimLine[]
  total: Amount
  iat: number
  exp: number
}

export function b64url(bytes: Uint8Array): string {
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function b64urlToBytes(text: string): Uint8Array<ArrayBuffer> {
  const base64 = text.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (text.length % 4)) % 4)
  const binary = atob(base64)
  return Uint8Array.from(binary, (char) => char.charCodeAt(0))
}

function jsonSegment(value: unknown): string {
  return b64url(encoder.encode(JSON.stringify(value)))
}

/** base64url(SHA-256(ascii)): how AP2 binds a mandate to the checkout JWT. */
export async function sha256B64url(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(text))
  return b64url(new Uint8Array(digest))
}

export function decodeJwt<T>(token: string): { header: Record<string, unknown>; payload: T } {
  const parts = token.split('.')
  if (parts.length !== 3) throw new Error('not a compact JWS')
  const [header, payload] = parts.slice(0, 2).map((part) => JSON.parse(decoder.decode(b64urlToBytes(part))))
  return { header, payload: payload as T }
}

/** Check an ES256 JWS against a public JWK. Only ES256 is accepted, whatever the token's header says. */
export async function verifyEs256(token: string, jwk: JsonWebKey): Promise<boolean> {
  const parts = token.split('.')
  if (parts.length !== 3) return false
  // Only the header is read before the signature is checked
  const header = JSON.parse(decoder.decode(b64urlToBytes(parts[0] as string))) as Record<string, unknown>
  if (header.alg !== 'ES256' || jwk.kty !== 'EC' || jwk.crv !== 'P-256' || 'd' in jwk) return false
  const key = await crypto.subtle.importKey('jwk', { kty: 'EC', crv: 'P-256', x: jwk.x, y: jwk.y }, ECDSA_P256, false, [
    'verify',
  ])
  const signingInput = token.slice(0, token.lastIndexOf('.'))
  const signature = b64urlToBytes(token.slice(token.lastIndexOf('.') + 1))
  if (signature.length !== 64) return false
  return crypto.subtle.verify(ECDSA_SHA256, key, signature, encoder.encode(signingInput))
}

export async function signEs256(payload: object, key: CryptoKey, kid: string, typ: string): Promise<string> {
  const signingInput = `${jsonSegment({ alg: 'ES256', kid, typ })}.${jsonSegment(payload)}`
  const signature = await crypto.subtle.sign(ECDSA_SHA256, key, encoder.encode(signingInput))
  return `${signingInput}.${b64url(new Uint8Array(signature))}`
}

export function generateSigningKey(): Promise<CryptoKeyPair> {
  // Non-extractable: the private key can sign but can never be read out of the browser
  return crypto.subtle.generateKey(ECDSA_P256, false, ['sign', 'verify'])
}

export async function exportPublicJwk(key: CryptoKey): Promise<JsonWebKey> {
  const { kty, crv, x, y } = await crypto.subtle.exportKey('jwk', key)
  return { kty, crv, x, y }
}

export interface VerifiedCheckout {
  claims: CheckoutClaims
  hash: string
}

/**
 * Everything the trusted surface shows comes out of this: the merchant signature checks, it is the checkout we
 * asked for, it has not expired, and the hash the server reported is the one we compute ourselves.
 */
export async function verifyCheckout(opts: {
  checkoutJwt: string
  checkoutId: string
  serverHash: string
  merchantJwk: JsonWebKey
  merchantId: string
  nowSec: number
}): Promise<VerifiedCheckout> {
  if (!(await verifyEs256(opts.checkoutJwt, opts.merchantJwk))) throw new Error('merchant_signature')
  const { payload } = decodeJwt<CheckoutClaims>(opts.checkoutJwt)
  if (payload.iss !== opts.merchantId) throw new Error('wrong_merchant')
  if (payload.checkout_id !== opts.checkoutId) throw new Error('wrong_checkout')
  if (payload.exp < opts.nowSec) throw new Error('expired')
  const hash = await sha256B64url(opts.checkoutJwt)
  if (hash !== opts.serverHash) throw new Error('hash_mismatch')
  return { claims: payload, hash }
}

/** The closed Payment Mandate for direct mode: pay exactly this checkout's signed total to its merchant. */
export async function signPaymentMandate(opts: {
  checkout: VerifiedCheckout
  merchantName: string
  instrument: 'qpay_qr' | 'card'
  key: CryptoKey
  kid: string
  nowSec: number
  ttlSec?: number
}): Promise<string> {
  const claims = {
    vct: PAYMENT_VCT,
    transaction_id: opts.checkout.hash,
    payee: { id: opts.checkout.claims.iss, name: opts.merchantName },
    payment_amount: opts.checkout.claims.total,
    payment_instrument: { type: opts.instrument },
    iat: opts.nowSec,
    exp: opts.nowSec + (opts.ttlSec ?? 600),
  }
  return `${await signEs256(claims, opts.key, opts.kid, MANDATE_TYP)}~`
}
