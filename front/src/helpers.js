// Выбрать значок и цвет карточки по названию товара.
export function getProductVisual(productName) {
  let name = ''

  if (productName) {
    name = String(productName).toLowerCase()
  }

  // Проверяем, относится ли товар к технике.
  if (name.includes('телефон')) return { icon: '⌁', className: 'visual-tech', tag: 'Техника' }
  if (name.includes('смартфон')) return { icon: '⌁', className: 'visual-tech', tag: 'Техника' }
  if (name.includes('ноутбук')) return { icon: '⌁', className: 'visual-tech', tag: 'Техника' }
  if (name.includes('компьютер')) return { icon: '⌁', className: 'visual-tech', tag: 'Техника' }
  if (name.includes('планшет')) return { icon: '⌁', className: 'visual-tech', tag: 'Техника' }

  // Проверяем, относится ли товар к аудио.
  if (name.includes('наушник')) return { icon: '♫', className: 'visual-audio', tag: 'Аудио' }
  if (name.includes('колонк')) return { icon: '♫', className: 'visual-audio', tag: 'Аудио' }
  if (name.includes('звук')) return { icon: '♫', className: 'visual-audio', tag: 'Аудио' }
  if (name.includes('аудио')) return { icon: '♫', className: 'visual-audio', tag: 'Аудио' }

  // Проверяем одежду и обувь.
  if (name.includes('одежд')) return { icon: '✳', className: 'visual-style', tag: 'Стиль' }
  if (name.includes('футбол')) return { icon: '✳', className: 'visual-style', tag: 'Стиль' }
  if (name.includes('куртк')) return { icon: '✳', className: 'visual-style', tag: 'Стиль' }
  if (name.includes('плать')) return { icon: '✳', className: 'visual-style', tag: 'Стиль' }
  if (name.includes('джинс')) return { icon: '✳', className: 'visual-style', tag: 'Стиль' }
  if (name.includes('обув')) return { icon: '✳', className: 'visual-style', tag: 'Стиль' }
  if (name.includes('кроссов')) return { icon: '✳', className: 'visual-style', tag: 'Стиль' }

  // Проверяем товары для дома.
  if (name.includes('дом')) return { icon: '⌂', className: 'visual-home', tag: 'Для дома' }
  if (name.includes('кух')) return { icon: '⌂', className: 'visual-home', tag: 'Для дома' }
  if (name.includes('ламп')) return { icon: '⌂', className: 'visual-home', tag: 'Для дома' }
  if (name.includes('стол')) return { icon: '⌂', className: 'visual-home', tag: 'Для дома' }
  if (name.includes('кресл')) return { icon: '⌂', className: 'visual-home', tag: 'Для дома' }
  if (name.includes('посуда')) return { icon: '⌂', className: 'visual-home', tag: 'Для дома' }

  // Проверяем книги и канцелярию.
  if (name.includes('книг')) return { icon: '▤', className: 'visual-books', tag: 'Книги' }
  if (name.includes('блокнот')) return { icon: '▤', className: 'visual-books', tag: 'Книги' }
  if (name.includes('ручк')) return { icon: '▤', className: 'visual-books', tag: 'Книги' }
  if (name.includes('тетрад')) return { icon: '▤', className: 'visual-books', tag: 'Книги' }

  // Проверяем аксессуары.
  if (name.includes('сумк')) return { icon: '◇', className: 'visual-accessory', tag: 'Аксессуары' }
  if (name.includes('кошел')) return { icon: '◇', className: 'visual-accessory', tag: 'Аксессуары' }
  if (name.includes('ремень')) return { icon: '◇', className: 'visual-accessory', tag: 'Аксессуары' }
  if (name.includes('очк')) return { icon: '◇', className: 'visual-accessory', tag: 'Аксессуары' }
  if (name.includes('час')) return { icon: '◇', className: 'visual-accessory', tag: 'Аксессуары' }

  return { icon: '✧', className: 'visual-default', tag: 'Находка' }
}

// Перевести статус заказа на русский язык.
export function getStatusName(status) {
  const names = {
    new: 'Новый',
    partially_shipped: 'Частично отправлен',
    shipped: 'В пути',
    partially_delivered: 'Частично доставлен',
    delivered: 'Доставлен',
    cancelled: 'Отменён',
    paid: 'Оплачен',
    pending: 'Ожидает оплаты',
    refunded: 'Возвращён',
  }

  if (names[status]) {
    return names[status]
  }

  return status
}

// Здесь можно вручную указать фотографии для конкретного ID товара.
// Например: 15: ['/images/my-product-1.jpg', '/images/my-product-2.jpg']
const PRODUCT_IMAGE_OVERRIDES = {}

