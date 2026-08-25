import type { HistoryRecord } from '../api/contracts'

const DATABASE = 'sna-learning-history'
const STORE = 'runs'

function openHistory(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1)
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) {
        const store = request.result.createObjectStore(STORE, { keyPath: 'id' })
        store.createIndex('createdAt', 'createdAt')
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('无法打开本地实验历史。'))
  })
}

function complete(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => reject(transaction.error ?? new Error('本地历史写入失败。'))
    transaction.onabort = () => reject(transaction.error ?? new Error('本地历史操作已取消。'))
  })
}

export async function saveHistory(record: HistoryRecord): Promise<void> {
  const database = await openHistory()
  try {
    const transaction = database.transaction(STORE, 'readwrite')
    transaction.objectStore(STORE).put(record)
    await complete(transaction)
  } finally { database.close() }
}

export async function listHistory(): Promise<HistoryRecord[]> {
  const database = await openHistory()
  try {
    const transaction = database.transaction(STORE, 'readonly')
    const request = transaction.objectStore(STORE).getAll()
    const rows = await new Promise<HistoryRecord[]>((resolve, reject) => {
      request.onsuccess = () => resolve(request.result as HistoryRecord[])
      request.onerror = () => reject(request.error ?? new Error('无法读取本地实验历史。'))
    })
    await complete(transaction)
    return rows.sort((left, right) => right.createdAt.localeCompare(left.createdAt))
  } finally { database.close() }
}

export async function deleteHistory(id: string): Promise<void> {
  const database = await openHistory()
  try {
    const transaction = database.transaction(STORE, 'readwrite')
    transaction.objectStore(STORE).delete(id)
    await complete(transaction)
  } finally { database.close() }
}

export async function clearHistory(): Promise<void> {
  const database = await openHistory()
  try {
    const transaction = database.transaction(STORE, 'readwrite')
    transaction.objectStore(STORE).clear()
    await complete(transaction)
  } finally { database.close() }
}
