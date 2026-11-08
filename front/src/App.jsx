import { useEffect, useState } from 'react'
import { apiGet, apiPost, getErrorMessage } from './api.js'
import { Button, Icon } from './components/Common.jsx'
import AuthModal from './pages/AuthModal.jsx'
import CatalogPage, { ProductModal } from './pages/CatalogPage.jsx'
import CartPage from './pages/CartPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import SellerPage from './pages/SellerPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'

const SESSION_KEY = 'mint-market-session'

// Получить сохранённую сессию пользователя.
function readSession() {
  try {
    const savedSession = localStorage.getItem(SESSION_KEY)

    if (savedSession) {
      return JSON.parse(savedSession)
    }
  } catch (error) {
    return null
  }

  return null
}

// Сохранить сессию после входа или удалить её после выхода.
function saveSession(session) {
  if (session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  } else {
    localStorage.removeItem(SESSION_KEY)
  }
}

let toastTimer = null

// Главный компонент всего сайта.
export default function App() {
  const [session, setSession] = useState(readSession)
  const [page, setPage] = useState('catalog')

  const [authOpen, setAuthOpen] = useState(false)
  const [authNextPage, setAuthNextPage] = useState('catalog')

  const [products, setProducts] = useState([])
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState('')

  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('id')
  const [inStock, setInStock] = useState(false)

  const [selectedProduct, setSelectedProduct] = useState(null)
  const [busyProduct, setBusyProduct] = useState(null)
  const [cartCount, setCartCount] = useState(0)
  const [toast, setToast] = useState('')

  let role = null
  if (session) {
    role = session.role
  }

  // Показать короткое сообщение пользователю.
  function showToast(message) {
    setToast(message)
    window.clearTimeout(toastTimer)

    toastTimer = window.setTimeout(() => {
      setToast('')
    }, 2800)
  }

  // Загрузить товары из Backend.
  async function loadCatalog() {
    setCatalogLoading(true)
    setCatalogError('')

    const params = new URLSearchParams()
    params.set('sort', sort)
    params.set('offset', '0')
    params.set('limit', '48')
    params.set('in_stock', String(inStock))

    if (query.trim()) {
      params.set('search', query.trim())
    }

    try {
      const result = await apiGet('/catalog/products?' + params.toString())
      setProducts(result)
    } catch (requestError) {
      setCatalogError(getErrorMessage(requestError))
    }

    setCatalogLoading(false)
  }

  // Загружать товары при изменении поиска, сортировки или фильтра.
  useEffect(() => {
    loadCatalog()
  }, [sort, inStock, query])

  // Проверить сохранённый вход и получить количество товаров в корзине.
  useEffect(() => {
    if (!session) {
      setCartCount(0)
      return
    }

    let pageIsOpen = true

    async function checkSession() {
      try {
        await apiGet('/auth/me', session.access_token)

        if (session.role === 'customer') {
          const cart = await apiGet('/customer/cart', session.access_token)

          if (pageIsOpen) {
            setCartCount(cart.total_quantity)
          }
        }
      } catch (error) {
        if (pageIsOpen) {
          setSession(null)
          saveSession(null)
          setPage('catalog')
        }
      }
    }

    checkSession()

    return function stopCheck() {
      pageIsOpen = false
    }
  }, [session])

  // Открыть окно входа или регистрации.
  function openAuth(nextPage) {
    let pageAfterLogin = 'catalog'

    if (nextPage) {
      pageAfterLogin = nextPage
    }

    setAuthNextPage(pageAfterLogin)
    setAuthOpen(true)
  }

  // Перейти на другую страницу сайта.
  function navigate(nextPage) {
    // Все страницы кроме каталога требуют входа.
    if (nextPage !== 'catalog') {
      if (!session) {
        openAuth(nextPage)
        return
      }
    }

    // Корзина доступна только покупателю.
    if (nextPage === 'cart') {
      if (role !== 'customer') {
        showToast('Корзина доступна в аккаунте покупателя')
        return
      }
    }

    // Кабинет магазина доступен только продавцу.
    if (nextPage === 'seller') {
      if (role !== 'seller') {
        showToast('Этот раздел доступен продавцам')
        return
      }
    }

    // Заказы доступны покупателю и продавцу.
    if (nextPage === 'orders') {
      if (role !== 'seller') {
        if (role !== 'customer') {
          showToast('Для просмотра заказов войдите как покупатель или продавец')
          return
        }
      }
    }

    setPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Сохранить сессию после успешного входа или регистрации.
  function completeAuth(authData) {
    setSession(authData)
    saveSession(authData)
    setAuthOpen(false)
    setPage(authNextPage)

    if (authData.role === 'seller') {
      showToast('Добро пожаловать в кабинет продавца')
    } else {
      showToast('Вы успешно вошли')
    }
  }

  // Добавить товар в корзину покупателя.
  async function addToCart(productId) {
    if (!session) {
      openAuth('catalog')
      showToast('Войдите или зарегистрируйтесь, чтобы добавить товар')
      return
    }

    if (role !== 'customer') {
      showToast('Добавлять товары в корзину может аккаунт покупателя')
      return
    }

    setBusyProduct(productId)

    try {
      const cart = await apiPost('/customer/cart/items', {
        product_id: productId,
        quantity: 1,
      }, session.access_token)

      setCartCount(cart.total_quantity)
      showToast('Товар добавлен в корзину')
      setSelectedProduct(null)
    } catch (requestError) {
      showToast(getErrorMessage(requestError))
    }

    setBusyProduct(null)
  }

  // Открыть подробную карточку товара.
  async function openProduct(productId) {
    try {
      const product = await apiGet('/catalog/products/' + productId)
      setSelectedProduct(product)
    } catch (requestError) {
      showToast(getErrorMessage(requestError))
    }
  }

  // Действия после оформления заказа.
  function checkoutComplete(order) {
    setPage('orders')
    setCartCount(0)
    loadCatalog()
    showToast('Заказ №' + order.order_id + ' успешно оформлен')
  }

  // Выйти из аккаунта.
  function logout() {
    setSession(null)
    saveSession(null)
    setPage('catalog')
    setCartCount(0)
    showToast('Вы вышли из аккаунта')
  }

  // Показываем разные пункты меню для разных ролей.
  let navItems = [
    { id: 'catalog', label: 'Каталог' },
  ]

  if (role === 'customer') {
    navItems.push({ id: 'cart', label: 'Корзина', count: cartCount })
    navItems.push({ id: 'orders', label: 'Мои заказы' })
  }

  if (role === 'seller') {
    navItems.push({ id: 'seller', label: 'Мой магазин' })
    navItems.push({ id: 'orders', label: 'Заказы' })
  }

  return (
    <div className="app-shell">
      <div className="announcement">
        <span>Место для уникальных находок</span>
        <span className="announcement-dot" />
        <span>Поддерживайте независимые магазины</span>
      </div>

      <header className="site-header">
        <div className="header-main">
          <button className="brand" onClick={() => navigate('catalog')}>
            <span className="brand-mark">m</span>
            <span>mint<span className="brand-light">market</span><small>ПЛОЩАДКА ХОРОШИХ НАХОДОК</small></span>
          </button>

          <form className="header-search" onSubmit={(event) => {
            event.preventDefault()
            setQuery(search)
            navigate('catalog')
          }}>
            <Icon name="search" />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Найти что-то особенное…" />
            <kbd>↵</kbd>
          </form>

          <div className="header-actions">
            {session ? (
              <>
                <button className="header-user" onClick={() => navigate('profile')}>
                  <span className="user-avatar">{role === 'seller' ? 'S' : 'M'}</span>
                  <span>
                    <small>Вы вошли как</small>
                    <strong>{role === 'seller' ? 'Продавец' : role === 'admin' ? 'Администратор' : 'Покупатель'}</strong>
                  </span>
                </button>
                <button className="header-icon-button" onClick={logout} title="Выйти"><Icon name="logout" /></button>
              </>
            ) : (
              <>
                <button className="login-link" onClick={() => openAuth('catalog')}>Войти</button>
                <Button onClick={() => openAuth('catalog')}>Создать аккаунт <Icon name="arrow" /></Button>
              </>
            )}
          </div>
        </div>

        <div className="header-nav">
          <nav>
            {navItems.map((item) => (
              <button key={item.id} className={page === item.id ? 'active' : ''} onClick={() => navigate(item.id)}>
                {item.label}
                {item.count > 0 ? <span className="nav-count">{item.count}</span> : null}
              </button>
            ))}
          </nav>
          <div className="nav-caption"><span className="online-dot" /> Открыто для покупок</div>
        </div>
      </header>

      <main className="main-content">
        {page === 'catalog' ? (
          <CatalogPage
            products={products}
            loading={catalogLoading}
            error={catalogError}
            search={search}
            setSearch={setSearch}
            sort={sort}
            setSort={setSort}
            inStock={inStock}
            setInStock={setInStock}
            onSearch={(event) => {
              event.preventDefault()
              setQuery(search)
            }}
            onOpen={openProduct}
            onAdd={addToCart}
            busyProduct={busyProduct}
          />
        ) : null}

        {page === 'cart' ? (
          session ? (
            role === 'customer' ? <CartPage
            token={session.access_token}
            onCheckoutComplete={checkoutComplete}
            onCartChange={setCartCount}
            showToast={showToast}
            goToCatalog={() => navigate('catalog')}
          /> : null
          ) : null
        ) : null}

        {page === 'orders' ? (
          session ? <OrdersPage token={session.access_token} role={role} showToast={showToast} /> : null
        ) : null}

        {page === 'seller' ? (
          session ? (
            role === 'seller' ? <SellerPage
            token={session.access_token}
            onCatalogChanged={loadCatalog}
            showToast={showToast}
          /> : null
          ) : null
        ) : null}

        {page === 'profile' ? (
          session ? <ProfilePage token={session.access_token} role={role} showToast={showToast} /> : null
        ) : null}

        {page !== 'catalog' ? (
          !session ? (
            <div className="empty-state">
              <h3>Необходимо войти в аккаунт</h3>
              <Button onClick={() => openAuth(page)}>Войти</Button>
            </div>
          ) : null
        ) : null}
      </main>

      <footer className="site-footer">
        <div className="footer-brand">
          <span className="brand-mark">m</span>
          <div><strong>mint market</strong><small>Хорошие вещи находят своих людей.</small></div>
        </div>
        <span>© 2026 Mint Market</span>
        <span>Сделано с заботой о покупках</span>
      </footer>

      {authOpen ? (
        <AuthModal onClose={() => setAuthOpen(false)} onSuccess={completeAuth} />
      ) : null}

      <ProductModal
        product={selectedProduct}
        onClose={() => setSelectedProduct(null)}
        onAdd={addToCart}
        busy={busyProduct === (selectedProduct ? selectedProduct.product_id : null)}
      />

      {toast ? (
        <div className="toast"><span><Icon name="check" /></span>{toast}</div>
      ) : null}
    </div>
  )
}
