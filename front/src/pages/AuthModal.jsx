import { useState } from 'react'
import { apiPost, getErrorMessage } from '../api.js'
import { Button, Field, Icon } from '../components/Common.jsx'

function validateAuthForm(values, mode, role) {
  const errors = {}
  const email = values.email.trim()
  const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

  if (!email) {
    errors.email = 'Введите электронную почту.'
  } else if (email.length > 100 || (mode === 'register' && email.length < 3) || !emailPattern.test(email)) {
    errors.email = 'Введите корректную почту (до 100 символов).'
  }

  const minimumPasswordLength = mode === 'register' ? 8 : 1
  if (values.password.length < minimumPasswordLength) {
    errors.password = mode === 'register' ? 'Пароль должен содержать не менее 8 символов.' : 'Введите пароль.'
  } else if (values.password.length > 128) {
    errors.password = 'Пароль не должен превышать 128 символов.'
  }

  if (mode === 'register') {
    const nameField = role === 'customer' ? 'fullName' : 'storeName'
    const nameLabel = role === 'customer' ? 'Имя' : 'Название магазина'
    const name = values[nameField].trim()

    if (!name) {
      errors[nameField] = `Введите ${nameLabel.toLowerCase()}.`
    } else if (name.length > 100) {
      errors[nameField] = 'Максимум 100 символов.'
    }

    const phone = values.phone.trim()
    const phoneDigits = phone.replace(/\D/g, '').length
    if (!phone) {
      errors.phone = 'Введите номер телефона.'
    } else if (phone.length > 20 || !/^[+()\d\s-]+$/.test(phone) || phoneDigits < 7 || phoneDigits > 15) {
      errors.phone = 'Введите корректный номер телефона (7–15 цифр).'
    }

    if (role === 'customer') {
      const address = values.address.trim()
      if (!address) {
        errors.address = 'Введите адрес доставки.'
      } else if (address.length > 255) {
        errors.address = 'Максимум 255 символов.'
      }
    }
  }

  return errors
}

// Окно входа и регистрации.
export default function AuthModal({ onClose, onSuccess }) {
  const [mode, setMode] = useState('login')
  const [role, setRole] = useState('customer')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [storeName, setStoreName] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  function handleChange(field, setValue) {
    return (event) => {
      setValue(event.target.value)
      setFieldErrors((current) => {
        const next = { ...current }
        delete next[field]
        return next
      })
    }
  }

  // Отправить данные входа или регистрации на Backend.
  async function submit(event) {
    event.preventDefault()
    setError('')
    const validationErrors = validateAuthForm(
      { email, password, fullName, phone, address, storeName },
      mode,
      role,
    )
    setFieldErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) {
      return
    }

    setLoading(true)

    try {
      let result = null

      if (mode === 'login') {
        result = await apiPost('/auth/login', {
          email: email.trim().toLowerCase(),
          password: password,
        })
      } else {
        if (role === 'customer') {
          result = await apiPost('/auth/register/customer', {
            full_name: fullName.trim(),
            email: email.trim().toLowerCase(),
            phone: phone.trim(),
            delivery_address: address.trim(),
            password: password,
          })
        } else {
          result = await apiPost('/auth/register/seller', {
            store_name: storeName.trim(),
            email: email.trim().toLowerCase(),
            phone: phone.trim(),
            password: password,
          })
        }
      }

      onSuccess(result)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setLoading(false)
  }

  function changeMode(newMode) {
    setMode(newMode)
    setError('')
    setFieldErrors({})
  }

  function changeRole(newRole) {
    setRole(newRole)
    setFieldErrors({})
  }

  function closeOnBackground(event) {
    if (event.target === event.currentTarget) {
      onClose()
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={closeOnBackground}>
      <section className="auth-modal modal-panel">
        <button className="modal-close" onClick={onClose} aria-label="Закрыть">
          <Icon name="close" />
        </button>

        <div className="modal-brand"><span className="brand-mark">m</span> mint market</div>
        <p className="eyebrow">ВАШ МАРКЕТПЛЕЙС</p>

        <h2>{mode === 'login' ? 'С возвращением' : 'Создайте аккаунт'}</h2>
        <p className="modal-subtitle">
          {mode === 'login'
            ? 'Войдите, чтобы продолжить покупки и управлять магазином.'
            : 'Покупайте любимые вещи или откройте собственный магазин.'}
        </p>

        <div className="auth-mode-switch">
          <button className={mode === 'login' ? 'active' : ''} onClick={() => changeMode('login')}>Войти</button>
          <button className={mode === 'register' ? 'active' : ''} onClick={() => changeMode('register')}>Регистрация</button>
        </div>

        {mode === 'register' ? (
          <div className="role-switch">
            <button className={role === 'customer' ? 'active' : ''} onClick={() => changeRole('customer')}>
              <Icon name="bag" /> Покупатель
            </button>
            <button className={role === 'seller' ? 'active' : ''} onClick={() => changeRole('seller')}>
              <Icon name="box" /> Продавец
            </button>
          </div>
        ) : null}

        <form onSubmit={submit} className="form-stack" noValidate>
          {mode === 'register' ? (
            role === 'customer' ? (
              <Field name="fullName" label="Ваше имя" value={fullName} onChange={handleChange('fullName', setFullName)} placeholder="Например, Айша" required maxLength={100} error={fieldErrors.fullName} />
            ) : (
              <Field name="storeName" label="Название магазина" value={storeName} onChange={handleChange('storeName', setStoreName)} placeholder="Например, Mint Store" required maxLength={100} error={fieldErrors.storeName} />
            )
          ) : null}

          <Field name="email" label="Электронная почта" type="email" value={email} onChange={handleChange('email', setEmail)} placeholder="name@example.com" required maxLength={100} error={fieldErrors.email} autoComplete="email" />

          {mode === 'register' ? (
            <Field name="phone" label="Телефон" type="tel" value={phone} onChange={handleChange('phone', setPhone)} placeholder="+7 700 000 00 00" required maxLength={20} error={fieldErrors.phone} autoComplete="tel" />
          ) : null}

          {mode === 'register' ? (
            role === 'customer' ? (
              <Field name="address" label="Адрес доставки" value={address} onChange={handleChange('address', setAddress)} placeholder="Город, улица, дом, квартира" required maxLength={255} error={fieldErrors.address} autoComplete="street-address" />
            ) : null
          ) : null}

          <Field name="password" label="Пароль" type="password" value={password} onChange={handleChange('password', setPassword)} placeholder={mode === 'register' ? 'Не менее 8 символов' : 'Введите пароль'} required minLength={mode === 'register' ? 8 : 1} maxLength={128} error={fieldErrors.password} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />

          {error ? <div className="form-error">{error}</div> : null}

          <Button type="submit" className="full-width" disabled={loading}>
            {loading ? 'Подождите…' : mode === 'login' ? 'Войти в аккаунт' : 'Создать аккаунт'}
            <Icon name="arrow" />
          </Button>
        </form>

        <p className="auth-footnote">Продолжая, вы соглашаетесь с правилами использования сервиса.</p>
      </section>
    </div>
  )
}
