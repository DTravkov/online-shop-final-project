import { t } from '../i18n.js'
import { useEffect, useState } from 'react'
import { apiGet, apiPost, apiPut, apiDelete, formatPrice, getErrorMessage } from '../api.js'
import { getProductVisual } from '../helpers.js'
import { Button, Icon, PageLoading, PageTitle } from '../components/Common.jsx'

// Корзина покупателя.
export default function CartPage({ token, onCheckoutComplete, onCartChange, showToast, goToCatalog, goToWallet }) {
  const [cart, setCart] = useState(null)
  const [address, setAddress] = useState('')
  const [payNow, setPayNow] = useState(false)
  const [balance, setBalance] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // Загрузить корзину и адрес покупателя.
  async function loadCart() {
    setLoading(true)
    setError('')

    try {
      const cartData = await apiGet('/customer/cart', token)
      const addressData = await apiGet('/customer/delivery-address', token)
      const wallet = await apiGet('/wallet', token)
      setBalance(wallet.balance)

      setCart(cartData)

      let savedAddress = ''
      if (addressData.delivery_address) {
        savedAddress = addressData.delivery_address
      }
      setAddress(savedAddress)
      onCartChange(cartData.total_quantity)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setLoading(false)
  }

  useEffect(() => {
    loadCart()
  }, [token])

  // Изменить количество товара в корзине.
  async function changeQuantity(productId, newQuantity) {
    if (newQuantity < 1) {
      return
    }

    setBusy(true)
    setError('')

    try {
      const updatedCart = await apiPut('/customer/cart/items/' + productId, {
        quantity: newQuantity,
      }, token)

      setCart(updatedCart)
      onCartChange(updatedCart.total_quantity)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusy(false)
  }

  // Удалить товар из корзины.
  async function removeItem(productId) {
    setBusy(true)
    setError('')

    try {
      const updatedCart = await apiDelete('/customer/cart/items/' + productId, token)
      setCart(updatedCart)
      onCartChange(updatedCart.total_quantity)
      showToast(t('Товар удалён из корзины'))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusy(false)
  }

  // Создать заказ из товаров в корзине.
  async function checkout() {
    setBusy(true)
    setError('')

    const orderData = {
      payment_status: 'pending',
    }

    if (address.trim()) {
      orderData.delivery_address = address.trim()
    }

    if (payNow) {
      orderData.payment_status = 'paid'
    }

    try {
      const order = await apiPost('/customer/orders', orderData, token)
      onCheckoutComplete(order)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusy(false)
  }

  if (loading) {
    return <PageLoading label={t('Загружаем вашу корзину…')} />
  }

  let items = []
  if (cart !== null) {
    if (cart.items) {
      items = cart.items
    }
  }

  let checkoutDisabled = false
  if (busy) {
    checkoutDisabled = true
  }
  if (cart === null) {
    checkoutDisabled = true
  } else {
    if (!cart.can_checkout) {
      checkoutDisabled = true
    }
  }
  if (!address.trim()) {
    checkoutDisabled = true
  }

  return (
    <section className="workspace-page">
      <PageTitle eyebrow={t("ВАШИ ПОКУПКИ")} title={t('Корзина')} subtitle={t('Проверьте товары и подготовьте заказ.')} />

      {error ? <div className="inline-error">{error}</div> : null}

      {items.length === 0 ? (
        <div className="empty-state empty-large">
          <div className="empty-icon"><Icon name="bag" /></div>
          <h3>{t('Корзина пока пуста')}</h3>
          <p>{t('Самое время найти что-нибудь особенное.')}</p>
          <Button onClick={goToCatalog}>{t('Перейти в каталог')} <Icon name="arrow" /></Button>
        </div>
      ) : (
        <div className="cart-layout">
          <div className="cart-items panel-card">
            <div className="panel-heading">
              <h3>{t('Ваши товары')}</h3>
              <span>{cart.total_quantity} {t("шт.")}</span>
            </div>

            {items.map((item) => {
              const visual = getProductVisual(item.product_name)

              let minusDisabled = false
              if (busy) {
                minusDisabled = true
              }
              if (item.quantity <= 1) {
                minusDisabled = true
              }

              let plusDisabled = false
              if (busy) {
                plusDisabled = true
              }
              if (item.quantity >= item.stock_quantity) {
                plusDisabled = true
              }

              return (
                <div className="cart-item" key={item.product_id}>
                  <div className={'cart-thumb ' + visual.className}>{visual.icon}</div>

                  <div className="cart-item-main">
                    <strong>{item.product_name}</strong>
                    <small>{item.store_name} · {formatPrice(item.unit_price)}</small>
                    {!item.available ? <em>{t('Недостаточно товара на складе')}</em> : null}
                    <button className="text-action remove-action" onClick={() => removeItem(item.product_id)} disabled={busy}>{t('Удалить')}</button>
                  </div>

                  <div className="quantity-control">
                    <button onClick={() => changeQuantity(item.product_id, item.quantity - 1)} disabled={minusDisabled}>
                      <Icon name="minus" />
                    </button>
                    <span>{item.quantity}</span>
                    <button onClick={() => changeQuantity(item.product_id, item.quantity + 1)} disabled={plusDisabled}>
                      <Icon name="plus" />
                    </button>
                  </div>

                  <strong className="cart-subtotal">{formatPrice(item.subtotal)}</strong>
                </div>
              )
            })}
          </div>

          <aside className="checkout-card panel-card">
            <p className="eyebrow">{t('ИТОГО')}</p>
            <div className="checkout-total">{formatPrice(cart.total_amount)}</div>
            <div className="checkout-line">
              <span>{t("Товары")} ({cart.total_quantity})</span>
              <strong>{formatPrice(cart.total_amount)}</strong>
            </div>
            <div className="checkout-line"><span>{t('Доставка')}</span><strong>{t('Уточняется')}</strong></div>
            <div className="checkout-divider" />

            <label className="field">
              <span>{t('Адрес доставки')}</span>
              <textarea value={address} onChange={(event) => setAddress(event.target.value)} rows={3} placeholder={t('Укажите адрес доставки')} />
            </label>

            <label className="check-row">
              <input type="checkbox" checked={payNow} onChange={(event) => setPayNow(event.target.checked)} />
              <span>{t('Оплатить с баланса сейчас')}</span>
            </label>

            {payNow && balance !== null && Number(balance) < Number(cart.total_amount) ?
              <p className="checkout-hint">{t('Для оплаты не хватает средств. Пополните баланс или оформите заказ с оплатой позже.')}</p> : null}

            <Button className="full-width" onClick={checkout} disabled={checkoutDisabled}>
              {busy ? t('Оформляем…') : t('Оформить заказ')} <Icon name="arrow" />
            </Button>

            {!cart.can_checkout ? (
              <p className="checkout-hint">{t('Некоторые товары недоступны в указанном количестве. Измените корзину, чтобы продолжить.')}</p>
            ) : null}

            <p className="checkout-note">{t("На балансе: ")} {balance === null ? '…' : formatPrice(balance)}. {t("Если оплатить позже, заказ появится в разделе «Мои заказы».")}</p>
            <button className="text-action" onClick={goToWallet}>{t('Пополнить баланс →')}</button>
          </aside>
        </div>
      )}
    </section>
  )
}
