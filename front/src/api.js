// Адрес API. Vite передаст запрос в FastAPI через proxy.
const API_URL = '/api'

// Общая функция для отправки запросов на Backend.
async function sendRequest(path, method, data, token) {
  const options = {
    method: method,
    headers: {},
  }

  // Если отправляем данные, указываем формат JSON.
  if (data !== null) {
    if (data !== undefined) {
      options.headers['Content-Type'] = 'application/json'
      options.body = JSON.stringify(data)
    }
  }

  // Если пользователь вошёл в аккаунт, добавляем JWT-токен.
  if (token) {
    options.headers.Authorization = 'Bearer ' + token
  }

  const response = await fetch(API_URL + path, options)

  // Некоторые запросы успешно завершаются без ответа.
  if (response.status === 204) {
    return null
  }

  let result = null

  try {
    result = await response.json()
  } catch (error) {
    result = null
  }

  // Показываем ошибку, если Backend вернул неуспешный статус.
  if (!response.ok) {
    let message = 'Ошибка запроса. Код: ' + response.status

    if (result !== null) {
      if (result.detail) {
        if (Array.isArray(result.detail)) {
          message = ''

          for (let i = 0; i < result.detail.length; i++) {
            if (i > 0) {
              message = message + '; '
            }
            message = message + result.detail[i].msg
          }
        } else {
          message = result.detail
        }
      }
    }

    throw new Error(message)
  }

  return result
}

// Получить данные.
export function apiGet(path, token) {
  return sendRequest(path, 'GET', null, token)
}

// Создать новую запись или выполнить действие.
export function apiPost(path, data, token) {
  return sendRequest(path, 'POST', data, token)
}

// Полностью обновить запись.
export function apiPut(path, data, token) {
  return sendRequest(path, 'PUT', data, token)
}

// Изменить отдельные поля записи.
export function apiPatch(path, data, token) {
  return sendRequest(path, 'PATCH', data, token)
}

// Удалить запись.
export function apiDelete(path, token) {
  return sendRequest(path, 'DELETE', null, token)
}

// Преобразовать цену в тенге.
export function formatPrice(price) {
  const number = Number(price)

  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'KZT',
    maximumFractionDigits: 0,
  }).format(number)
}

// Преобразовать дату в понятный формат.
export function formatDate(value) {
  if (!value) {
    return '—'
  }

  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

// Получить текст ошибки.
export function getErrorMessage(error) {
  if (error) {
    if (error.message) {
      return error.message
    }
  }

  return 'Что-то пошло не так. Попробуйте ещё раз.'
}
