import { ApiError, type DeliveryResult, type Job } from './api.js'

const statuses = new Map([
  ['partially_shipped', 'частично отправлен'],
  ['shipped', 'отправлен'],
  ['partially_delivered', 'частично доставлен'],
  ['delivered', 'доставлен'],
  ['cancelled', 'отменён'],
])

export function notificationText(job: Job): string {
  if (job.event === 'seller_new_order') return `Mint Market · Новый заказ №${job.order_id}.`
  const status = statuses.get(job.event)
  if (!status) throw new ApiError(400)
  return `Mint Market · Заказ №${job.order_id} ${status}.`
}

export function deliveryFailure(error: unknown): DeliveryResult {
  if (error instanceof ApiError) {
    if (error.status === 429) return { outcome: 'retry', retry_after: Math.min(error.retryAfter, 86400) }
    if (error.status >= 400 && error.status < 500 && error.status !== 408) return { outcome: 'failed' }
  }
  return { outcome: 'retry' }
}
