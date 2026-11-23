import { t } from '../i18n.js'
import { useEffect, useState } from 'react'
import { apiGet, apiPost, formatDate, formatPrice, getErrorMessage } from '../api.js'
import { Button, Field, PageLoading, PageTitle } from '../components/Common.jsx'

const transactionNames = {
  deposit: 'Пополнение',
  payment: 'Оплата заказа',
  sale: 'Доход от продажи',
  refund: 'Возврат за заказ',
  sale_refund: 'Возврат покупателю',
}

export default function WalletPage({ token, showToast, onBalanceChange }) {
  const [wallet, setWallet] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [amount, setAmount] = useState('')
  const [page, setPage] = useState(0)
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    Promise.all([
      apiGet('/wallet', token),
      apiGet(`/wallet/transactions?offset=${page * 20}&limit=20`, token),
    ]).then(([balanceData, history]) => {
      if (active) {
        setWallet(balanceData)
        setTransactions(history)
        onBalanceChange(balanceData.balance)
      }
    }).catch((requestError) => {
      if (active) setError(getErrorMessage(requestError))
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [token, page, revision, onBalanceChange])

  useEffect(() => {
    function refresh() { setRevision((value) => value + 1) }
    window.addEventListener('focus', refresh)
    return () => window.removeEventListener('focus', refresh)
  }, [])

  async function deposit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      // Send the decimal string unchanged so fractional amounts keep their precision.
      const result = await apiPost('/wallet/deposit', { amount }, token)
      setWallet(result)
      onBalanceChange(result.balance)
      setAmount('')
      setPage(0)
      setRevision((value) => value + 1)
      showToast(t('Баланс пополнен'))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  if (loading && !wallet) return <PageLoading label={t('Загружаем баланс…')} />

  return (
    <section className="workspace-page wallet-page">
      <PageTitle eyebrow={t("ЛИЧНЫЙ КАБИНЕТ")} title={t('Мой баланс')} subtitle={t('Пополняйте баланс, оплачивайте покупки и следите за поступлениями.')}
        action={<Button variant="outline" onClick={() => setRevision((value) => value + 1)} disabled={loading}>{t('Обновить')}</Button>} />
      {error && <div className="inline-error" role="alert">{error}</div>}
      {!wallet && <Button onClick={() => setRevision((value) => value + 1)}>{t('Попробовать снова')}</Button>}
      {wallet && <>
        <div className="wallet-layout">
          <div className="wallet-summary panel-card">
            <p className="eyebrow">{t('ДОСТУПНО НА СЧЁТЕ')}</p>
            <strong className="wallet-amount">{formatPrice(wallet.balance)}</strong>
            <p>{t('Покупки списываются с баланса. Доход от продаж поступает сюда сразу после оплаты покупателем.')}</p>
          </div>
          <form className="wallet-deposit panel-card" onSubmit={deposit}>
            <h3>{t('Пополнить баланс')}</h3>
            <p className="section-subtitle">{t('Тестовое пополнение: укажите сумму, деньги добавятся без банковской оплаты.')}</p>
            <Field label={t('Сумма пополнения, ₸')} type="number" value={amount} onChange={(event) => setAmount(event.target.value)}
              required min="0.01" step="0.01" />
            <Button type="submit" disabled={busy || !amount}>{busy ? t('Пополняем…') : t('Пополнить')}</Button>
          </form>
        </div>
        <div className="section-heading"><div><p className="eyebrow">{t('ДВИЖЕНИЕ СРЕДСТВ')}</p><h2>{t('История операций')}</h2></div></div>
        {loading ? <PageLoading label={t("Обновляем историю…")} /> : <div className="wallet-history panel-card">
          {transactions.length ? transactions.map((transaction) => <div className="wallet-transaction" key={transaction.transaction_id}>
            <div><strong>{t(transactionNames[transaction.kind] || transaction.kind)}</strong>
              <small>{formatDate(transaction.created_at)}{transaction.order_id ? ` · ${t("Заказ №")}${transaction.order_id}` : ''}</small></div>
            <b className={Number(transaction.amount) < 0 ? 'wallet-debit' : 'wallet-credit'}>
              {Number(transaction.amount) > 0 ? '+' : ''}{formatPrice(transaction.amount)}
            </b>
          </div>) : <div className="empty-state"><h3>{t('Операций пока нет')}</h3><p>{t('Пополните баланс, чтобы оплатить первую покупку.')}</p></div>}
        </div>}
        <nav className="pagination" aria-label={t('История операций')}>
          <Button variant="outline" disabled={loading || page === 0} onClick={() => setPage(page - 1)}>{t('Назад')}</Button>
          <span>{t("Страница")} {page + 1}</span>
          <Button variant="outline" disabled={loading || transactions.length < 20} onClick={() => setPage(page + 1)}>{t('Далее')}</Button>
        </nav>
      </>}
    </section>
  )
}
