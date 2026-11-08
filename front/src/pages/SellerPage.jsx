import { useEffect, useState } from 'react'
import { apiGet, apiPost, apiPatch, formatDate, formatPrice, getErrorMessage } from '../api.js'
import { getProductVisual } from '../helpers.js'
import { Button, Field, Icon, ModalFrame, PageLoading, Status } from '../components/Common.jsx'

// Форма добавления или изменения товара.
function ProductForm({ product, onClose, onSave, busy }) {
  let startName = ''
  let startPrice = ''
  let startStock = 1

  if (product) {
    startName = product.product_name
    startPrice = product.price
    startStock = product.stock_quantity
  }

  const [name, setName] = useState(startName)
  const [price, setPrice] = useState(startPrice)
  const [stock, setStock] = useState(startStock)

  function submit(event) {
    event.preventDefault()

    const productData = {
      product_name: name.trim(),
      price: Number(price),
      stock_quantity: Number(stock),
    }

    onSave(productData)
  }

  return (
    <ModalFrame onClose={onClose}>
      <p className="eyebrow">КАТАЛОГ МАГАЗИНА</p>
      <h2>{product ? 'Редактировать товар' : 'Новый товар'}</h2>

      <form className="form-stack" onSubmit={submit}>
        <Field label="Название товара" value={name} onChange={(event) => setName(event.target.value)} required maxLength={150} placeholder="Например, Настольная лампа" />
        <Field label="Цена, ₸" type="number" min="0" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} required />
        <Field label="Количество на складе" type="number" min="0" step="1" value={stock} onChange={(event) => setStock(event.target.value)} required />

        <div className="modal-actions">
          <Button variant="outline" onClick={onClose}>Отмена</Button>
          <Button type="submit" disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить товар'}</Button>
        </div>
      </form>
    </ModalFrame>
  )
}

// Форма изменения профиля магазина.
function StoreProfileForm({ profile, onClose, onSave, busy }) {
  const [storeName, setStoreName] = useState(profile.store_name)
  const [email, setEmail] = useState(profile.email)
  const [phone, setPhone] = useState(profile.phone)

  function submit(event) {
    event.preventDefault()

    onSave({
      store_name: storeName.trim(),
      email: email.trim(),
      phone: phone.trim(),
    })
  }

  return (
    <ModalFrame onClose={onClose}>
      <p className="eyebrow">НАСТРОЙКИ</p>
      <h2>Профиль магазина</h2>

      <form className="form-stack" onSubmit={submit}>
        <Field label="Название магазина" value={storeName} onChange={(event) => setStoreName(event.target.value)} required maxLength={100} />
        <Field label="Электронная почта" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={100} />
        <Field label="Телефон" value={phone} onChange={(event) => setPhone(event.target.value)} required maxLength={20} />
        <p className="form-hint">Рейтинг магазина рассчитывается системой и не редактируется вручную.</p>

        <div className="modal-actions">
          <Button variant="outline" onClick={onClose}>Отмена</Button>
          <Button type="submit" disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить'}</Button>
        </div>
      </form>
    </ModalFrame>
  )
}

