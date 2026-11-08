import { getStatusName } from '../helpers.js'

// Простые текстовые значки для кнопок и навигации.
export function Icon({ name }) {
  const icons = {
    search: '⌕',
    bag: '▢',
    user: '◉',
    grid: '▦',
    box: '▧',
    heart: '♡',
    arrow: '→',
    plus: '+',
    minus: '−',
    close: '×',
    check: '✓',
    truck: '▰',
    logout: '↪',
    edit: '✎',
    filter: '☷',
  }

  let iconText = icons[name]

  if (!iconText) {
    iconText = '•'
  }

  return <span className="simple-icon">{iconText}</span>
}

// Обычная кнопка сайта.
export function Button(props) {
  let className = 'button button-primary'

  if (props.variant) {
    className = 'button button-' + props.variant
  }

  if (props.className) {
    className = className + ' ' + props.className
  }

  let buttonType = 'button'
  if (props.type) {
    buttonType = props.type
  }

  return (
    <button
      type={buttonType}
      className={className}
      onClick={props.onClick}
      disabled={props.disabled}
    >
      {props.children}
    </button>
  )
}

// Поле ввода с подписью.
export function Field(props) {
  let inputType = 'text'
  if (props.type) {
    inputType = props.type
  }

  return (
    <label className="field">
      <span>{props.label}</span>
      <input
        type={inputType}
        name={props.name}
        value={props.value}
        onChange={props.onChange}
        placeholder={props.placeholder}
        required={props.required}
        minLength={props.minLength}
        maxLength={props.maxLength}
        min={props.min}
        step={props.step}
      />
    </label>
  )
}

// Показать статус заказа или оплаты.
export function Status({ value }) {
  let color = 'warm'

  if (value === 'paid') {
    color = 'good'
  }
  if (value === 'delivered') {
    color = 'good'
  }

  if (value === 'cancelled') {
    color = 'muted'
  }
  if (value === 'refunded') {
    color = 'muted'
  }

  if (value === 'shipped') {
    color = 'blue'
  }

  return <span className={'status status-' + color}>{getStatusName(value)}</span>
}

// Заголовок страницы личного кабинета.
export function PageTitle(props) {
  return (
    <div className="page-title-row">
      <div>
        <p className="eyebrow">{props.eyebrow}</p>
        <h1>{props.title}<span>.</span></h1>
        {props.subtitle ? <p className="section-subtitle">{props.subtitle}</p> : null}
      </div>
      {props.action}
    </div>
  )
}

// Экран загрузки.
export function PageLoading({ label }) {
  let loadingText = 'Загружаем…'
  if (label) {
    loadingText = label
  }

  return (
    <div className="page-loading">
      <div className="loader" />
      <span>{loadingText}</span>
    </div>
  )
}

// Обычное модальное окно.
export function ModalFrame({ children, onClose }) {
  function closeOnBackground(event) {
    if (event.target === event.currentTarget) {
      onClose()
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={closeOnBackground}>
      <section className="modal-panel form-modal">
        <button className="modal-close" onClick={onClose} aria-label="Закрыть">
          <Icon name="close" />
        </button>
        {children}
      </section>
    </div>
  )
}
