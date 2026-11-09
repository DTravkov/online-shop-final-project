import { useEffect, useState } from 'react'
import { apiGet, apiPost, apiPut, apiPatch, formatDate, formatPrice, getErrorMessage } from '../api.js'
import { getProductVisual } from '../helpers.js'
import { Button, Icon, PageLoading, PageTitle, Status } from '../components/Common.jsx'

// История покупок или заказы продавца.
export default function OrdersPage({ token, role, showToast }) {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [busyOrder, setBusyOrder] = useState(null)
  const [error, setError] = useState('')

  // Загрузить список заказов.
  async function loadOrders() {
    setLoading(true)
    setError('')

    let path = '/customer/orders'
    if (role === 'seller') {
      path = '/seller/orders'
    }

    try {
      const result = await apiGet(path, token)
      setOrders(result)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setLoading(false)
  }

  useEffect(() => {
    loadOrders()
  }, [token, role])

  // Покупатель оплачивает заказ или отменяет его.
  async function customerAction(orderId, action) {
    setBusyOrder(orderId)
    setError('')

    try {
      await apiPost('/customer/orders/' + orderId + '/' + action, {}, token)
      await loadOrders()

      if (action === 'pay') {
        showToast('Заказ оплачен')
      } else {
        showToast('Заказ отменён')
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusyOrder(null)
  }

  async function rateSeller(orderId, sellerId, rating) {
    setBusyOrder(orderId)
    setError('')

    try {
      await apiPut('/customer/orders/' + orderId + '/seller-ratings/' + sellerId, { rating }, token)
      await loadOrders()
      showToast('Оценка сохранена')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusyOrder(null)
  }

  // Продавец меняет статус заказа.
  async function sellerAction(orderId, nextStatus) {
    setBusyOrder(orderId)
    setError('')

    try {
      await apiPatch('/seller/orders/' + orderId + '/status', {
        order_status: nextStatus,
      }, token)

      await loadOrders()
      showToast('Статус заказа обновлён')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setBusyOrder(null)
  }

  if (loading) {
    return <PageLoading label="Загружаем заказы…" />
  }

  let title = 'Мои заказы'
  let subtitle = 'Все ваши покупки собраны в одном месте.'
  let eyebrow = 'ВАША ИСТОРИЯ'

  if (role === 'seller') {
    title = 'Заказы покупателей'
    subtitle = 'Следите за заказами и обновляйте их статус.'
    eyebrow = 'РАБОТА МАГАЗИНА'
  }

  return (
    <section className="workspace-page">
      <PageTitle eyebrow={eyebrow} title={title} subtitle={subtitle} />
      {error ? <div className="inline-error">{error}</div> : null}

      {orders.length === 0 ? (
        <div className="empty-state empty-large">
          <div className="empty-icon"><Icon name="box" /></div>
          <h3>Заказов пока нет</h3>
          <p>{role === 'seller' ? 'Когда покупатели оформят заказ, он появится здесь.' : 'Оформленные покупки появятся здесь.'}</p>
        </div>
      ) : (
        <div className="orders-list">
          {orders.map((order) => {
            const sellersInOrder = [...new Map(order.items.map((item) => [item.seller_id, {
              sellerId: item.seller_id,
              storeName: item.store_name,
            }])).values()]
            const ratingsBySeller = Object.fromEntries(
              (order.seller_ratings || []).map((rating) => [rating.seller_id, rating.rating]),
            )
            let customerName = 'Покупатель'
            if (order.customer_name) {
              customerName = order.customer_name
            }

            let canPay = false
            if (order.payment_status === 'pending') {
              if (order.order_status !== 'cancelled') {
                canPay = true
              }
            }

            let canCancel = false
            if (order.order_status === 'new') {
              canCancel = true
            }

            let canMarkDelivered = false
            if (order.order_status === 'new') {
              canMarkDelivered = true
            }
            if (order.order_status === 'shipped') {
              canMarkDelivered = true
            }

            return (
            <article className="order-card panel-card" key={order.order_id}>
              <div className="order-top">
                <div>
                  <p className="eyebrow">ЗАКАЗ №{order.order_id}</p>
                  <span className="order-date">{formatDate(order.order_date)}</span>
                </div>
                <div className="order-statuses">
                  <Status value={order.order_status} />
                  <Status value={order.payment_status} />
                </div>
              </div>

              {role === 'seller' ? (
                <div className="order-customer">
                  <span>Покупатель</span>
                  <strong>{customerName}</strong>
                </div>
              ) : null}

              <div className="order-product-list">
                {order.items.map((item) => {
                  const visual = getProductVisual(item.product_name)

                  return (
                    <div className="order-product" key={item.order_item_id}>
                      <div className={'order-product-icon ' + visual.className}>{visual.icon}</div>
                      <div>
                        <strong>{item.product_name}</strong>
                        <small>{item.store_name} · {item.quantity} шт. × {formatPrice(item.unit_price)}</small>
                      </div>
                      <b>{formatPrice(item.subtotal)}</b>
                    </div>
                  )
                })}
              </div>

              {role === 'customer' && order.order_status === 'delivered' ? (
                <div className="order-rating-list">
                  {sellersInOrder.map((seller) => {
                    const currentRating = ratingsBySeller[seller.sellerId] || 0

                    return (
                      <div className="order-rating" key={seller.sellerId}>
                        <div>
                          <strong>{seller.storeName}</strong>
                          <span>{currentRating ? `Ваша оценка: ${currentRating} из 5` : 'Оцените магазин'}</span>
                        </div>
                        <div className="rating-stars" role="group" aria-label={`Оценка магазина ${seller.storeName}`}>
                          {[1, 2, 3, 4, 5].map((rating) => (
                            <button
                              type="button"
                              key={rating}
                              className={rating <= currentRating ? 'selected' : ''}
                              aria-pressed={rating === currentRating}
                              aria-label={`${rating} из 5`}
                              title={`${rating} из 5`}
                              disabled={busyOrder === order.order_id}
                              onClick={() => rateSeller(order.order_id, seller.sellerId, rating)}
                            >
                              ★
                            </button>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : null}

              <div className="order-bottom">
                <div>
                  <span>{role === 'seller' ? 'Сумма товаров магазина' : 'Сумма заказа'}</span>
                  <strong>{formatPrice(role === 'seller' ? order.seller_total : order.total_amount)}</strong>
                </div>

                {role === 'customer' ? (
                  <div className="order-actions">
                    {canPay ? (
                      <Button variant="soft" onClick={() => customerAction(order.order_id, 'pay')} disabled={busyOrder === order.order_id}>Оплатить</Button>
                    ) : null}
                    {canCancel ? (
                      <Button variant="outline" onClick={() => customerAction(order.order_id, 'cancel')} disabled={busyOrder === order.order_id}>Отменить</Button>
                    ) : null}
                  </div>
                ) : (
                  <div className="order-actions">
                    {order.order_status === 'new' ? (
                      <Button variant="soft" onClick={() => sellerAction(order.order_id, 'shipped')} disabled={busyOrder === order.order_id}>Отправить</Button>
                    ) : null}
                    {canMarkDelivered ? (
                      <Button variant="outline" onClick={() => sellerAction(order.order_id, 'delivered')} disabled={busyOrder === order.order_id}>Доставлен</Button>
                    ) : null}
                  </div>
                )}
              </div>

              {order.delivery_address ? (
                <p className="order-address"><Icon name="truck" /> {order.delivery_address}</p>
              ) : null}
              </article>
              )
            })}
        </div>
      )}
    </section>
  )
}
