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
    shipped: 'В пути',
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
