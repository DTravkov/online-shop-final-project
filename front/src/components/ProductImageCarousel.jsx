import { useEffect, useState } from 'react'
import { getProductGallery, getProductVisual } from '../helpers.js'

// Карусель фотографий товара.
// Сейчас используются демо-фотографии, позже сюда будут приходить фото с Backend.
export default function ProductImageCarousel({ product, size = 'card', onImageClick }) {
  const gallery = getProductGallery(product)
  const images = gallery.images
  const visual = getProductVisual(product?.product_name)

  const [currentIndex, setCurrentIndex] = useState(0)
  const [imageError, setImageError] = useState(false)

  // Сбрасываем выбранное фото, когда открывается другой товар.
  useEffect(() => {
    setCurrentIndex(0)
    setImageError(false)
  }, [product?.product_id])

  // Перейти к предыдущей фотографии.
  function showPrevious(event) {
    event.stopPropagation()

    if (images.length < 2) return

    if (currentIndex === 0) {
      setCurrentIndex(images.length - 1)
    } else {
      setCurrentIndex(currentIndex - 1)
    }

    setImageError(false)
  }

  // Перейти к следующей фотографии.
  function showNext(event) {
    event.stopPropagation()

    if (images.length < 2) return

    if (currentIndex === images.length - 1) {
      setCurrentIndex(0)
    } else {
      setCurrentIndex(currentIndex + 1)
    }

    setImageError(false)
  }

  // Выбрать фотографию по точке или миниатюре.
  function selectImage(index) {
    setCurrentIndex(index)
    setImageError(false)
  }

  // Если фотография не загрузилась, покажем знакомую заглушку.
  let showPhoto = true
  if (imageError) {
    showPhoto = false
  }

  return (
    <div className={'product-image-carousel ' + size + ' ' + visual.className}>
      <button
        type="button"
        className="carousel-image-button"
        onClick={onImageClick}
        aria-label={'Открыть товар: ' + product.product_name}
      >
        {showPhoto ? (
          <img
            className="carousel-photo"
            src={images[currentIndex]}
            alt={product.product_name}
            loading="lazy"
            onError={() => setImageError(true)}
          />
        ) : (
          <span className="carousel-fallback-symbol">{visual.icon}</span>
        )}
      </button>

      {gallery.isDemo ? <span className="carousel-demo-label">Демо-фото</span> : null}

      <span className="carousel-counter">
        {currentIndex + 1} / {images.length}
      </span>

      {images.length > 1 ? (
        <>
          <button
            type="button"
            className="carousel-arrow carousel-arrow-left"
            onClick={showPrevious}
            aria-label="Предыдущая фотография"
          >
            ‹
          </button>
          <button
            type="button"
            className="carousel-arrow carousel-arrow-right"
            onClick={showNext}
            aria-label="Следующая фотография"
          >
            ›
          </button>

          <div className="carousel-dots" aria-label="Выбор фотографии">
            {images.map((image, index) => (
              <button
                type="button"
                key={image + index}
                className={index === currentIndex ? 'active' : ''}
                onClick={(event) => {
                  event.stopPropagation()
                  selectImage(index)
                }}
                aria-label={'Фотография ' + (index + 1)}
                aria-current={index === currentIndex ? 'true' : undefined}
              />
            ))}
          </div>

          {size === 'large' ? (
            <div className="carousel-thumbnails">
              {images.map((image, index) => (
                <button
                  type="button"
                  key={image + '-thumb-' + index}
                  className={index === currentIndex ? 'active' : ''}
                  onClick={() => selectImage(index)}
                  aria-label={'Показать фотографию ' + (index + 1)}
                >
                  <img src={image} alt="" loading="lazy" />
                </button>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
