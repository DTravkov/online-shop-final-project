import { formatPrice } from '../api.js'
import { getProductVisual } from '../helpers.js'
import { Button, Icon } from '../components/Common.jsx'

// Одна карточка товара в каталоге.
function ProductCard({ product, onOpen, onAdd, busy }) {
  const visual = getProductVisual(product.product_name)

  let storeName = 'Магазин'
  if (product.store_name) {
    storeName = product.store_name
  }

  let rating = 0
  if (product.seller_rating) {
    rating = Number(product.seller_rating)
  }

  let cannotAdd = false
  if (busy) {
    cannotAdd = true
  }
  if (product.stock_quantity < 1) {
    cannotAdd = true
  }

  return (
    <article className="product-card">
      <button className={'product-visual ' + visual.className} onClick={onOpen} aria-label={'Подробнее: ' + product.product_name}>
        <span className="visual-tag">{visual.tag}</span>
        <span className="visual-symbol">{visual.icon}</span>
        <span className="visual-id">№{String(product.product_id).padStart(3, '0')}</span>
      </button>

      <div className="product-info">
        <div className="product-store">
          {storeName}
          <span> · ★ {rating.toFixed(1)}</span>
        </div>

        <button className="product-name" onClick={onOpen}>{product.product_name}</button>

        <div className="product-meta">
          {product.stock_quantity > 0
            ? 'В наличии · ' + product.stock_quantity + ' шт.'
            : 'Нет в наличии'}
        </div>

        <div className="product-buy-row">
          <strong>{formatPrice(product.price)}</strong>
          <button className="round-add" onClick={onAdd} disabled={cannotAdd} title="Добавить в корзину">
            <Icon name="plus" />
          </button>
        </div>
      </div>
    </article>
  )
}

