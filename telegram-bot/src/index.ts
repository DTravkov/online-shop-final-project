import { setTimeout as delay } from 'node:timers/promises'

import { ApiError, Backend, Telegram, type DeliveryResult, type Update } from './api.js'
import { decodeBotKey, encryptRedemption } from './crypto.js'
import { deliveryFailure, notificationText } from './notifications.js'

function required(name: string): string {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`Set ${name}.`)
  return value
}

const stop = new AbortController()
const signal = stop.signal
process.once('SIGINT', () => stop.abort())
process.once('SIGTERM', () => stop.abort())

const botKey = decodeBotKey(required('TELEGRAM_BOT_KEY'))
const backend = new Backend(required('TELEGRAM_BACKEND_URL').replace(/\/+$/, ''), required('TELEGRAM_SERVICE_TOKEN'), signal)
const telegram = new Telegram(required('TELEGRAM_BOT_TOKEN'), signal)

async function pause(milliseconds: number): Promise<void> {
  await delay(milliseconds, undefined, { signal }).catch(() => {})
}

async function processUpdate(update: Update): Promise<void> {
  const message = update.message
  if (message?.chat.type !== 'private' || !message.text) return
  const start = /^\/start(?:@\w+)?(?: ([A-Za-z0-9_-]{59}))?$/.exec(message.text.trim())
  if (!start) return

  const chatId = message.chat.id
  let reply = 'Откройте профиль Mint Market и нажмите «Подключить Telegram».'
  if (start[1]) {
    try {
      const { code } = await backend.redeem(encryptRedemption(botKey, start[1], chatId))
      reply = `Введите код в профиле Mint Market, чтобы подтвердить подключение Telegram: ${code}`
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        reply = 'Этот чат уже подключён. Отключите его в текущем профиле Mint Market и попробуйте снова.'
      } else if (error instanceof ApiError && (error.status === 400 || error.status === 422)) {
        reply = 'Ссылка истекла или уже использована. Создайте новую ссылку в профиле Mint Market.'
      } else {
        console.warn('Telegram link redemption is temporarily unavailable.')
        reply = 'Не удалось подключить Telegram. Попробуйте создать новую ссылку в профиле Mint Market.'
      }
    }
  }
  await telegram.send(chatId, reply)
}

async function pollUpdates(): Promise<void> {
  let offset: number | undefined
  while (!signal.aborted) {
    try {
      for (const update of await telegram.updates(offset)) {
        try {
          await processUpdate(update)
        } catch {
          if (!signal.aborted) console.warn('Could not reply to a Telegram update.')
        }
        offset = update.update_id + 1
      }
    } catch (error) {
      if (signal.aborted) break
      const wait = error instanceof ApiError ? Math.max(5, error.retryAfter) : 5
      console.warn('Telegram update polling failed. Retrying.')
      await pause(wait * 1000)
    }
  }
}

async function deliverNotifications(): Promise<void> {
  while (!signal.aborted) {
    try {
      const job = await backend.claim()
      if (!job) {
        await pause(5000)
        continue
      }
      let result: DeliveryResult
      try {
        await telegram.send(job.chat_id, notificationText(job))
        result = { outcome: 'sent' }
      } catch (error) {
        result = deliveryFailure(error)
      }
      try {
        await backend.report(job, result)
      } catch (error) {
        // A repeated report for the same lease is harmless if the first report reached FastAPI.
        if (error instanceof ApiError && error.status < 500) throw error
        await backend.report(job, result)
      }
      if (result.retry_after) await pause(result.retry_after * 1000)
    } catch {
      if (signal.aborted) break
      console.warn('Notification job processing failed. Retrying.')
      await pause(5000)
    }
  }
}

console.info('Mint Market Telegram bot started.')
await Promise.all([pollUpdates(), deliverNotifications()])
