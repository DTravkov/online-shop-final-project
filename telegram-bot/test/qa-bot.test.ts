// QA: 10 дополнительных тестов Telegram-бота (встроенный node:test, без новых библиотек).
// BT-01 … BT-06: проверяют отдельные модули (крипто, тексты, клиенты API).
// BT-07 … BT-10: запускают настоящего бота (src/index.ts) с "фейковым" Telegram и backend.
// Запуск (из папки telegram-bot/):  npm test

import assert from 'node:assert/strict'
import { randomBytes } from 'node:crypto'
import { afterEach, mock, test } from 'node:test'

import { ApiError, Backend, Telegram, type Job } from '../src/api.js'
import { decodeBotKey, encryptRedemption } from '../src/crypto.js'
import { deliveryFailure, notificationText } from '../src/notifications.js'
import { BOT_KEY_BYTES, BOT_TOKEN, SERVICE_TOKEN, decryptEnvelope, startBot } from './telegram-bot-tests/telegram-bot/test/helpers/run-bot.js'

afterEach(() => mock.restoreAll())

const json = (status: number, body?: unknown) => new Response(body === undefined ? null : JSON.stringify(body), { status })

// Подменяет fetch и запоминает, с чем его вызвали.
function stubFetch(handler: (url: string, init: RequestInit) => Response) {
  return mock.method(globalThis, 'fetch', async (url: string | URL | Request, init?: RequestInit) => handler(String(url), init ?? {}))
}

const PAYLOAD = 'A'.repeat(59) // ссылка привязки: ровно 59 символов

// ---------------------------------------------------------------------------
// BT-01  Ключ бота: что принимается, а что нет
// ---------------------------------------------------------------------------
test('BT-01 bot key must be exactly 32 bytes in clean base64url', () => {
  const good = randomBytes(32)
  assert.deepEqual(decodeBotKey(good.toString('base64url')), good)

  const bad: Record<string, string> = {
    'пустая строка': '',
    '31 байт': randomBytes(31).toString('base64url'),
    '33 байта': randomBytes(33).toString('base64url'),
    'с символом = на конце': good.toString('base64'),
    'обычный base64 с + и /': Buffer.alloc(32, 0xfb).toString('base64').replace(/=+$/, ''),
    'с пробелом в конце': good.toString('base64url') + ' ',
    'с переводом строки': good.toString('base64url') + '\n',
  }
  for (const [name, value] of Object.entries(bad)) {
    assert.throws(() => decodeBotKey(value), /TELEGRAM_BOT_KEY/, `должен отклонить: ${name}`)
  }
})

// ---------------------------------------------------------------------------
// BT-02  Шифрование ссылки привязки: защита от подделки
// ---------------------------------------------------------------------------
test('BT-02 encrypted envelope cannot be read or changed without the right key', () => {
  const key = BOT_KEY_BYTES
  const envelope = encryptRedemption(key, PAYLOAD, 555)

  // Контроль: с правильным ключом всё расшифровывается
  assert.deepEqual(decryptEnvelope(key, envelope), { start: PAYLOAD, chat_id: '555' })

  // Чужой ключ
  assert.throws(() => decryptEnvelope(Buffer.alloc(32, 1), envelope))

  // Один изменённый байт шифртекста (GCM замечает подмену)
  const raw = Buffer.from(envelope, 'base64url')
  raw[20] ^= 1
  assert.throws(() => decryptEnvelope(key, raw.toString('base64url')))

  // Неверный контекст (AAD): конверт нельзя использовать для другой цели
  assert.throws(() => decryptEnvelope(key, envelope, 'another-context'))

  // Открытый текст не виден внутри конверта
  assert.equal(Buffer.from(envelope, 'base64url').includes(Buffer.from(PAYLOAD)), false)

  // Одноразовый номер (nonce) не повторяется
  const nonces = new Set(Array.from({ length: 500 }, () => Buffer.from(encryptRedemption(key, PAYLOAD, 1), 'base64url').subarray(0, 12).toString('hex')))
  assert.equal(nonces.size, 500)
})

