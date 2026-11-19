import { createCipheriv, randomBytes } from 'node:crypto'

const context = Buffer.from('mint-market:telegram:redeem:v1')

export function decodeBotKey(encoded: string): Buffer {
  const key = Buffer.from(encoded, 'base64url')
  if (key.length !== 32 || key.toString('base64url') !== encoded) {
    throw new Error('TELEGRAM_BOT_KEY must be a 32-byte, unpadded base64url key.')
  }
  return key
}

export function encryptRedemption(key: Buffer, start: string, chatId: number): string {
  const nonce = randomBytes(12)
  const cipher = createCipheriv('aes-256-gcm', key, nonce)
  cipher.setAAD(context)
  const json = JSON.stringify({ start, chat_id: String(chatId) })
  return Buffer.concat([nonce, cipher.update(json, 'utf8'), cipher.final(), cipher.getAuthTag()]).toString('base64url')
}
