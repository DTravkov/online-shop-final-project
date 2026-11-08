import { useEffect, useState } from 'react'
import { apiGet, apiPatch, apiPut, getErrorMessage } from '../api.js'
import { Button, Field, Icon, PageLoading, PageTitle } from '../components/Common.jsx'

// Страница изменения личного профиля.
export default function ProfilePage({ token, role, showToast }) {
  const isSeller = role === 'seller'

  const [profile, setProfile] = useState(null)
  const [fullName, setFullName] = useState('')
  const [storeName, setStoreName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Загрузить профиль покупателя или продавца.
  async function loadProfile() {
    setLoading(true)
    setError('')

    let path = '/customer/profile'
    if (isSeller) {
      path = '/seller/profile'
    }

    try {
      const profileData = await apiGet(path, token)
      setProfile(profileData)

      let savedEmail = ''
      let savedPhone = ''
      if (profileData.email) {
        savedEmail = profileData.email
      }
      if (profileData.phone) {
        savedPhone = profileData.phone
      }
      setEmail(savedEmail)
      setPhone(savedPhone)

      if (isSeller) {
        let savedStoreName = ''
        if (profileData.store_name) {
          savedStoreName = profileData.store_name
        }
        setStoreName(savedStoreName)
      } else {
        let savedFullName = ''
        let savedAddress = ''
        if (profileData.full_name) {
          savedFullName = profileData.full_name
        }
        if (profileData.delivery_address) {
          savedAddress = profileData.delivery_address
        }
        setFullName(savedFullName)
        setAddress(savedAddress)
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setLoading(false)
  }

  useEffect(() => {
    loadProfile()
  }, [token, role])

  // Сохранить изменения профиля.
  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')

    try {
      if (isSeller) {
        await apiPatch('/seller/profile', {
          store_name: storeName.trim(),
          email: email.trim(),
          phone: phone.trim(),
        }, token)
      } else {
        await apiPatch('/customer/profile', {
          full_name: fullName.trim(),
          email: email.trim(),
          phone: phone.trim(),
        }, token)

        await apiPut('/customer/delivery-address', {
          delivery_address: address.trim(),
        }, token)
      }

      await loadProfile()
      showToast('Изменения сохранены')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    }

    setSaving(false)
  }

  if (loading) {
    return <PageLoading label="Загружаем профиль…" />
  }

  let displayName = fullName
  let roleName = 'Аккаунт покупателя'

  if (isSeller) {
    displayName = storeName
    roleName = 'Аккаунт продавца'
  }

  let rating = 0
  if (profile !== null) {
    if (profile.rating) {
      rating = Number(profile.rating).toFixed(1)
    }
  }

  let firstLetter = 'M'
  if (displayName) {
    firstLetter = displayName.charAt(0).toUpperCase()
  }

  return (
    <section className="workspace-page profile-page">
      <PageTitle eyebrow="ЛИЧНЫЙ КАБИНЕТ" title="Мой профиль" subtitle="Контактные данные и настройки аккаунта." />
      {error ? <div className="inline-error">{error}</div> : null}

      {profile ? (
        <div className="profile-layout">
          <div className="profile-aside panel-card">
            <div className="profile-avatar">{firstLetter}</div>
            <h3>{displayName}</h3>
            <span className="role-label">{roleName}</span>

            {isSeller ? (
              <div className="profile-rating">★ {rating} <small>рейтинг магазина</small></div>
            ) : null}

            <div className="profile-note">Данные профиля используются для связи и оформления заказов.</div>
          </div>

          <form className="profile-form panel-card" onSubmit={submit}>
            <div className="panel-heading">
              <h3>Основная информация</h3>
              <span>Изменения сохраняются в аккаунте</span>
            </div>

            {isSeller ? (
              <Field label="Название магазина" value={storeName} onChange={(event) => setStoreName(event.target.value)} required maxLength={100} />
            ) : (
              <Field label="Полное имя" value={fullName} onChange={(event) => setFullName(event.target.value)} required maxLength={100} />
            )}

            <Field label="Электронная почта" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={100} />
            <Field label="Телефон" value={phone} onChange={(event) => setPhone(event.target.value)} required maxLength={20} />

            {!isSeller ? (
              <label className="field">
                <span>Адрес доставки по умолчанию</span>
                <textarea rows={3} value={address} onChange={(event) => setAddress(event.target.value)} required maxLength={255} />
              </label>
            ) : null}

            <div className="profile-form-footer">
              <p>Новый email также станет логином для входа.</p>
              <Button type="submit" disabled={saving}>
                {saving ? 'Сохраняем…' : 'Сохранить изменения'} <Icon name="check" />
              </Button>
            </div>
          </form>
        </div>
      ) : null}
    </section>
  )
}