// ---------------------------------------------------------------------------
// BT-03  Тексты уведомлений для всех событий backend
// ---------------------------------------------------------------------------
test('BT-03 notification text is correct for every event the backend sends', () => {
  const job = (event: string, order_id = 42): Job =>
    ({ notification_id: 1, lease_id: 'secret-lease', chat_id: '99887766', order_id, event })

  const expected: Record<string, string> = {
    seller_new_order: 'Mint Market · Новый заказ №42.',
    paid: 'Mint Market · Заказ №42 оплачен.',
    cancelled: 'Mint Market · Заказ №42 отменён.',
    shipped: 'Mint Market · Заказ №42 отправлен.',
    partially_shipped: 'Mint Market · Заказ №42 частично отправлен.',
    delivered: 'Mint Market · Заказ №42 доставлен.',
    partially_delivered: 'Mint Market · Заказ №42 частично доставлен.',
  }
  for (const [event, text] of Object.entries(expected)) {
    assert.equal(notificationText(job(event)), text, event)
  }

  // Сообщения о привязке: backend ставит order_id = -1, и "№-1" в тексте быть не должно
  assert.match(notificationText(job('link_success', -1)), /успешно привязан/)
  assert.match(notificationText(job('unlink_success', -1)), /отвязан/)
  assert.doesNotMatch(notificationText(job('link_success', -1)), /-1|№/)
  assert.doesNotMatch(notificationText(job('unlink_success', -1)), /-1|№/)

  // В тексте нет служебных данных (chat_id, lease_id)
  for (const event of [...Object.keys(expected), 'link_success']) {
    const text = notificationText(job(event))
    assert.ok(!text.includes('99887766') && !text.includes('secret-lease'), event)
  }
})

// ---------------------------------------------------------------------------
// BT-04  Что делать с ошибкой доставки: повторить или отказаться
// ---------------------------------------------------------------------------
test('BT-04 delivery failures are classified correctly (retry vs failed)', () => {
  // 429: повтор, ожидание берётся из Telegram, но не больше суток
  assert.deepEqual(deliveryFailure(new ApiError(429, 10)), { outcome: 'retry', retry_after: 10 })
  assert.deepEqual(deliveryFailure(new ApiError(429, 1_000_000)), { outcome: 'retry', retry_after: 86400 })
  assert.deepEqual(deliveryFailure(new ApiError(429)), { outcome: 'retry', retry_after: 0 })

  // 408 (таймаут) и все 5xx: повторяем
  for (const status of [408, 500, 502, 503, 504]) {
    assert.deepEqual(deliveryFailure(new ApiError(status)), { outcome: 'retry' }, String(status))
  }

  // Остальные 4xx: повтор бессмысленен (бот заблокирован, чат не найден)
  for (const status of [400, 401, 403, 404, 422]) {
    assert.deepEqual(deliveryFailure(new ApiError(status)), { outcome: 'failed' }, String(status))
  }

  // Не ApiError (обрыв сети, баг): повторяем
  assert.deepEqual(deliveryFailure(new Error('boom')), { outcome: 'retry' })
  assert.deepEqual(deliveryFailure('строка'), { outcome: 'retry' })
})

// ---------------------------------------------------------------------------
// BT-05  Клиент backend: адреса, токен, тела запросов, ошибки
// ---------------------------------------------------------------------------
test('BT-05 backend client sends correct requests and maps errors', async () => {
  const backend = new Backend('http://backend.test', SERVICE_TOKEN, new AbortController().signal)

  const fetchMock = stubFetch((url) => {
    if (url.endsWith('/redeem')) return json(200, { code: '482910' })
    if (url.endsWith('/claim')) return json(204)
    return json(204)
  })

  assert.deepEqual(await backend.redeem('ENVELOPE'), { code: '482910' })
  assert.ok(!(await backend.claim()), 'пустая очередь: задачи нет')
  const job: Job = { notification_id: 7, lease_id: 'L1', chat_id: '10', order_id: 3, event: 'paid' }
  await backend.report(job, { outcome: 'retry', retry_after: 5 })

  const [redeem, claim, report] = fetchMock.mock.calls.map((c) => ({ url: String(c.arguments[0]), init: c.arguments[1] as RequestInit }))

  assert.equal(redeem.url, 'http://backend.test/telegram/bot/redeem')
  assert.equal(redeem.init.method, 'POST')
  assert.deepEqual(redeem.init.headers, { Authorization: 'Bearer svc-token', 'Content-Type': 'application/json' })
  assert.deepEqual(JSON.parse(String(redeem.init.body)), { envelope: 'ENVELOPE' })

  assert.equal(claim.url, 'http://backend.test/telegram/bot/jobs/claim')
  assert.deepEqual(JSON.parse(String(claim.init.body)), {})

  assert.equal(report.url, 'http://backend.test/telegram/bot/jobs/7/result')
  assert.deepEqual(JSON.parse(String(report.init.body)), { lease_id: 'L1', outcome: 'retry', retry_after: 5 })

  // Ошибки backend превращаются в ApiError с кодом
  for (const status of [400, 409, 500]) {
    stubFetch(() => json(status, { detail: 'x' }))
    await assert.rejects(backend.redeem('E'), (error) => error instanceof ApiError && error.status === status)
    mock.restoreAll()
  }
})