// Временные фотографии с Unsplash.
// Они нужны, пока Backend ещё не возвращает фотографии товаров.
const DEMO_PRODUCT_IMAGES = {
  // Телефоны, ноутбуки и другая техника.
  tech: [
    'https://images.unsplash.com/photo-1611073310858-875b989e02d6?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1723054072995-af2b91c5cbb6?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1517754461499-9930e2b54957?auto=format&fit=crop&w=850&q=80',
  ],

  // Наушники и аудиотехника.
  audio: [
    'https://images.unsplash.com/photo-1637868796503-9191d8ae78be?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1583343894790-5cff219de28a?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=850&q=80',
  ],

  // Обувь и одежда.
  style: [
    'https://images.unsplash.com/photo-1620989928357-71ff9bbf1f34?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1625860191460-10a66c7384fb?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1680204101400-aeac783c9d87?auto=format&fit=crop&w=850&q=80',
  ],

  // Рюкзаки, сумки и аксессуары.
  bags: [
    'https://images.unsplash.com/photo-1583300418584-8332e32b710e?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1623085151447-3761e3168f3d?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1650500426868-27a68714a4a4?auto=format&fit=crop&w=850&q=80',
  ],

  // Кружки, посуда и товары для дома.
  home: [
    'https://images.unsplash.com/photo-1617294891800-30497d3cbee7?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1516646227334-6102731f3c25?auto=format&fit=crop&w=850&q=80',
    'https://images.unsplash.com/photo-1612509590595-785e974ed690?auto=format&fit=crop&w=850&q=80',
  ],
}

// Получить список фотографий товара.
// Если Backend уже прислал фото, используем их.
// Если фотографий пока нет, используем временные демо-фото.
export function getProductGallery(product) {
  // Сначала проверяем, есть ли отдельные фото для этого товара.
  if (product?.product_id && PRODUCT_IMAGE_OVERRIDES[product.product_id]) {
    return {
      images: PRODUCT_IMAGE_OVERRIDES[product.product_id],
      isDemo: true,
    }
  }

  let serverImages = []

  if (Array.isArray(product?.images)) {
    serverImages = product.images.map((image) => {
      if (typeof image === 'string') return image
      if (image?.image_url) return image.image_url
      if (image?.url) return image.url
      return ''
    }).filter((image) => image)
  }

  if (serverImages.length === 0 && Array.isArray(product?.image_urls)) {
    serverImages = product.image_urls.filter((image) => typeof image === 'string' && image)
  }

  if (serverImages.length === 0 && product?.image_url) {
    serverImages = [product.image_url]
  }

  if (serverImages.length > 0) {
    return {
      images: serverImages,
      isDemo: false,
    }
  }

  let name = ''
  if (product?.product_name) {
    name = String(product.product_name).toLowerCase()
  }

  // Подбираем временные фотографии по названию товара.
  if (name.includes('телефон') || name.includes('смартфон') || name.includes('ноутбук') || name.includes('компьютер') || name.includes('планшет') || name.includes('техник') || name.includes('smartphone') || name.includes('laptop') || name.includes('computer') || name.includes('phone')) {
    return { images: DEMO_PRODUCT_IMAGES.tech, isDemo: true }
  }

  if (name.includes('наушник') || name.includes('колонк') || name.includes('аудио') || name.includes('звук') || name.includes('headphone') || name.includes('speaker') || name.includes('audio')) {
    return { images: DEMO_PRODUCT_IMAGES.audio, isDemo: true }
  }

  if (name.includes('кроссов') || name.includes('обув') || name.includes('футбол') || name.includes('куртк') || name.includes('плать') || name.includes('джинс') || name.includes('sneaker') || name.includes('shoes') || name.includes('jacket') || name.includes('dress')) {
    return { images: DEMO_PRODUCT_IMAGES.style, isDemo: true }
  }

  if (name.includes('рюкзак') || name.includes('сумк') || name.includes('кошел') || name.includes('ремень') || name.includes('bag')) {
    return { images: DEMO_PRODUCT_IMAGES.bags, isDemo: true }
  }

  if (name.includes('круж') || name.includes('чаш') || name.includes('посуда') || name.includes('кух') || name.includes('ваза') || name.includes('дом') || name.includes('mug') || name.includes('cup') || name.includes('ceramic') || name.includes('vase')) {
    return { images: DEMO_PRODUCT_IMAGES.home, isDemo: true }
  }

  // Для неизвестной категории используем нейтральную временную галерею.
  return { images: DEMO_PRODUCT_IMAGES.audio, isDemo: true }
}
