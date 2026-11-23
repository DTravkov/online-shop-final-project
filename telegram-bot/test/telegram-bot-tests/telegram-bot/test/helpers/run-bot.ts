import { spawn, type ChildProcess } from 'node:child_process'
import { createDecipheriv } from 'node:crypto'
import { fileURLToPath } from 'node:url'

export const BOT_KEY_BYTES = Buffer.alloc(32, 9)
export const SERVICE_TOKEN = 'svc-token'
export const BOT_TOKEN = '123:ABC'

export interface Call {
  url: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  body: any
  authorization: string | null
}

// Запущенный бот + список всех его сетевых запросов.
export class RunningBot {
  calls: Call[] = []
  stderr = ''
  private buffer = ''

  constructor(private readonly child: ChildProcess) {
    child.stdout!.on('data', (chunk: Buffer) => {
      this.buffer += chunk.toString()
      const lines = this.buffer.split('\n')
      this.buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (line.startsWith('CALL ')) this.calls.push(JSON.parse(line.slice(5)))
      }
    })
    child.stderr!.on('data', (chunk: Buffer) => { this.stderr += chunk.toString() })
  }

  // Все запросы к Telegram с таким методом (sendMessage, getUpdates).
  telegram(method: string): Call[] {
    return this.calls.filter((call) => call.url === `https://api.telegram.org/bot${BOT_TOKEN}/${method}`)
  }

  // Все запросы к backend с таким путём.
  backend(path: string): Call[] {
    return this.calls.filter((call) => call.url === 'http://backend.test' + path)
  }

  async waitFor(condition: () => boolean, what: string, timeoutMs = 5000): Promise<void> {
    const started = Date.now()
    while (!condition()) {
      if (Date.now() - started > timeoutMs) {
        throw new Error(`Timed out waiting for: ${what}\nCalls so far: ${JSON.stringify(this.calls, null, 2)}\n${this.stderr}`)
      }
      await new Promise((resolve) => setTimeout(resolve, 20))
    }
  }

  // Останавливаем бота так же, как это делает Docker: сигналом SIGTERM.
  async stop(): Promise<void> {
    if (this.child.exitCode !== null) return
    const exited = new Promise<void>((resolve) => this.child.once('exit', () => resolve()))
    this.child.kill('SIGTERM')
    await exited
  }
}

// Запускает настоящий src/index.js с подменённой сетью (fake-network.js).
export function startBot(scenario: object): RunningBot {
  const index = fileURLToPath(new URL('../../src/index.js', import.meta.url))
  const fakeNetwork = new URL('./fake-network.js', import.meta.url).href
  const child = spawn(process.execPath, ['--import', fakeNetwork, index], {
    env: {
      ...process.env, // на Windows Node нужны системные переменные (SystemRoot и др.)
      TELEGRAM_BOT_KEY: BOT_KEY_BYTES.toString('base64url'),
      TELEGRAM_BACKEND_URL: 'http://backend.test/', // со слэшем в конце: бот должен его убрать
      TELEGRAM_SERVICE_TOKEN: SERVICE_TOKEN,
      TELEGRAM_BOT_TOKEN: BOT_TOKEN,
      FAKE_SCENARIO: JSON.stringify(scenario),
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  return new RunningBot(child)
}

// Расшифровка конверта так, как это делает backend.
export function decryptEnvelope(key: Buffer, envelope: string, aad = 'mint-market:telegram:redeem:v1'): unknown {
  const raw = Buffer.from(envelope, 'base64url')
  const decipher = createDecipheriv('aes-256-gcm', key, raw.subarray(0, 12))
  decipher.setAAD(Buffer.from(aad))
  decipher.setAuthTag(raw.subarray(-16))
  const plaintext = Buffer.concat([decipher.update(raw.subarray(12, -16)), decipher.final()])
  return JSON.parse(plaintext.toString('utf8'))
}
