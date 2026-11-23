import { useEffect, useState } from 'react'
import { apiGet, apiPost, formatPrice, getErrorMessage } from './api.js'
import { Button, Icon } from './components/Common.jsx'
import AuthModal from './pages/AuthModal.jsx'
import CatalogPage from './pages/CatalogPage.jsx'
import CartPage from './pages/CartPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import SellerPage from './pages/SellerPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import ShopPage from './pages/ShopPage.jsx'
import WalletPage from './pages/WalletPage.jsx'
import ProductPage from './pages/ProductPage.jsx'
import { getLanguage, setLanguage, t } from './i18n.js'

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

function readLocation() {
  const productMatch = window.location.hash.match(/^#\/products\/([1-9]\d*)$/)
  if (productMatch) return { page: 'product', productId: Number(productMatch[1]), sellerId: null }
  const match = window.location.hash.match(/^#\/shops\/([1-9]\d*)$/)
  if (match) return { page: 'shop', sellerId: Number(match[1]), productId: null }
  const page = window.location.hash.slice(1)
  return { page: ['cart', 'orders', 'seller', 'profile', 'wallet'].includes(page) ? page : 'catalog', sellerId: null, productId: null }
}

let toastTimer = null

// Главный компонент всего сайта.
export default function App() {
  const [session, setSession] = useState(readSession)
  const [page, setPage] = useState(() => readLocation().page)
  const [shopId, setShopId] = useState(() => readLocation().sellerId)
  const [productId, setProductId] = useState(() => readLocation().productId)
  const [language, setLanguageState] = useState(getLanguage)

  const [authOpen, setAuthOpen] = useState(false)
  const [authNextPage, setAuthNextPage] = useState('catalog')

  const [products, setProducts] = useState([])
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState('')

  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('id')
  const [inStock, setInStock] = useState(false)

  const [busyProduct, setBusyProduct] = useState(null)
  const [cartCount, setCartCount] = useState(0)
  const [balance, setBalance] = useState(null)
  const [toast, setToast] = useState('')

  let role = null
  if (session) {
    role = session.role
  }

  useEffect(() => {
    function followLocation() {
      const location = readLocation()
      setPage(location.page)
      setShopId(location.sellerId)
      setProductId(location.productId)
    }
    window.addEventListener('hashchange', followLocation)
    window.addEventListener('popstate', followLocation)
    return () => {
      window.removeEventListener('hashchange', followLocation)
      window.removeEventListener('popstate', followLocation)
    }
  }, [])

  // Изменить язык интерфейса.
  function changeLanguage(nextLanguage) {
    setLanguage(nextLanguage)
    setLanguageState(nextLanguage)
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

  async function refreshBalance() {
    if (!session) return
    try {
      const wallet = await apiGet('/wallet', session.access_token)
      setBalance(wallet.balance)
    } catch (error) {
      setBalance(null)
    }
  }

  useEffect(() => {
    if (!session) {
      setBalance(null)
      return
    }
    let active = true
    function loadBalance() {
      apiGet('/wallet', session.access_token).then((wallet) => {
        if (active) setBalance(wallet.balance)
      }).catch(() => {
        if (active) setBalance(null)
      })
    }
    loadBalance()
    window.addEventListener('focus', loadBalance)
    return () => { active = false; window.removeEventListener('focus', loadBalance) }
  }, [session, page])

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
    if (nextPage !== 'catalog' && nextPage !== 'shop') {
      if (!session) {
        openAuth(nextPage)
        return
      }
    }

    // Корзина доступна только покупателю.
    if (nextPage === 'cart') {
      if (role !== 'customer') {
        showToast(t('Корзина доступна в аккаунте покупателя'))
        return
      }
    }

    // Кабинет магазина доступен только продавцу.
    if (nextPage === 'seller') {
      if (role !== 'seller') {
        showToast(t('Этот раздел доступен продавцам'))
        return
      }
    }

    // Заказы доступны покупателю и продавцу.
    if (nextPage === 'orders') {
      if (role !== 'seller') {
        if (role !== 'customer') {
          showToast(t('Для просмотра заказов войдите как покупатель или продавец'))
          return
        }
      }
    }

    setPage(nextPage)
    window.history.pushState(null, '', '#' + nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Сохранить сессию после успешного входа или регистрации.
  function completeAuth(authData) {
    setSession(authData)
    saveSession(authData)
    setAuthOpen(false)
    setPage(authNextPage)
    if (authNextPage === 'product' && productId) {
      window.history.pushState(null, '', '#/products/' + productId)
    } else if (authNextPage !== 'shop') {
      window.history.pushState(null, '', '#' + authNextPage)
    }

    if (authData.role === 'seller') {
      showToast(t('Добро пожаловать в кабинет продавца'))
    } else {
      showToast(t('Вы успешно вошли'))
    }
  }

  // Добавить товар в корзину покупателя.
  async function addToCart(productId) {
    if (!session) {
      openAuth(page === 'shop' ? 'shop' : page === 'product' ? 'product' : 'catalog')
      showToast(t('Войдите или зарегистрируйтесь, чтобы добавить товар'))
      return
    }

    if (role !== 'customer') {
      showToast(t('Добавлять товары в корзину может аккаунт покупателя'))
      return
    }

    setBusyProduct(productId)

    try {
      const cart = await apiPost('/customer/cart/items', {
        product_id: productId,
        quantity: 1,
      }, session.access_token)

      setCartCount(cart.total_quantity)
      showToast(t('Товар добавлен в корзину'))
    } catch (requestError) {
      showToast(getErrorMessage(requestError))
    }

    setBusyProduct(null)
  }

  // Открыть подробную карточку товара.
  async function openProduct(nextProductId) {
    setProductId(nextProductId)
    setPage('product')
    window.history.pushState(null, '', '#/products/' + nextProductId)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Действия после оформления заказа.
  function checkoutComplete(order) {
    refreshBalance()
    setPage('orders')
    window.history.pushState(null, '', '#orders')
    setCartCount(0)
    loadCatalog()
    showToast(t('Заказ №') + order.order_id + ' ' + t('успешно оформлен'))
  }

  // Выйти из аккаунта.
  function logout() {
    setSession(null)
    saveSession(null)
    setPage('catalog')
    window.history.pushState(null, '', '#catalog')
    setCartCount(0)
    showToast(t('Вы вышли из аккаунта'))
  }

  // Показываем разные пункты меню для разных ролей.
  let navItems = [
    { id: 'catalog', label: t('Каталог') },
  ]

  if (role === 'customer') {
    navItems.push({ id: 'cart', label: t('Корзина'), count: cartCount })
    navItems.push({ id: 'orders', label: t('Мои заказы') })
  }

  if (role === 'seller') {
    navItems.push({ id: 'seller', label: t('Мой магазин') })
    navItems.push({ id: 'orders', label: t('Заказы') })
  }

  if (session) navItems.push({ id: 'wallet', label: t('Баланс') })

  return (
    <div className="app-shell">
      <div className="announcement">
        <span>{t('Место для уникальных находок')}</span>
        <span className="announcement-dot" />
        <span>{t('Поддерживайте независимые магазины')}</span>
      </div>

      <header className="site-header">
        <div className="header-main">
          <button className="brand" onClick={() => navigate('catalog')}>
            <span className="brand-mark">m</span>
            <span>mint<span className="brand-light">market</span><small>{t("Площадка хороших находок")}</small></span>
          </button>

          <form className="header-search" onSubmit={(event) => {
            event.preventDefault()
            setQuery(search)
            navigate('catalog')
          }}>
            <Icon name="search" />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("Найти что-то особенное…")} />
            <kbd>↵</kbd>
          </form>

          <div className="header-actions">
            <label className="language-picker" aria-label={t('Язык')}>
              <span>{t('Язык')}</span>
              <select value={language} onChange={(event) => changeLanguage(event.target.value)}>
                <option value="ru">RU</option>
                <option value="en">EN</option>
                <option value="kk">ҚАЗ</option>
              </select>
            </label>
            {session ? (
              <>
                <button className="header-user" onClick={() => navigate(role === 'admin' ? 'wallet' : 'profile')}>
                  <span className="user-avatar">{role === 'seller' ? 'S' : 'M'}</span>
                  <span>
                    <small>{t("Вы вошли как")}</small>
                    <strong>{role === 'seller' ? t('Продавец') : role === 'admin' ? t('Администратор') : t('Покупатель')}</strong>
                  </span>
                </button>
                <button className="header-icon-button" onClick={logout} title={t("Выйти")}><Icon name="logout" /></button>
              </>
            ) : (
              <>
                <button className="login-link" onClick={() => openAuth(page === 'shop' ? 'shop' : page === 'product' ? 'product' : 'catalog')}>{t("Войти")}</button>
                <Button onClick={() => openAuth(page === 'shop' ? 'shop' : page === 'product' ? 'product' : 'catalog')}>{t("Создать аккаунт")} <Icon name="arrow" /></Button>
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
          {session ? <button className="header-balance" onClick={() => navigate('wallet')}>{t("Баланс")}: {balance === null ? '…' : formatPrice(balance)}</button>
            : <div className="nav-caption"><span className="online-dot" /> {t("Открыто для покупок")}</div>}
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

        {page === 'product' && productId ? <ProductPage productId={productId} session={session} onAdd={addToCart} busyProduct={busyProduct} showToast={showToast} /> : null}

        {page === 'shop' && shopId ? <ShopPage key={shopId} sellerId={shopId} session={session}
          onOpen={openProduct} onAdd={addToCart} busyProduct={busyProduct} showToast={showToast}
          onReviewsChanged={loadCatalog} /> : null}

        {page === 'cart' ? (
          session ? (
            role === 'customer' ? <CartPage
            token={session.access_token}
            onCheckoutComplete={checkoutComplete}
            onCartChange={setCartCount}
            goToWallet={() => navigate('wallet')}
            showToast={showToast}
            goToCatalog={() => navigate('catalog')}
          /> : null
          ) : null
        ) : null}

        {page === 'orders' ? (
          session ? <OrdersPage token={session.access_token} role={role} showToast={showToast} onBalanceChanged={refreshBalance} /> : null
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

        {page === 'wallet' && session ? <WalletPage token={session.access_token} showToast={showToast} onBalanceChange={setBalance} /> : null}

        {page === 'profile' ? (
          session ? <ProfilePage token={session.access_token} role={role} showToast={showToast} /> : null
        ) : null}

        {page !== 'catalog' && page !== 'shop' && page !== 'product' ? (
          !session ? (
            <div className="empty-state">
              <h3>{t("Необходимо войти в аккаунт")}</h3>
              <Button onClick={() => openAuth(page)}>{t('Войти')}</Button>
            </div>
          ) : null
        ) : null}
      </main>

      <footer className="site-footer">
        <div className="footer-brand">
          <span className="brand-mark">m</span>
          <div><strong>mint market</strong><small>{t("Хорошие вещи находят своих людей.")}</small></div>
        </div>
        <span>© 2026 Mint Market</span>
        <span>{t("Сделано с заботой о покупках")}</span>
      </footer>

      {authOpen ? (
        <AuthModal onClose={() => setAuthOpen(false)} onSuccess={completeAuth} />
      ) : null}


      {toast ? (
        <div className="toast"><span><Icon name="check" /></span>{toast}</div>
      ) : null}
    </div>
  )
}