// Кабинет продавца.
export default function SellerPage({ token, onCatalogChanged, showToast }) {
  const [tab, setTab] = useState('products')
  const [products, setProducts] = useState([])
  const [profile, setProfile] = useState(null)
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modalType, setModalType] = useState('')
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [busy, setBusy] = useState(false)

  // Загрузить товары, профиль магазина и заказы продавца.
  async function loadSellerData() {
    setLoading(true)
    setError('')

    try {
      const productData = await apiGet('/seller/products?include_inactive=true', token)
      const profileData = await apiGet('/seller/profile', token)
      const orderData = await apiGet('/seller/orders', token)

      setProducts(productData)
      setProfile(profileData)
      setOrders(orderData)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setLoading(false)
  }

  useEffect(() => {
    loadSellerData()
  }, [token])

  // Открыть форму для нового товара.
  function addNewProduct() {
    setSelectedProduct(null)
    setModalType('product')
  }

  // Открыть форму для изменения товара.
  function editProduct(product) {
    setSelectedProduct(product)
    setModalType('product')
  }

  // Сохранить новый товар или изменения товара.
  async function saveProduct(productData) {
    setBusy(true)
    setError('')

    try {
      if (selectedProduct) {
        await apiPatch('/seller/products/' + selectedProduct.product_id, productData, token)
      } else {
        await apiPost('/seller/products', productData, token)
      }

      await loadSellerData()
      onCatalogChanged()
      setModalType('')

      if (selectedProduct) {
        showToast('Товар обновлён')
      } else {
        showToast('Товар добавлен в магазин')
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusy(false)
  }

  // Снять товар с продажи или снова опубликовать его.
  async function changeProductStatus(product) {
    setBusy(true)
    setError('')

    try {
      await apiPatch('/seller/products/' + product.product_id, {
        is_active: !product.is_active,
      }, token)

      await loadSellerData()
      onCatalogChanged()

      if (product.is_active) {
        showToast('Товар снят с продажи')
      } else {
        showToast('Товар снова опубликован')
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusy(false)
  }

  // Сохранить настройки магазина.
  async function saveStoreProfile(profileData) {
    setBusy(true)
    setError('')

    try {
      const updatedProfile = await apiPatch('/seller/profile', profileData, token)
      setProfile(updatedProfile)
      setModalType('')
      showToast('Профиль магазина сохранён')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusy(false)
  }

  // Изменить статус заказа.
  async function changeOrderStatus(orderId, nextStatus) {
    setBusy(true)
    setError('')

    try {
      await apiPatch('/seller/orders/' + orderId + '/status', {
        order_status: nextStatus,
      }, token)

      await loadSellerData()
      showToast('Статус заказа обновлён')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusy(false)
  }

  if (loading) {
    return <PageLoading label="Открываем кабинет продавца…" />
  }

  let activeCount = 0
  for (let i = 0; i < products.length; i++) {
    if (products[i].is_active) {
      activeCount = activeCount + 1
    }
  }

  let storeName = 'Мой магазин'
  let rating = 0

  if (profile) {
    storeName = profile.store_name
    rating = Number(profile.rating).toFixed(1)
  }

  return (
    <section className="workspace-page seller-workspace">
      <div className="seller-banner">
        <div>
          <p className="eyebrow">ПРОСТРАНСТВО ПРОДАВЦА</p>
          <h1>{storeName}<span>.</span></h1>
          <p>Ваш магазин — ваши правила. Управляйте товарами и заказами в одном месте.</p>
        </div>
        <button className="seller-profile-button" onClick={() => setModalType('profile')}>
          <Icon name="edit" /> Настроить магазин
        </button>
        <div className="seller-banner-mark">m.</div>
      </div>

      <div className="seller-stats">
        <div className="stat-card"><span>Всего товаров</span><strong>{products.length}</strong><small>В каталоге магазина</small></div>
        <div className="stat-card"><span>Активные товары</span><strong>{activeCount}</strong><small>Доступны покупателям</small></div>
        <div className="stat-card"><span>Заказы</span><strong>{orders.length}</strong><small>В последних записях</small></div>
        <div className="stat-card"><span>Рейтинг</span><strong>★ {rating}</strong><small>Оценка покупателей</small></div>
      </div>

      {error ? <div className="inline-error">{error}</div> : null}

      <div className="workspace-tabs">
        <button className={tab === 'products' ? 'active' : ''} onClick={() => setTab('products')}>Мои товары <span>{products.length}</span></button>
        <button className={tab === 'orders' ? 'active' : ''} onClick={() => setTab('orders')}>Заказы <span>{orders.length}</span></button>
      </div>

      {tab === 'products' ? (
        <div className="seller-product-section">
          <div className="section-heading compact-heading">
            <div>
              <h2>Каталог магазина<span>.</span></h2>
              <p className="section-subtitle">Добавляйте товары, меняйте цену и остатки.</p>
            </div>
            <Button onClick={addNewProduct}><Icon name="plus" /> Добавить товар</Button>
          </div>

          {products.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><Icon name="box" /></div>
              <h3>Здесь пока пусто</h3>
              <p>Добавьте первый товар, чтобы начать продавать.</p>
              <Button onClick={addNewProduct}>Добавить товар <Icon name="plus" /></Button>
            </div>
          ) : (
            <div className="seller-product-list">
              {products.map((product) => {
                const visual = getProductVisual(product.product_name)
                let rowClass = 'seller-product-row panel-card'
                let statusClass = 'status status-good'
                let statusText = 'Активен'

                if (!product.is_active) {
                  rowClass = rowClass + ' inactive-row'
                  statusClass = 'status status-muted'
                  statusText = 'Снят с продажи'
                }

                return (
                  <div className={rowClass} key={product.product_id}>
                    <div className={'seller-product-thumb ' + visual.className}>{visual.icon}</div>
                    <div className="seller-product-main">
                      <strong>{product.product_name}</strong>
                      <span>Артикул #{product.product_id} · {product.stock_quantity} шт. на складе</span>
                    </div>
                    <div className="seller-product-price">{formatPrice(product.price)}</div>
                    <span className={statusClass}>{statusText}</span>
                    <div className="seller-product-actions">
                      <button className="icon-action" onClick={() => editProduct(product)} title="Редактировать"><Icon name="edit" /></button>
                      <button className="text-action" onClick={() => changeProductStatus(product)} disabled={busy}>
                        {product.is_active ? 'Снять с продажи' : 'Опубликовать'}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ) : (
        <div className="seller-order-section">
          {orders.length === 0 ? (
            <div className="empty-state"><h3>Заказов пока нет</h3><p>Новые заказы покупателей появятся здесь.</p></div>
          ) : null}

          {orders.map((order) => (
            <article className="order-card panel-card" key={order.order_id}>
              <div className="order-top">
                <div>
                  <p className="eyebrow">ЗАКАЗ №{order.order_id}</p>
                  <span className="order-date">{formatDate(order.order_date)} · {order.customer_name}</span>
                </div>
                <div className="order-statuses"><Status value={order.order_status} /><Status value={order.payment_status} /></div>
              </div>

              <div className="order-product-list">
                {order.items.map((item) => {
                  const visual = getProductVisual(item.product_name)

                  return (
                    <div className="order-product" key={item.order_item_id}>
                      <div className={'order-product-icon ' + visual.className}>{visual.icon}</div>
                      <div>
                        <strong>{item.product_name}</strong>
                        <small>{item.quantity} шт. × {formatPrice(item.unit_price)}</small>
                      </div>
                      <b>{formatPrice(item.subtotal)}</b>
                    </div>
                  )
                })}
              </div>

              <div className="order-bottom">
                <div><span>К выплате за товары</span><strong>{formatPrice(order.seller_total)}</strong></div>
                <div className="order-actions">
                  {order.order_status === 'new' ? (
                    <Button variant="soft" onClick={() => changeOrderStatus(order.order_id, 'shipped')} disabled={busy}>Отправить</Button>
                  ) : null}
                  {order.order_status === 'new' ? (
                    <Button variant="outline" onClick={() => changeOrderStatus(order.order_id, 'delivered')} disabled={busy}>Доставлен</Button>
                  ) : null}
                  {order.order_status === 'shipped' ? (
                    <Button variant="outline" onClick={() => changeOrderStatus(order.order_id, 'delivered')} disabled={busy}>Доставлен</Button>
                  ) : null}
                </div>
              </div>

              {order.delivery_address ? <p className="order-address"><Icon name="truck" /> {order.delivery_address}</p> : null}
            </article>
          ))}
        </div>
      )}

      {modalType === 'product' ? (
        <ProductForm product={selectedProduct} onClose={() => setModalType('')} onSave={saveProduct} busy={busy} />
      ) : null}

      {modalType === 'profile' ? (
        profile ? <StoreProfileForm profile={profile} onClose={() => setModalType('')} onSave={saveStoreProfile} busy={busy} /> : null
      ) : null}
    </section>
  )
}
