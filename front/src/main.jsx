import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Найти элемент root в HTML и показать в нём приложение React.
const rootElement = document.getElementById('root')
const root = createRoot(rootElement)

root.render(<App />)
