// Этот файл работает ВНУТРИ процесса бота (его подключает `node --import`).
// Он подменяет fetch: вместо настоящего Telegram и настоящего backend отвечает "фейк".
// Каждый запрос бота печатается в stdout строкой "CALL {...}", чтобы тест мог его прочитать.

interface Scenario {
  updates?: unknown[]                              // что вернёт Telegram на первый getUpdates
  redeem?: { status: number, body?: object }       // ответ backend на /telegram/bot/redeem
  job?: object                                     // задача уведомления для /jobs/claim
  send?: { status: number, body: object }          // ответ Telegram на sendMessage
}

const scenario: Scenario = JSON.parse(process.env.FAKE_SCENARIO ?? '{}')
let updatesServed = false
let jobServed = false

function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status })
}

// Запрос "зависает", пока бота не остановят (так ведёт себя настоящий long polling).
function hang(signal?: AbortSignal | null): Promise<Response> {
  return new Promise((_resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason)
    signal?.addEventListener('abort', () => reject(signal.reason), { once: true })
  })
}

globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
  const url = String(input)
  const body = init?.body ? JSON.parse(String(init.body)) : undefined
  const authorization = new Headers(init?.headers).get('authorization')
  process.stdout.write('CALL ' + JSON.stringify({ url, body, authorization }) + '\n')

  if (url.startsWith('https://api.telegram.org/bot')) {
    const method = url.split('/').pop()
    if (method === 'getUpdates') {
      if (updatesServed) return hang(init?.signal)
      updatesServed = true
      return reply(200, { ok: true, result: scenario.updates ?? [] })
    }
    if (method === 'sendMessage') {
      return scenario.send ? reply(scenario.send.status, scenario.send.body) : reply(200, { ok: true, result: {} })
    }
  }

  if (url.startsWith('http://backend.test/')) {
    const path = url.slice('http://backend.test'.length)
    if (path === '/telegram/bot/redeem') {
      const redeem = scenario.redeem ?? { status: 200, body: { code: '123456' } }
      return reply(redeem.status, redeem.body)
    }
    if (path === '/telegram/bot/jobs/claim') {
      if (scenario.job && !jobServed) {
        jobServed = true
        return reply(200, scenario.job)
      }
      return reply(204)
    }
    if (/^\/telegram\/bot\/jobs\/\d+\/result$/.test(path)) return reply(204)
  }

  return reply(404, { detail: 'no fake for ' + url })
}) as typeof fetch