// Подробная информация о товаре и предложения других продавцов.
export function ProductModal({ product, onClose, onAdd, busy }) {
  if (!product) {
    return null
  }

  const visual = getProductVisual(product.product_name)

  let rating = 0
  if (product.seller_rating) {
    rating = Number(product.seller_rating)
  }

  let stockText = 'Сейчас нет в наличии'
  if (product.stock_quantity > 0) {
    stockText = 'В наличии ' + product.stock_quantity + ' шт.'
  }

  let cannotAdd = false
  if (busy) {
    cannotAdd = true
  }
  if (product.stock_quantity < 1) {
    cannotAdd = true
  }

  let showOffers = false
  if (product.offers) {
    if (product.offers.length > 1) {
      showOffers = true
    }
  }

  function closeOnBackground(event) {
    if (event.target === event.currentTarget) {
      onClose()
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={closeOnBackground}>
      <section className="product-modal modal-panel">
        <button className="modal-close" onClick={onClose} aria-label="Закрыть"><Icon name="close" /></button>

        <div className={'detail-visual ' + visual.className}>
          <span className="visual-tag">{visual.tag}</span>
          <span className="visual-symbol">{visual.icon}</span>
          <span className="visual-id">№{String(product.product_id).padStart(3, '0')}</span>
        </div>

        <div className="detail-content">
          <p className="eyebrow">КАРТОЧКА ТОВАРА</p>
          <h2>{product.product_name}</h2>
          <p className="detail-seller">{product.store_name} · ★ {rating.toFixed(1)}</p>
          <p className="detail-stock">{stockText}</p>
          <div className="detail-price">{formatPrice(product.price)}</div>

          <Button onClick={() => onAdd(product.product_id)} disabled={cannotAdd} className="full-width">
            Добавить в корзину <Icon name="bag" />
          </Button>

          {showOffers ? (
            <div className="offers">
              <h3>Другие предложения</h3>
              {product.offers.map((offer) => {
                let offerButtonDisabled = false
                if (busy) {
                  offerButtonDisabled = true
                }
                if (offer.stock_quantity < 1) {
                  offerButtonDisabled = true
                }

                return (
                <div className="offer-row" key={offer.product_id}>
                  <div>
                    <strong>{offer.store_name}</strong>
                    <small>★ {Number(offer.seller_rating).toFixed(1)} · {offer.stock_quantity} шт.</small>
                  </div>
                  <b>{formatPrice(offer.price)}</b>
                  <button onClick={() => onAdd(offer.product_id)} disabled={offerButtonDisabled}>Выбрать</button>
                </div>
                )
              })}
            </div>
          ) : null}
        </div>
      </section>
    </div>
  )
}

// Главная страница с товарами.
export default function CatalogPage(props) {
  let showProducts = false
  let showEmptyMessage = false

  if (!props.loading) {
    if (props.products.length > 0) {
      showProducts = true
    } else {
      showEmptyMessage = true
    }
  }

  return (
    <>
      <section className="hero-section">
        <div className="hero-copy">
          <span className="hero-kicker"><span /> МЕСТО, ГДЕ ВСТРЕЧАЮТСЯ НАХОДКИ</span>
          <h1>Хорошие вещи.<br /><em>Хорошие люди.</em></h1>
          <p>Открывайте небольшие магазины, находите особенные вещи и поддерживайте продавцов, которым доверяете.</p>
          <a className="hero-link" href="#catalog">Исследовать каталог <Icon name="arrow" /></a>
        </div>

        <div className="hero-art" aria-label="Иллюстрация товаров">
          <div className="art-orbit orbit-one" />
          <div className="art-orbit orbit-two" />
          <div className="art-card art-card-back"><span>МАЛЕНЬКИЕ БРЕНДЫ</span><b>Большие<br />возможности.</b><i>✳</i></div>
          <div className="art-card art-card-front"><div className="art-product-symbol">✧</div><span>РЕДКАЯ НАХОДКА</span><strong>Выбрано<br />с заботой.</strong><small>mint selection / 2026</small></div>
          <span className="art-sticker">shop<br />local <b>↗</b></span>
          <span className="art-sparkle sparkle-one">✳</span>
          <span className="art-sparkle sparkle-two">✧</span>
        </div>
      </section>

      <section className="catalog-section" id="catalog">
        <div className="section-heading">
          <div>
            <p className="eyebrow">СОБРАНО ДЛЯ ВАС</p>
            <h2>Свежие находки<span>.</span></h2>
            <p className="section-subtitle">Товары от независимых продавцов на одной площадке.</p>
          </div>
          <div className="catalog-count">{props.products.length.toString().padStart(2, '0')} <span>товаров на странице</span></div>
        </div>

        <form className="catalog-tools" onSubmit={props.onSearch}>
          <div className="catalog-search">
            <Icon name="search" />
            <input value={props.search} onChange={(event) => props.setSearch(event.target.value)} placeholder="Что будем искать сегодня?" />
            <button type="submit">Найти</button>
          </div>

          <label className="stock-toggle">
            <input type="checkbox" checked={props.inStock} onChange={(event) => props.setInStock(event.target.checked)} />
            <span className="toggle-track" />
            <span>Только в наличии</span>
          </label>

          <label className="sort-select">
            <Icon name="filter" />
            <select value={props.sort} onChange={(event) => props.setSort(event.target.value)}>
              <option value="id">Сначала новые</option>
              <option value="price_asc">Сначала дешевле</option>
              <option value="price_desc">Сначала дороже</option>
              <option value="name">По названию</option>
            </select>
          </label>
        </form>

        {props.error ? <div className="inline-error">{props.error}</div> : null}

        {props.loading ? (
          <div className="loading-grid">
            {Array.from({ length: 8 }).map((item, index) => (
              <div className="skeleton-card" key={index}><div /><span /><span /></div>
            ))}
          </div>
        ) : null}

        {showProducts ? (
          <div className="product-grid">
            {props.products.map((product) => (
              <ProductCard
                key={product.product_id}
                product={product}
                onOpen={() => props.onOpen(product.product_id)}
                onAdd={() => props.onAdd(product.product_id)}
                busy={props.busyProduct === product.product_id}
              />
            ))}
          </div>
        ) : null}

        {showEmptyMessage ? (
          <div className="empty-state">
            <div className="empty-icon">⌕</div>
            <h3>Пока ничего не найдено</h3>
            <p>Попробуйте изменить поисковый запрос или фильтр.</p>
          </div>
        ) : null}
      </section>
    </>
  )
}
