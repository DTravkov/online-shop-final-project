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
      showToast('Баланс пополнен')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  if (loading && !wallet) return <PageLoading label="Загружаем баланс…" />

  return (
    <section className="workspace-page wallet-page">
      <PageTitle eyebrow="ЛИЧНЫЙ КАБИНЕТ" title="Мой баланс" subtitle="Пополняйте баланс, оплачивайте покупки и следите за поступлениями."
        action={<Button variant="outline" onClick={() => setRevision((value) => value + 1)} disabled={loading}>Обновить</Button>} />
      {error && <div className="inline-error" role="alert">{error}</div>}
      {!wallet && <Button onClick={() => setRevision((value) => value + 1)}>Попробовать снова</Button>}
      {wallet && <>
        <div className="wallet-layout">
          <div className="wallet-summary panel-card">
            <p className="eyebrow">ДОСТУПНО НА СЧЁТЕ</p>
            <strong className="wallet-amount">{formatPrice(wallet.balance)}</strong>
            <p>Покупки списываются с баланса. Доход от продаж поступает сюда сразу после оплаты покупателем.</p>
          </div>
          <form className="wallet-deposit panel-card" onSubmit={deposit}>
            <h3>Пополнить баланс</h3>
            <p className="section-subtitle">Тестовое пополнение: укажите сумму, деньги добавятся без банковской оплаты.</p>
            <Field label="Сумма пополнения, ₸" type="number" value={amount} onChange={(event) => setAmount(event.target.value)}
              required min="0.01" step="0.01" />
            <Button type="submit" disabled={busy || !amount}>{busy ? 'Пополняем…' : 'Пополнить'}</Button>
          </form>
        </div>
        <div className="section-heading"><div><p className="eyebrow">ДВИЖЕНИЕ СРЕДСТВ</p><h2>История операций</h2></div></div>
        {loading ? <PageLoading label="Обновляем историю…" /> : <div className="wallet-history panel-card">
          {transactions.length ? transactions.map((transaction) => <div className="wallet-transaction" key={transaction.transaction_id}>
            <div><strong>{transactionNames[transaction.kind]}</strong>
              <small>{formatDate(transaction.created_at)}{transaction.order_id ? ` · Заказ №${transaction.order_id}` : ''}</small></div>
            <b className={Number(transaction.amount) < 0 ? 'wallet-debit' : 'wallet-credit'}>
              {Number(transaction.amount) > 0 ? '+' : ''}{formatPrice(transaction.amount)}
            </b>
          </div>) : <div className="empty-state"><h3>Операций пока нет</h3><p>Пополните баланс, чтобы оплатить первую покупку.</p></div>}
        </div>}
        <nav className="pagination" aria-label="История операций">
          <Button variant="outline" disabled={loading || page === 0} onClick={() => setPage(page - 1)}>Назад</Button>
          <span>Страница {page + 1}</span>
          <Button variant="outline" disabled={loading || transactions.length < 20} onClick={() => setPage(page + 1)}>Далее</Button>
        </nav>
      </>}
    </section>
  )
}
