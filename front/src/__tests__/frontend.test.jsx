// QA: 10 frontend-тестов (Vitest + React Testing Library + jsdom).
// Настоящий backend не нужен: запросы fetch заменены "фейковым API" (mockApi).
// Запуск (из папки front/):  npm test

import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import App from '../App.jsx'
import { apiDelete, apiGet, apiPost, formatDate, formatPrice, getErrorMessage } from '../api.js'
import { getProductVisual, getStatusName } from '../helpers.js'
import CartPage from '../pages/CartPage.jsx'
import OrdersPage from '../pages/OrdersPage.jsx'

// ---------------------------------------------------------------------------
// Помощники
// ---------------------------------------------------------------------------

// Подменяет fetch. routes: { 'GET /catalog/products': ответ или функция(body, url) }.
// Ответ можно дать как объект (200) или как { status, body }.
function mockApi(routes) {
  const fetchMock = vi.fn(async (url, options = {}) => {
    const method = options.method || 'GET'
    const path = new URL(url, 'http://localhost').pathname.replace(/^\/api/, '')
    const handler = routes[`${method} ${path}`]

    if (handler === undefined) {
      return new Response(JSON.stringify({ detail: `no mock for ${method} ${path}` }), { status: 404 })
    }

    const body = options.body ? JSON.parse(options.body) : undefined
    const result = typeof handler === 'function' ? handler(body, url) : handler

    if (result && result.status) {
      return new Response(result.body === undefined ? null : JSON.stringify(result.body), { status: result.status })
    }
    return new Response(JSON.stringify(result), { status: 200 })
  })

  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

// Список вызовов fetch в удобном виде.
function calls(fetchMock) {
  return fetchMock.mock.calls.map(([url, options = {}]) => {
    const parsed = new URL(url, 'http://localhost')
    return {
      method: options.method || 'GET',
      path: parsed.pathname.replace(/^\/api/, ''),
      params: parsed.searchParams,
      body: options.body ? JSON.parse(options.body) : undefined,
      headers: options.headers || {},
    }
  })
}

const headphones = {
  product_id: 1, product_name: 'Беспроводные наушники', price: '15000.00',
  stock_quantity: 5, store_name: 'Mint Store', seller_rating: '4.5',
}
const mug = {
  product_id: 2, product_name: 'Кружка', price: '2500.00',
  stock_quantity: 0, store_name: 'Cup Shop', seller_rating: '3.0',
}

const customerSession = {
  access_token: 'tok123', token_type: 'bearer', account_id: 1,
  role: 'customer', customer_id: 1, seller_id: null,
}

const emptyCart = { items: [], total_quantity: 0, total_amount: '0.00', can_checkout: false }

// ---------------------------------------------------------------------------
// FT-01  helpers.js: цена, дата, статусы, значки товаров
// ---------------------------------------------------------------------------
describe('FT-01 helpers', () => {
  it('formats prices, dates, statuses and product icons', () => {
    // Цена в тенге, с копейками (2 знака) и разделителем тысяч
    // (знак валюты зависит от Node/браузера: ₸ или KZT, поэтому принимаем оба)
    expect(formatPrice('15000').replace(/\s/g, ' ')).toMatch(/^15 000,00 (₸|KZT)$/)
    expect(formatPrice('1234.56').replace(/\s/g, ' ')).toMatch(/^1 234,56 (₸|KZT)$/)

    // Пустая дата не ломает страницу
    expect(formatDate(null)).toBe('—')

    // Статусы переводятся, неизвестный статус остаётся как есть
    expect(getStatusName('paid')).toBe('Оплачен')
    expect(getStatusName('cancelled')).toBe('Отменён')
    expect(getStatusName('something_new')).toBe('something_new')

    // Значок по названию: без учёта регистра, запасной вариант "Находка"
    expect(getProductVisual('Беспроводные наушники').tag).toBe('Аудио')
    expect(getProductVisual('НОУТБУК Pro').tag).toBe('Техника')
    expect(getProductVisual('Кружка').tag).toBe('Находка')
    expect(getProductVisual(null).tag).toBe('Находка')
  })
})

// ---------------------------------------------------------------------------
// FT-02  api.js: как формируется запрос (адрес, метод, JSON, токен)
// ---------------------------------------------------------------------------
describe('FT-02 api request format', () => {
  it('builds URL, method, JSON body and Bearer token correctly', async () => {
    const fetchMock = mockApi({
      'GET /ping': { ok: true },
      'POST /items': { ok: true },
      'DELETE /items/1': { status: 204 },
    })

    await apiGet('/ping', 'tok')
    await apiPost('/items', { a: 1 })
    const deleted = await apiDelete('/items/1', 'tok')

    const [get, post, del] = fetchMock.mock.calls

    // GET: префикс /api, токен есть, тела и Content-Type нет
    expect(get[0]).toBe('/api/ping')
    expect(get[1].method).toBe('GET')
    expect(get[1].headers.Authorization).toBe('Bearer tok')
    expect(get[1].body).toBeUndefined()
    expect(get[1].headers['Content-Type']).toBeUndefined()

    // POST без токена: есть JSON, нет Authorization
    expect(post[1].method).toBe('POST')
    expect(post[1].headers['Content-Type']).toBe('application/json')
    expect(post[1].body).toBe('{"a":1}')
    expect(post[1].headers.Authorization).toBeUndefined()

    // DELETE: ответ 204 превращается в null
    expect(del[1].method).toBe('DELETE')
    expect(deleted).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// FT-03  api.js: тексты ошибок, которые видит пользователь
// ---------------------------------------------------------------------------
describe('FT-03 api error messages', () => {
  it('turns backend errors into readable messages', async () => {
    // detail-строка
    mockApi({ 'GET /a': { status: 400, body: { detail: 'Not enough stock' } } })
    await expect(apiGet('/a')).rejects.toThrow('Not enough stock')

    // ошибки валидации (массив) склеиваются через "; "
    mockApi({ 'GET /b': { status: 422, body: { detail: [{ msg: 'Field required' }, { msg: 'Too short' }] } } })
    await expect(apiGet('/b')).rejects.toThrow('Field required; Too short')

    // ответ без JSON: общее сообщение с кодом
    mockApi({ 'GET /c': { status: 500 } })
    await expect(apiGet('/c')).rejects.toThrow('Ошибка запроса. Код: 500')

    // если ошибки нет, показываем запасной текст
    expect(getErrorMessage(null)).toBe('Что-то пошло не так. Попробуйте ещё раз.')
  })
})

// ---------------------------------------------------------------------------
// FT-04  Каталог: товары показываются, нет в наличии нельзя купить
// ---------------------------------------------------------------------------
describe('FT-04 catalog page', () => {
  it('shows products and blocks "add to cart" for out-of-stock items', async () => {
    mockApi({ 'GET /catalog/products': [headphones, mug] })
    render(<App />)

    expect(await screen.findByText('Беспроводные наушники')).toBeInTheDocument()
    expect(screen.getByText('Кружка')).toBeInTheDocument()
    expect(screen.getByText(/^15 000,00 (₸|KZT)$/)).toBeInTheDocument()
    expect(screen.getByText('В наличии · 5 шт.')).toBeInTheDocument()
    expect(screen.getByText('Нет в наличии')).toBeInTheDocument()

    const addButtons = screen.getAllByTitle('Добавить в корзину')
    expect(addButtons[0]).toBeEnabled()   // наушники
    expect(addButtons[1]).toBeDisabled()  // кружка (остаток 0)
  })
})

// ---------------------------------------------------------------------------
// FT-05  Каталог: поиск, фильтр и сортировка уходят на backend
// ---------------------------------------------------------------------------
describe('FT-05 catalog search, filter and sort', () => {
  it('sends the right query parameters to the API', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi({ 'GET /catalog/products': [headphones] })
    render(<App />)
    await screen.findByText('Беспроводные наушники')

    // Первая загрузка: значения по умолчанию
    const first = calls(fetchMock).find((c) => c.path === '/catalog/products')
    expect(first.params.get('sort')).toBe('id')
    expect(first.params.get('limit')).toBe('48')
    expect(first.params.get('in_stock')).toBe('false')
    expect(first.params.has('search')).toBe(false)

    // Поиск
    await user.type(screen.getByPlaceholderText('Что будем искать сегодня?'), '  наушники ')
    await user.click(screen.getByRole('button', { name: 'Найти' }))
    await waitFor(() => {
      const last = calls(fetchMock).filter((c) => c.path === '/catalog/products').at(-1)
      expect(last.params.get('search')).toBe('наушники') // пробелы по краям обрезаны
    })

    // Фильтр "только в наличии"
    await user.click(screen.getByLabelText('Только в наличии'))
    await waitFor(() => {
      const last = calls(fetchMock).filter((c) => c.path === '/catalog/products').at(-1)
      expect(last.params.get('in_stock')).toBe('true')
    })

    // Сортировка
    await user.selectOptions(screen.getByRole('combobox'), 'price_asc')
    await waitFor(() => {
      const last = calls(fetchMock).filter((c) => c.path === '/catalog/products').at(-1)
      expect(last.params.get('sort')).toBe('price_asc')
    })
  })
})

// ---------------------------------------------------------------------------
// FT-06  Гость не может добавить товар в корзину
// ---------------------------------------------------------------------------
describe('FT-06 guest adds to cart', () => {
  it('opens the login window and does not call the cart API', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi({ 'GET /catalog/products': [headphones] })
    render(<App />)
    await screen.findByText('Беспроводные наушники')

    await user.click(screen.getByTitle('Добавить в корзину'))

    expect(await screen.findByText('С возвращением')).toBeInTheDocument()
    expect(screen.getByText('Войдите или зарегистрируйтесь, чтобы добавить товар')).toBeInTheDocument()
    expect(calls(fetchMock).some((c) => c.path === '/customer/cart/items')).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// FT-07  Вход: ошибка пароля и успешный вход
// ---------------------------------------------------------------------------
describe('FT-07 login', () => {
  it('shows the server error, then logs in and saves the session', async () => {
    const user = userEvent.setup()
    let attempt = 0
    const fetchMock = mockApi({
      'GET /catalog/products': [headphones],
      'POST /auth/login': () => (++attempt === 1
        ? { status: 401, body: { detail: 'Incorrect email or password.' } }
        : customerSession),
      'GET /auth/me': { account_id: 1, email: 'a@test.local', role: 'customer' },
      'GET /customer/cart': emptyCart,
    })
    render(<App />)
    await screen.findByText('Беспроводные наушники')

    await user.click(screen.getByRole('button', { name: 'Войти' }))
    await user.type(screen.getByLabelText('Электронная почта'), 'a@test.local')
    await user.type(screen.getByLabelText('Пароль'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: /Войти в аккаунт/ }))

    // 1) неверный пароль: окно остаётся, видна ошибка
    expect(await screen.findByText('Incorrect email or password.')).toBeInTheDocument()
    expect(localStorage.getItem('mint-market-session')).toBeNull()

    // 2) повторная попытка: успех
    await user.click(screen.getByRole('button', { name: /Войти в аккаунт/ }))
    expect(await screen.findByText('Вы успешно вошли')).toBeInTheDocument()
    expect(screen.queryByText('С возвращением')).not.toBeInTheDocument() // окно закрылось

    // сессия сохранена, меню покупателя появилось
    expect(JSON.parse(localStorage.getItem('mint-market-session')).access_token).toBe('tok123')
    expect(screen.getByText('Покупатель')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Корзина' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Мои заказы' })).toBeInTheDocument()

    // и токен передаётся в защищённые запросы
    await waitFor(() => {
      const me = calls(fetchMock).find((c) => c.path === '/auth/me')
      expect(me.headers.Authorization).toBe('Bearer tok123')
    })
  })
})

// ---------------------------------------------------------------------------
// FT-08  Регистрация: разные поля для покупателя и продавца
// ---------------------------------------------------------------------------
describe('FT-08 registration form', () => {
  it('shows different fields per role and sends the right payload', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi({
      'GET /catalog/products': [],
      'POST /auth/register/seller': {
        access_token: 'sell-tok', token_type: 'bearer', account_id: 2,
        role: 'seller', customer_id: null, seller_id: 7,
      },
      'GET /auth/me': { account_id: 2, email: 's@test.local', role: 'seller' },
    })
    render(<App />)
    await screen.findByText('Пока ничего не найдено')

    await user.click(screen.getByRole('button', { name: 'Войти' }))
    await user.click(screen.getByRole('button', { name: 'Регистрация' }))

    // По умолчанию: покупатель
    expect(screen.getByLabelText('Ваше имя')).toBeInTheDocument()
    expect(screen.getByLabelText('Адрес доставки')).toBeInTheDocument()
    expect(screen.queryByLabelText('Название магазина')).not.toBeInTheDocument()

    // Продавец: другое имя поля и нет адреса доставки
    await user.click(screen.getByRole('button', { name: /Продавец/ }))
    expect(screen.getByLabelText('Название магазина')).toBeInTheDocument()
    expect(screen.queryByLabelText('Адрес доставки')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Ваше имя')).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Название магазина'), 'Mint Store')
    await user.type(screen.getByLabelText('Электронная почта'), 's@test.local')
    await user.type(screen.getByLabelText('Телефон'), '+77010000000')
    await user.type(screen.getByLabelText('Пароль'), 'password123')

    const modal = document.querySelector('.auth-modal')
    await user.click(within(modal).getByRole('button', { name: /Создать аккаунт/ }))

    expect(await screen.findByText('Добро пожаловать в кабинет продавца')).toBeInTheDocument()

    const register = calls(fetchMock).find((c) => c.path === '/auth/register/seller')
    expect(register.body).toEqual({
      store_name: 'Mint Store',
      email: 's@test.local',
      phone: '+77010000000',
      password: 'password123',
    })
    expect(screen.getByText('Продавец', { selector: 'strong' })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// FT-09  Корзина: кнопки + и −, адрес и оформление заказа
// ---------------------------------------------------------------------------
describe('FT-09 cart page', () => {
  it('respects stock limit, requires an address and sends the order', async () => {
    const user = userEvent.setup()
    const item = (quantity) => ({
      product_id: 1, product_name: 'Наушники', store_name: 'Mint Store',
      unit_price: '15000.00', quantity, stock_quantity: 2, available: true,
      subtotal: String(15000 * quantity) + '.00',
    })
    const cartWith = (quantity) => ({
      items: [item(quantity)], total_quantity: quantity,
      total_amount: String(15000 * quantity) + '.00', can_checkout: true,
    })

    const fetchMock = mockApi({
      'GET /customer/cart': cartWith(2),
      'GET /customer/delivery-address': { delivery_address: '' },
      'GET /wallet': { balance: '50000.00' },
      'PUT /customer/cart/items/1': cartWith(1),
      'POST /customer/orders': { order_id: 42 },
    })
    const onCheckoutComplete = vi.fn()

    render(
      <CartPage token="t" onCheckoutComplete={onCheckoutComplete} onCartChange={vi.fn()}
        showToast={vi.fn()} goToCatalog={vi.fn()} goToWallet={vi.fn()} />,
    )
    await screen.findByText('Наушники')

    const plus = screen.getByRole('button', { name: '+' })
    const minus = screen.getByRole('button', { name: '−' })
    const checkout = screen.getByRole('button', { name: /Оформить заказ/ })

    // Количество = остатку: "+" выключен. Адреса нет: оформить нельзя
    expect(plus).toBeDisabled()
    expect(minus).toBeEnabled()
    expect(checkout).toBeDisabled()

    // Уменьшаем до 1: уходит PUT, "−" выключается, "+" включается
    await user.click(minus)
    await waitFor(() => expect(screen.getByRole('button', { name: '−' })).toBeDisabled())
    expect(screen.getByRole('button', { name: '+' })).toBeEnabled()
    expect(calls(fetchMock).find((c) => c.method === 'PUT').body).toEqual({ quantity: 1 })

    // Вводим адрес, отмечаем "оплатить с баланса", оформляем
    await user.type(screen.getByPlaceholderText('Укажите адрес доставки'), '  Almaty, Abay 1 ')
    await user.click(screen.getByLabelText(/Оплатить с баланса сейчас/))
    expect(checkout).toBeEnabled()
    await user.click(checkout)

    await waitFor(() => expect(onCheckoutComplete).toHaveBeenCalledWith({ order_id: 42 }))
    const order = calls(fetchMock).find((c) => c.path === '/customer/orders')
    expect(order.body).toEqual({ payment_status: 'paid', delivery_address: 'Almaty, Abay 1' })
  })
})

// ---------------------------------------------------------------------------
// FT-10  Заказы: какие кнопки доступны при каком статусе
// ---------------------------------------------------------------------------
describe('FT-10 orders page', () => {
  it('shows Pay/Cancel only when allowed and calls the API on click', async () => {
    const user = userEvent.setup()
    const order = (id, order_status, payment_status) => ({
      order_id: id, order_status, payment_status, order_date: '2026-11-01T10:00:00Z',
      total_amount: '15000.00', delivery_address: 'Almaty, Abay 1',
      items: [{
        order_item_id: id, product_name: 'Наушники', store_name: 'Mint Store',
        quantity: 1, unit_price: '15000.00', subtotal: '15000.00',
      }],
    })

    const fetchMock = mockApi({
      'GET /customer/orders': [
        order(1, 'new', 'pending'),
        order(2, 'cancelled', 'pending'),
        order(3, 'delivered', 'paid'),
      ],
      'POST /customer/orders/1/pay': { order_id: 1 },
    })
    const showToast = vi.fn()
    const onBalanceChanged = vi.fn()

    render(<OrdersPage token="t" role="customer" showToast={showToast} onBalanceChanged={onBalanceChanged} />)
    await screen.findByText('ЗАКАЗ №1')

    const card = (id) => screen.getByText(`ЗАКАЗ №${id}`).closest('article')

    // Новый и неоплаченный: можно оплатить и отменить
    expect(within(card(1)).getByRole('button', { name: 'Оплатить' })).toBeInTheDocument()
    expect(within(card(1)).getByRole('button', { name: 'Отменить' })).toBeInTheDocument()

    // Отменённый: ни оплатить, ни отменить
    expect(within(card(2)).queryByRole('button', { name: 'Оплатить' })).not.toBeInTheDocument()
    expect(within(card(2)).queryByRole('button', { name: 'Отменить' })).not.toBeInTheDocument()
    expect(within(card(2)).getByText('Отменён')).toBeInTheDocument()

    // Доставленный и оплаченный: кнопок нет
    expect(within(card(3)).queryByRole('button')).not.toBeInTheDocument()

    // Клик "Оплатить": POST на нужный адрес, список перезагружается, есть уведомление
    await user.click(within(card(1)).getByRole('button', { name: 'Оплатить' }))
    await waitFor(() => expect(showToast).toHaveBeenCalledWith('Заказ оплачен'))
    expect(onBalanceChanged).toHaveBeenCalled() // после оплаты баланс обновляется

    const all = calls(fetchMock)
    expect(all.some((c) => c.method === 'POST' && c.path === '/customer/orders/1/pay')).toBe(true)
    expect(all.filter((c) => c.method === 'GET' && c.path === '/customer/orders')).toHaveLength(2)
  })
})
