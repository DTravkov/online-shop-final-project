import { useEffect, useState } from 'react'
import { apiGet, formatDate, formatPrice, getErrorMessage } from '../api.js'
import { Button, Icon, PageLoading } from '../components/Common.jsx'
import ProductImageCarousel from '../components/ProductImageCarousel.jsx'
import { t } from '../i18n.js'
import { getProductDescription } from '../helpers.js'

// Отдельная страница товара в стиле крупных маркетплейсов.
export default function ProductPage({ productId, session, onAdd, busyProduct, showToast }) {
  const [product, setProduct] = useState(null)
  const [shop, setShop] = useState(null)
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    setProduct(null)
    setShop(null)
    setReviews([])

    async function loadProduct() {
      try {
        const productData = await apiGet('/catalog/products/' + productId)
        if (!active) return
        setProduct(productData)

        // Отзывы в текущем API относятся к магазину продавца, а не к товару.
        const results = await Promise.allSettled([
          apiGet('/catalog/sellers/' + productData.seller_id),
          apiGet('/catalog/sellers/' + productData.seller_id + '/reviews?offset=0&limit=6'),
        ])

        if (!active) return
        if (results[0].status === 'fulfilled') setShop(results[0].value)
        if (results[1].status === 'fulfilled') setReviews(results[1].value)
      } catch (requestError) {
        if (active) setError(getErrorMessage(requestError))
      } finally {
        if (active) setLoading(false)
      }
    }

    loadProduct()
    return () => { active = false }
  }, [productId])

  if (loading) return <PageLoading label={t('Открываем товар…')} />
  if (error || !product) {
    return <div className="empty-state product-not-found" role="alert">
      <h2>{t('Не удалось загрузить товар')}</h2>
      <p>{error || t('Товар не найден')}</p>
      <Button onClick={() => window.location.hash = '#catalog'}>{t('Назад к каталогу')}</Button>
    </div>
  }

  const productHasReviews = Array.isArray(product.reviews)
  const visibleReviews = productHasReviews ? product.reviews : reviews
  const rating = Number(product.rating ?? shop?.rating ?? product.seller_rating ?? 0)
  const reviewCount = product.review_count ?? shop?.review_count ?? visibleReviews.length
  const description = getProductDescription(product)
  const isDemoDescription = !product.description
  const inStock = Number(product.stock_quantity) > 0
  const busy = busyProduct === product.product_id

  return (
    <section className="workspace-page product-page">
      <a className="shop-back" href="#catalog">← {t('Назад к каталогу')}</a>

      <div className="product-detail-layout">
        <div className="product-detail-gallery panel-card">
          <ProductImageCarousel product={product} size="large" />
        </div>

        <div className="product-detail-summary panel-card">
          <p className="eyebrow">{t('КАРТОЧКА ТОВАРА')}</p>
          <h1>{product.product_name}</h1>
          <div className="product-detail-rating">
            <span className="rating-stars">★</span>
            <strong>{rating.toFixed(1)}</strong>
            <a href="#product-shop-reviews">{reviewCount ? `${reviewCount} ${t('Отзывов:').toLowerCase()}` : t('Пока без отзывов')}</a>
          </div>
          <div className="product-detail-price">{formatPrice(product.price)}</div>
          <p className={inStock ? 'product-stock available' : 'product-stock unavailable'}>
            {inStock ? `${t('В наличии')} · ${product.stock_quantity} ${t('шт.')}` : t('Нет в наличии')}
          </p>
          <Button className="product-detail-add" onClick={() => onAdd(product.product_id)} disabled={!inStock || busy}>
            {busy ? t('Подождите…') : t('Добавить в корзину')} <Icon name="bag" />
          </Button>

          <div className="product-seller-panel">
            <div className="product-seller-avatar">{String(product.store_name || 'M').slice(0, 1).toUpperCase()}</div>
            <div className="product-seller-info">
              <small>{t('Продавец')}</small>
              <a href={`#/shops/${product.seller_id}`}>{product.store_name || t('Магазин')}</a>
              <span>★ {rating.toFixed(1)} · {reviewCount} {t('Отзывов:').toLowerCase()}</span>
            </div>
            <a className="product-seller-link" href={`#/shops/${product.seller_id}`}>{t('Смотреть магазин')} →</a>
          </div>
          <div className="product-detail-meta">
            <span>{t('Артикул')}</span><strong>#{product.product_id}</strong>
          </div>
        </div>
      </div>

      <section className="product-description panel-card">
        <p className="eyebrow">{t('ИНФОРМАЦИЯ')}</p>
        <h2>{t('Описание товара')}</h2>
        <p>{isDemoDescription ? t(description) : description}</p>
        {isDemoDescription && <small className="demo-content-note">{t('Описание пока не добавлено.')}</small>}
      </section>

      <section id="product-shop-reviews" className="product-reviews">
        <div className="section-heading">
          <div><p className="eyebrow">{t('ОЦЕНКИ И КОММЕНТАРИИ')}</p><h2>{productHasReviews ? t('Отзывы о товаре') : t('Отзывы покупателей о магазине')}</h2>
            <p className="section-subtitle">{productHasReviews ? t('Отзывы покупателей о товаре.') : t('Рейтинг и отзывы относятся к магазину продавца, а не к отдельному товару.')}</p>
          </div>
          <div className="product-reviews-score"><strong>★ {rating.toFixed(1)}</strong><span>{reviewCount} {t('Отзывов:').toLowerCase()}</span></div>
        </div>
        {visibleReviews.length ? <div className="reviews-list">{visibleReviews.map((review) => (
          <article className="review-card panel-card" key={review.review_id}>
            <div className="review-top"><strong>{review.customer_name}</strong>
              <span className="review-stars" aria-label={`${review.rating} ${t('из 5')}`}>{'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}</span>
            </div>
            <time dateTime={review.created_at}>{formatDate(review.created_at)}</time>
            <p>{review.comment}</p>
          </article>
        ))}</div> : <div className="empty-state product-review-empty"><h3>{t('Отзывов пока нет')}</h3><p>{t('Оставить отзыв можно после завершённой покупки в этом магазине.')}</p></div>}
        {session?.role === 'customer' ? <p className="review-note">{t('Чтобы оставить отзыв, откройте магазин и завершите покупку.')}</p> : null}
      </section>
    </section>
  )
}
