import { t } from '../i18n.js'
import { useState } from 'react'
import { apiPost, getErrorMessage } from '../api.js'
import { Button, Field, Icon } from '../components/Common.jsx'

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

  // Отправить данные входа или регистрации на Backend.
  async function submit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      let result = null

      if (mode === 'login') {
        result = await apiPost('/auth/login', {
          email: email,
          password: password,
        })
      } else {
        if (role === 'customer') {
          result = await apiPost('/auth/register/customer', {
            full_name: fullName,
            email: email,
            phone: phone,
            delivery_address: address,
            password: password,
          })
        } else {
          result = await apiPost('/auth/register/seller', {
            store_name: storeName,
            email: email,
            phone: phone,
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
  }

  function closeOnBackground(event) {
    if (event.target === event.currentTarget) {
      onClose()
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={closeOnBackground}>
      <section className="auth-modal modal-panel">
        <button className="modal-close" onClick={onClose} aria-label={t('Закрыть')}>
          <Icon name="close" />
        </button>

        <div className="modal-brand"><span className="brand-mark">m</span> mint market</div>
        <p className="eyebrow">{t('ВАШ МАРКЕТПЛЕЙС')}</p>

        <h2>{mode === 'login' ? t('С возвращением') : t('Создайте аккаунт')}</h2>
        <p className="modal-subtitle">
          {mode === 'login'
            ? t('Войдите, чтобы продолжить покупки и управлять магазином.')
            : t('Покупайте любимые вещи или откройте собственный магазин.')}
        </p>

        <div className="auth-mode-switch">
          <button className={mode === 'login' ? 'active' : ''} onClick={() => changeMode('login')}>{t('Войти')}</button>
          <button className={mode === 'register' ? 'active' : ''} onClick={() => changeMode('register')}>{t('Регистрация')}</button>
        </div>

        {mode === 'register' ? (
          <div className="role-switch">
            <button className={role === 'customer' ? 'active' : ''} onClick={() => setRole('customer')}>
              <Icon name="bag" /> {t('Покупатель')}
            </button>
            <button className={role === 'seller' ? 'active' : ''} onClick={() => setRole('seller')}>
              <Icon name="box" /> {t('Продавец')}
            </button>
          </div>
        ) : null}

        <form onSubmit={submit} className="form-stack">
          {mode === 'register' ? (
            role === 'customer' ? (
              <Field label={t('Ваше имя')} value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder={t('Например, Айша')} required maxLength={100} />
            ) : (
              <Field label={t('Название магазина')} value={storeName} onChange={(event) => setStoreName(event.target.value)} placeholder={t('Например, Mint Store')} required maxLength={100} />
            )
          ) : null}

          <Field label={t('Электронная почта')} type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" required maxLength={100} />

          {mode === 'register' ? (
            <Field label={t('Телефон')} type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+7 700 000 00 00" required maxLength={20} />
          ) : null}

          {mode === 'register' ? (
            role === 'customer' ? (
              <Field label={t('Адрес доставки')} value={address} onChange={(event) => setAddress(event.target.value)} placeholder={t('Город, улица, дом, квартира')} required maxLength={255} />
            ) : null
          ) : null}

          <Field label={t('Пароль')} type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={t('Не менее 8 символов')} required minLength={8} maxLength={128} />

          {error ? <div className="form-error">{error}</div> : null}

          <Button type="submit" className="full-width" disabled={loading}>
            {loading ? t('Подождите…') : mode === 'login' ? t('Войти в аккаунт') : t('Создать аккаунт')}
            <Icon name="arrow" />
          </Button>
        </form>

        <p className="auth-footnote">{t('Продолжая, вы соглашаетесь с правилами использования сервиса.')}</p>
      </section>
    </div>
  )
}