// ---------------------------------------------------------------------------
// BT-06  Клиент Telegram: запросы и разбор ошибок
// ---------------------------------------------------------------------------
test('BT-06 telegram client builds requests and maps error responses', async () => {
  const telegram = new Telegram(BOT_TOKEN, new AbortController().signal)

  const fetchMock = stubFetch((url) => (url.endsWith('/getUpdates')
    ? json(200, { ok: true, result: [{ update_id: 5 }] })
    : json(200, { ok: true, result: {} })))

  assert.deepEqual(await telegram.updates(5), [{ update_id: 5 }])
  await telegram.send(10, 'привет')

  const [updates, send] = fetchMock.mock.calls.map((c) => ({ url: String(c.arguments[0]), init: c.arguments[1] as RequestInit }))
  assert.equal(updates.url, 'https://api.telegram.org/bot123:ABC/getUpdates')
  assert.deepEqual(JSON.parse(String(updates.init.body)), { offset: 5, timeout: 30, allowed_updates: ['message'] })
  assert.equal(send.url, 'https://api.telegram.org/bot123:ABC/sendMessage')
  assert.deepEqual(JSON.parse(String(send.init.body)), { chat_id: 10, text: 'привет' })

  const cases: Array<[string, Response, number, number]> = [
    ['лимит запросов', json(429, { ok: false, error_code: 429, parameters: { retry_after: 17 } }), 429, 17],
    ['бот заблокирован', json(403, { ok: false, error_code: 403 }), 403, 0],
    ['HTTP 200, но ok=false без кода', json(200, { ok: false }), 502, 0],
    ['ответ не JSON', new Response('<html>oops</html>', { status: 500 }), 500, 0],
  ]
  for (const [name, response, status, retryAfter] of cases) {
    stubFetch(() => response)
    await assert.rejects(
      telegram.send(10, 'x'),
      (error) => error instanceof ApiError && error.status === status && error.retryAfter === retryAfter,
      name,
    )
    mock.restoreAll()
  }
})

// ---------------------------------------------------------------------------
// BT-07  Бот: /start со ссылкой привязки (настоящий index.ts, фейковая сеть)
// ---------------------------------------------------------------------------
test('BT-07 /start with a link payload redeems it and replies with the code', async () => {
  const second = 'B'.repeat(59)
  const bot = startBot({
    updates: [
      { update_id: 1, message: { chat: { id: 555, type: 'private' }, text: `/start ${PAYLOAD}` } },
      { update_id: 2, message: { chat: { id: 556, type: 'private' }, text: `/start@MintMarketBot ${second}` } },
    ],
    redeem: { status: 200, body: { code: '482910' } },
  })
  try {
    await bot.waitFor(() => bot.telegram('sendMessage').length === 2, 'two replies')

    // Запрос на backend: правильный адрес (без двойного слэша), токен сервиса, зашифрованный конверт
    const [first, other] = bot.backend('/telegram/bot/redeem')
    assert.equal(first.authorization, 'Bearer svc-token')
    assert.deepEqual(decryptEnvelope(BOT_KEY_BYTES, first.body.envelope), { start: PAYLOAD, chat_id: '555' })
    assert.deepEqual(decryptEnvelope(BOT_KEY_BYTES, other.body.envelope), { start: second, chat_id: '556' })

    // Ответы пользователям (команда с @имя_бота тоже работает)
    const [reply1, reply2] = bot.telegram('sendMessage')
    const text = 'Введите код в профиле Mint Market, чтобы подтвердить подключение Telegram: 482910'
    assert.deepEqual(reply1.body, { chat_id: 555, text })
    assert.deepEqual(reply2.body, { chat_id: 556, text })

    // Бот запомнил, что обработал update_id 1 и 2, и просит новые начиная с 3
    await bot.waitFor(() => bot.telegram('getUpdates').length === 2, 'second poll')
    assert.equal(bot.telegram('getUpdates')[1].body.offset, 3)
  } finally {
    await bot.stop()
  }
})

// ---------------------------------------------------------------------------
// BT-08  Бот: что видит пользователь, если backend ответил ошибкой
// ---------------------------------------------------------------------------
const redeemErrors: Array<[number, string]> = [
  [409, 'Этот чат уже подключён. Отключите его в текущем профиле Mint Market и попробуйте снова.'],
  [400, 'Ссылка истекла или уже использована. Создайте новую ссылку в профиле Mint Market.'],
  [422, 'Ссылка истекла или уже использована. Создайте новую ссылку в профиле Mint Market.'],
  [500, 'Не удалось подключить Telegram. Попробуйте создать новую ссылку в профиле Mint Market.'],
  [403, 'Не удалось подключить Telegram. Попробуйте создать новую ссылку в профиле Mint Market.'],
]
for (const [status, expectedText] of redeemErrors) {
  test(`BT-08 redeem error ${status} gives the right message to the user`, async () => {
    const bot = startBot({
      updates: [{ update_id: 1, message: { chat: { id: 777, type: 'private' }, text: `/start ${PAYLOAD}` } }],
      redeem: { status, body: { detail: 'error' } },
    })
    try {
      await bot.waitFor(() => bot.telegram('sendMessage').length === 1, 'reply')
      assert.deepEqual(bot.telegram('sendMessage')[0].body, { chat_id: 777, text: expectedText })
      assert.equal(bot.telegram('sendMessage').length, 1) // ровно один ответ
    } finally {
      await bot.stop()
    }
  })
}

