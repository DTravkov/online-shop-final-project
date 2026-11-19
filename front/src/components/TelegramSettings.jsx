import { useEffect, useState } from 'react'
import { apiDelete, apiGet, apiPost, getErrorMessage } from '../api.js'
import { Button } from './Common.jsx'

const path = '/telegram/link'

export default function TelegramSettings({ token }) {
  const [status, setStatus] = useState(null)
  const [url, setUrl] = useState('')
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    apiGet(path, token)
      .then((result) => { if (active) setStatus(result) })
      .catch((requestError) => { if (active) setError(getErrorMessage(requestError)) })
    return () => { active = false }
  }, [token])

  async function perform(action) {
    setBusy(true)
    setError('')
    try {
      await action()
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  function start() {
    return perform(async () => {
      const result = await apiPost(`${path}/start`, null, token)
      setUrl(result.url)
      setCode('')
    })
  }

  function confirm(event) {
    event.preventDefault()
    return perform(async () => {
      await apiPost(`${path}/confirm`, { code: code.trim() }, token)
      setStatus({ ...status, linked: true })
      setUrl('')
      setCode('')
    })
  }

  function unlink() {
    return perform(async () => {
      await apiDelete(path, token)
      setStatus({ ...status, linked: false })
      setUrl('')
      setCode('')
    })
  }

  return (
    <section className="profile-form profile-telegram panel-card">
      <div className="panel-heading">
        <h3>Уведомления в Telegram</h3>
        {status && <span role="status">{status.linked ? 'Подключено' : 'Не подключено'}</span>}
      </div>
      {error && <div className="inline-error" role="alert">{error}</div>}
      {!status && !error && <p role="status">Проверяем подключение…</p>}
      {status?.linked && <Button variant="outline" onClick={unlink} disabled={busy}>Отключить Telegram</Button>}
      {status && !status.enabled && <p>Уведомления в Telegram сейчас недоступны.</p>}
      {status?.enabled && !status.linked && !url && <Button onClick={start} disabled={busy}>Подключить Telegram</Button>}
      {url && (
        <form onSubmit={confirm}>
          <p>Откройте бота, нажмите Start и введите полученный код. Ссылка действует 5 минут.</p>
          <a className="button button-primary" href={url} target="_blank" rel="noopener noreferrer">Открыть Telegram</a>
          <label className="field">
            <span>Код из Telegram</span>
            <input value={code} onChange={(event) => setCode(event.target.value)} required
              pattern="[a-fA-F0-9]{12}" maxLength={12} autoComplete="off" spellCheck={false} />
          </label>
          <div className="profile-telegram-actions">
            <Button type="submit" disabled={busy}>Подтвердить</Button>
            <Button variant="soft" onClick={start} disabled={busy}>Новая ссылка</Button>
            <Button variant="outline" onClick={unlink} disabled={busy}>Отменить</Button>
          </div>
        </form>
      )}
    </section>
  )
}
