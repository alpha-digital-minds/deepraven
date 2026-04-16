import { reactive } from 'vue'

export interface Toast {
  id: number
  message: string
  type: 'info' | 'success' | 'error'
}

const toasts = reactive<Toast[]>([])
let _id = 0

export function useToast() {
  function toast(message: string, type: Toast['type'] = 'info', duration = 3500) {
    const id = ++_id
    toasts.push({ id, message, type })
    setTimeout(() => {
      const idx = toasts.findIndex(t => t.id === id)
      if (idx !== -1) toasts.splice(idx, 1)
    }, duration)
  }
  return { toasts, toast }
}
