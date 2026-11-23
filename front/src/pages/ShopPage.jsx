import { t } from '../i18n.js'
import { useEffect, useState } from 'react'
import { apiDelete, apiGet, apiPut, formatDate, getErrorMessage } from '../api.js'
import { Button, PageLoading, PageTitle } from '../components/Common.jsx'
import { ProductCard } from './CatalogPage.jsx'

function ReviewForm({ sellerId, token, eligibility, onSaved, showToast }) {
  const [rating, setRating] = useState(eligibility.review?.rating ?? 5)
  const [comment, setComment] = useState(eligibility.review?.comment ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function save(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await apiPut(`/customer/sellers/${sellerId}/review`, { rating: Number(rating), comment: comment.trim() }, token)
      onSaved()
      showToast(t('Спасибо! Ваш отзыв сохранён'))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    setBusy(true)
    setError('')
    try {
      await apiDelete(`/customer/sellers/${sellerId}/review`, token)
      onSaved()
      showToast(t('Отзыв удалён'))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="review-form panel-card" onSubmit={save}>
      <h3>{eligibility.review ? t('Ваш отзыв') : t('Поделитесь впечатлениями')}</h3>
      <p className="section-subtitle">{t('Оцените магазин и расскажите о своей покупке.')}</p>
      {error && <div className="inline-error" role="alert">{error}</div>}
      {eligibility.can_review ? <>
        <label className="field">
          <span>{t('Ваша оценка')}</span>
          <select value={rating} onChange={(event) => setRating(event.target.value)} disabled={busy}>
            {[5, 4, 3, 2, 1].map((value) => <option key={value} value={value}>{'★'.repeat(value)} · {value} из 5</option>)}
          </select>
        </label>
        <label className="field">
          <span>{t('Комментарий')}</span>
          <textarea value={comment} onChange={(event) => setComment(event.target.value)} required maxLength={2000}
            rows={4} disabled={busy} placeholder={t('Что вам понравилось в работе магазина?')} />
        </label>
        <div className="order-actions">
          <Button type="submit" disabled={busy || !comment.trim()}>{busy ? t('Сохраняем…') : t('Сохранить отзыв')}</Button>
          {eligibility.review && <Button variant="outline" onClick={remove} disabled={busy}>{t('Удалить')}</Button>}
        </div>
      </> : <>
        <p>{eligibility.review?.comment}</p>
        <p className="section-subtitle">{t('Для изменения отзыва нужна оплаченная и доставленная покупка.')}</p>
        {eligibility.review && <Button variant="outline" onClick={remove} disabled={busy}>{t('Удалить мой отзыв')}</Button>}
      </>}
    </form>
  )
}

function Pagination({ page, setPage, hasNext, label }) {
  return (
    <nav className="pagination" aria-label={label}>
      <Button variant="outline" disabled={page === 0} onClick={() => setPage(page - 1)}>{t('Назад')}</Button>
      <span>{t("Страница")} {page + 1}</span>
      <Button variant="outline" disabled={!hasNext} onClick={() => setPage(page + 1)}>{t('Далее')}</Button>
    </nav>
  )
}

export default function ShopPage({ sellerId, session, onOpen, onAdd, busyProduct, showToast, onReviewsChanged }) {
  const [shop, setShop] = useState(null)
  const [products, setProducts] = useState([])
  const [reviews, setReviews] = useState([])
  const [eligibility, setEligibility] = useState(null)
  const [productPage, setProductPage] = useState(0)
  const [reviewPage, setReviewPage] = useState(0)
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reviewError, setReviewError] = useState('')
  const isCustomer = session?.role === 'customer'

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    Promise.all([
      apiGet(`/catalog/sellers/${sellerId}`),
      apiGet(`/catalog/products?seller_id=${sellerId}&in_stock=false&offset=${productPage * 24}&limit=24`),
      apiGet(`/catalog/sellers/${sellerId}/reviews?offset=${reviewPage * 20}&limit=20`),
    ]).then(([shopData, productData, reviewData]) => {
      if (active) {
        setShop(shopData)
        setProducts(productData)
        setReviews(reviewData)
      }
    }).catch((requestError) => {
      if (active) setError(getErrorMessage(requestError))
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [sellerId, productPage, reviewPage, revision])

  useEffect(() => {
    let active = true
    setEligibility(null)
    setReviewError('')
    if (isCustomer) {
      apiGet(`/customer/sellers/${sellerId}/review`, session.access_token).then((result) => {
        if (active) setEligibility(result)
      }).catch((requestError) => {
        if (active) setReviewError(getErrorMessage(requestError))
      })
    }
    return () => { active = false }
  }, [sellerId, session?.access_token, isCustomer, revision])

  function reviewSaved() {
    setReviewPage(0)
    setRevision((value) => value + 1)
    onReviewsChanged()
  }

  if (loading) return <PageLoading label={t('Открываем магазин…')} />
  if (error) return <div className="empty-state" role="alert"><h2>{t('Не удалось открыть магазин')}</h2><p>{error}</p>
    <Button onClick={() => setRevision((value) => value + 1)}>{t('Попробовать снова')}</Button></div>

  return (
    <section className="workspace-page shop-page">
      <a className="shop-back" href="#catalog">← {t("Все товары")}</a>
      <div className="shop-header panel-card">
        <div className="shop-avatar" aria-hidden="true">{shop.store_name.slice(0, 1).toUpperCase()}</div>
        <PageTitle eyebrow={t("МАГАЗИН НА MINT MARKET")} title={shop.store_name} subtitle={t('Хорошие находки от независимого продавца.')} />
        <div className="shop-rating"><strong>★ {Number(shop.rating).toFixed(1)}</strong>
          <button type="button" onClick={() => document.getElementById('shop-reviews')?.scrollIntoView({ behavior: 'smooth' })}>{shop.review_count ? t("Отзывов:") + " " + shop.review_count : t('Пока без отзывов')}</button></div>
      </div>

      <div className="section-heading"><div><p className="eyebrow">{t('ВИТРИНА')}</p><h2>{t('Товары магазина')}</h2></div></div>
      {products.length ? <div className="product-grid">{products.map((product) => <ProductCard key={product.product_id}
        product={product} onOpen={() => onOpen(product.product_id)} onAdd={() => onAdd(product.product_id)}
        busy={busyProduct === product.product_id} />)}</div>
        : <div className="empty-state"><h3>{t('В магазине пока нет активных товаров')}</h3><p>{t('Загляните в магазин позже.')}</p></div>}
      <Pagination page={productPage} setPage={setProductPage} hasNext={products.length === 24} label={t('Страницы товаров')} />

      <section id="shop-reviews" className="shop-reviews">
        <div className="section-heading"><div><p className="eyebrow">{t('ОПЫТ ПОКУПАТЕЛЕЙ')}</p><h2>{t('Отзывы о магазине')}</h2>
          <p className="section-subtitle">{t('Отзывы оставляют покупатели после оплаты и получения товара.')}</p></div></div>
        {reviewError && <div className="inline-error" role="alert">{reviewError}</div>}
        {eligibility && (eligibility.can_review || eligibility.review) ? <ReviewForm key={revision}
          sellerId={sellerId} token={session.access_token} eligibility={eligibility} onSaved={reviewSaved} showToast={showToast} />
          : <p className="review-note">{isCustomer ? t('Вы сможете оставить отзыв после оплаты и доставки покупки из этого магазина.')
            : t('Покупатели могут оставить отзыв после оплаты и доставки заказа.')}</p>}
        <div className="reviews-list">{reviews.map((review) => <article className="review-card panel-card" key={review.review_id}>
          <div className="review-top"><strong>{review.customer_name}</strong>
            <span className="review-stars" aria-label={`${review.rating} ${t("из 5")}`}>{'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}</span></div>
          <time dateTime={review.created_at}>{formatDate(review.created_at)}</time>
          <p>{review.comment}</p>
        </article>)}</div>
        {!reviews.length && <p className="review-note">{t('Отзывов пока нет. Ваш опыт может помочь другим покупателям.')}</p>}
        <Pagination page={reviewPage} setPage={setReviewPage} hasNext={(reviewPage + 1) * 20 < shop.review_count} label={t('Страницы отзывов')} />
      </section>
    </section>
  )
}
