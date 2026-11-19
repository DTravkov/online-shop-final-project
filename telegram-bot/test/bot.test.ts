import assert from 'node:assert/strict'
import { createDecipheriv } from 'node:crypto'
import { test } from 'node:test'

import { ApiError, type Job } from '../src/api.js'
import { decodeBotKey, encryptRedemption } from '../src/crypto.js'
import { deliveryFailure, notificationText } from '../src/notifications.js'

test('redemption envelopes authenticate the context and preserve the chat ID as a string', () => {
  const key = decodeBotKey(Buffer.alloc(32, 7).toString('base64url'))
  const start = 'A'.repeat(59)
  const chatId = 4503599627370495
  const envelope = encryptRedemption(key, start, chatId)
  assert.match(envelope, /^[A-Za-z0-9_-]+$/)
  assert.notEqual(encryptRedemption(key, start, chatId), envelope)

  const raw = Buffer.from(envelope, 'base64url')
  const cipher = createDecipheriv('aes-256-gcm', key, raw.subarray(0, 12))
  cipher.setAAD(Buffer.from('mint-market:telegram:redeem:v1'))
  cipher.setAuthTag(raw.subarray(-16))
  const plaintext = Buffer.concat([cipher.update(raw.subarray(12, -16)), cipher.final()])
  assert.deepEqual(JSON.parse(plaintext.toString('utf8')), { start, chat_id: String(chatId) })
  assert.throws(() => decodeBotKey('bad-key'))
})

test('Telegram rate limits and transient errors are retried, while blocked chats fail', () => {
  assert.deepEqual(deliveryFailure(new ApiError(429, 23)), { outcome: 'retry', retry_after: 23 })
  assert.deepEqual(deliveryFailure(new ApiError(503)), { outcome: 'retry' })
  assert.deepEqual(deliveryFailure(new TypeError('network')), { outcome: 'retry' })
  assert.deepEqual(deliveryFailure(new ApiError(403)), { outcome: 'failed' })
})

test('order messages use seller and customer event text without profile details', () => {
  const job: Job = { notification_id: 1, lease_id: 'lease', chat_id: '10', order_id: 42, event: 'seller_new_order' }
  assert.equal(notificationText(job), 'Mint Market · Новый заказ №42.')
  assert.equal(notificationText({ ...job, event: 'partially_delivered' }), 'Mint Market · Заказ №42 частично доставлен.')
  assert.throws(() => notificationText({ ...job, event: 'unknown' }), ApiError)
})
