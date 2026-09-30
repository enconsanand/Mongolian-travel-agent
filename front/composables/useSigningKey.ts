import { API_ENDPOINTS } from '~/constants'
import { exportPublicJwk, generateSigningKey } from '~/utils/ap2'

/**
 * The user's signing key for AP2 mandates. Made with WebCrypto as non-extractable, kept in IndexedDB (a CryptoKey
 * can be stored but its private part never read), and registered once with the backend (POST /me/keys).
 */

const DB_NAME = 'mta-signing'
const STORE = 'keys'

interface StoredKey {
  keyPair: CryptoKeyPair
  publicJwk: JsonWebKey
  kid: string | null
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function idb<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest): Promise<T> {
  const db = await openDb()
  return new Promise<T>((resolve, reject) => {
    const request = run(db.transaction(STORE, mode).objectStore(STORE))
    request.onsuccess = () => resolve(request.result as T)
    request.onerror = () => reject(request.error)
  }).finally(() => db.close())
}

export const useSigningKey = () => {
  const api = useApi()
  const cookieAuth = useCookieAuth()

  const storageKey = () => `user:${cookieAuth.userEmail.value || 'anonymous'}`

  async function register(stored: StoredKey): Promise<string> {
    const { data, error } = await api.post<{ kid: string }>(API_ENDPOINTS.PAYMENTS.KEYS, { jwk: stored.publicJwk })
    if (error || !data) throw error ?? new Error('key registration failed')
    stored.kid = data.kid
    await idb('readwrite', (store) => store.put(stored, storageKey()))
    return data.kid
  }

  /** The key to sign with, creating and registering it on first use. */
  async function ensureKey(): Promise<{ privateKey: CryptoKey; kid: string }> {
    let stored = await idb<StoredKey | undefined>('readonly', (store) => store.get(storageKey()))
    if (!stored) {
      const keyPair = await generateSigningKey()
      stored = { keyPair, publicJwk: await exportPublicJwk(keyPair.publicKey), kid: null }
    }
    const kid = stored.kid ?? (await register(stored))
    return { privateKey: stored.keyPair.privateKey, kid }
  }

  /** The server forgot the key (e.g. a database reset): register the same public key again. */
  async function reRegister(): Promise<void> {
    const stored = await idb<StoredKey | undefined>('readonly', (store) => store.get(storageKey()))
    if (stored) await register(stored)
  }

  return { ensureKey, reRegister }
}
