export interface Update {
  update_id: number
  message?: { chat: { id: number, type: string }, text?: string }
}

export interface Job {
  notification_id: number
  lease_id: string
  chat_id: string
  order_id: number
  event: string
}

export interface DeliveryResult {
  outcome: 'sent' | 'retry' | 'failed'
  retry_after?: number
}

export class ApiError extends Error {
  constructor(readonly status: number, readonly retryAfter = 0) {
    super(`Request failed (${status})`)
  }
}

export class Backend {
  constructor(private readonly baseUrl: string, private readonly token: string, private readonly stop: AbortSignal) {}

  async redeem(envelope: string): Promise<{ code: string }> {
    return this.post('/telegram/bot/redeem', { envelope })
  }

  async claim(): Promise<Job | null> {
    return this.post('/telegram/bot/jobs/claim', {})
  }

  async report(job: Job, result: DeliveryResult): Promise<void> {
    await this.post(`/telegram/bot/jobs/${job.notification_id}/result`, { lease_id: job.lease_id, ...result })
  }

  private async post<T>(path: string, body: object): Promise<T> {
    const response = await fetch(this.baseUrl + path, {
      method: 'POST',
      headers: { Authorization: `Bearer ${this.token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.any([this.stop, AbortSignal.timeout(10_000)]),
    })
    if (!response.ok) throw new ApiError(response.status)
    if (response.status === 204) return undefined as T
    return await response.json() as T
  }
}

export class Telegram {
  constructor(private readonly token: string, private readonly stop: AbortSignal) {}

  async updates(offset?: number): Promise<Update[]> {
    return this.post('getUpdates', { offset, timeout: 30, allowed_updates: ['message'] }, 40_000)
  }

  async send(chatId: string | number, text: string): Promise<void> {
    await this.post('sendMessage', { chat_id: chatId, text }, 10_000)
  }

  private async post<T>(method: string, body: object, timeout: number): Promise<T> {
    const response = await fetch(`https://api.telegram.org/bot${this.token}/${method}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.any([this.stop, AbortSignal.timeout(timeout)]),
    })
    const result = await response.json().catch(() => null) as {
      ok: boolean, result: T, error_code?: number, parameters?: { retry_after?: number }
    } | null
    if (!response.ok || !result?.ok) {
      const status = result?.error_code ?? (response.ok ? 502 : response.status)
      throw new ApiError(status, result?.parameters?.retry_after)
    }
    return result.result
  }
}