// ---------------------------------------------------------------------------
// BT-09  Бот: лишние сообщения игнорируются
// ---------------------------------------------------------------------------
test('BT-09 bot ignores groups, non-text, other commands and malformed links', async () => {
  const group = (type: string, id: number, text?: string) =>
    ({ message: { chat: { id, type }, ...(text === undefined ? {} : { text }) } })

  const bot = startBot({
    updates: [
      { update_id: 1, ...group('group', 1, `/start ${PAYLOAD}`) },       // группа
      { update_id: 2, ...group('supergroup', 2, `/start ${PAYLOAD}`) },  // супергруппа
      { update_id: 3, ...group('private', 3) },                          // нет текста (стикер)
      { update_id: 4, ...group('private', 4, 'привет') },                // не команда
      { update_id: 5, ...group('private', 5, '/help') },                 // другая команда
      { update_id: 6, ...group('private', 6, `/start ${'A'.repeat(58)}`) }, // ссылка короче 59
      { update_id: 7, ...group('private', 7, `/start ${'A'.repeat(60)}`) }, // ссылка длиннее 59
      { update_id: 8, ...group('private', 8, `/start ${'A'.repeat(58)}$`) }, // недопустимый символ
      { update_id: 9 },                                                  // нет message вообще
      // Контрольное сообщение: после него точно всё предыдущее обработано
      { update_id: 10, ...group('private', 777, '  /start  ') },
    ],
  })
  try {
    await bot.waitFor(() => bot.telegram('sendMessage').length >= 1, 'control reply')
    await new Promise((resolve) => setTimeout(resolve, 100)) // на случай лишних ответов

    const sent = bot.telegram('sendMessage')
    assert.equal(sent.length, 1, 'ответ только на контрольное сообщение')
    assert.deepEqual(sent[0].body, {
      chat_id: 777,
      text: 'Откройте профиль Mint Market и нажмите «Подключить Telegram».',
    })
    assert.equal(bot.backend('/telegram/bot/redeem').length, 0, 'redeem не вызывался')
  } finally {
    await bot.stop()
  }
})

// ---------------------------------------------------------------------------
// BT-10  Бот: доставка уведомлений и отчёт backend о результате
// ---------------------------------------------------------------------------
const job = { notification_id: 7, lease_id: 'lease-abc', chat_id: '4242', order_id: 42, event: 'shipped' }
const deliveryCases: Array<{ name: string, scenario: object, report: object, sends: number }> = [
  {
    name: 'sent', sends: 1,
    scenario: { job },
    report: { lease_id: 'lease-abc', outcome: 'sent' },
  },
  {
    name: 'user blocked the bot (403) -> failed', sends: 1,
    scenario: { job, send: { status: 403, body: { ok: false, error_code: 403 } } },
    report: { lease_id: 'lease-abc', outcome: 'failed' },
  },
  {
    name: 'Telegram rate limit (429) -> retry with delay', sends: 1,
    scenario: { job, send: { status: 429, body: { ok: false, error_code: 429, parameters: { retry_after: 1 } } } },
    report: { lease_id: 'lease-abc', outcome: 'retry', retry_after: 1 },
  },
  {
    name: 'unknown event -> failed, nothing is sent to the user', sends: 0,
    scenario: { job: { ...job, event: 'unknown_event' } },
    report: { lease_id: 'lease-abc', outcome: 'failed' },
  },
]
for (const item of deliveryCases) {
  test(`BT-10 notification job: ${item.name}`, async () => {
    const bot = startBot(item.scenario)
    try {
      await bot.waitFor(() => bot.backend('/telegram/bot/jobs/7/result').length === 1, 'result report')

      const [claim] = bot.backend('/telegram/bot/jobs/claim')
      assert.equal(claim.authorization, 'Bearer svc-token')

      const sent = bot.telegram('sendMessage')
      assert.equal(sent.length, item.sends)
      if (item.sends) {
        assert.deepEqual(sent[0].body, { chat_id: '4242', text: 'Mint Market · Заказ №42 отправлен.' })
      }

      const report = bot.backend('/telegram/bot/jobs/7/result')[0]
      assert.equal(report.authorization, 'Bearer svc-token')
      assert.deepEqual(report.body, item.report)
    } finally {
      await bot.stop()
    }
  })
}
