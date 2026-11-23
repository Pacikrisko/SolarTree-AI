import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'
import './refresh.css'

import {getLanguage} from './language'

document.documentElement.lang=getLanguage()
document.documentElement.dataset.theme = localStorage.getItem('solartree_theme') === 'dark' ? 'dark' : 'light'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>
)
