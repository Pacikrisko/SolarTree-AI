import '@radix-ui/themes/tokens/base.css'
import '@radix-ui/themes/tokens/colors/sage.css'
import '@radix-ui/themes/tokens/colors/grass.css'
import '@radix-ui/themes/components.css'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import ClientVersion from './ClientVersion'
import './styles.css'
import './refresh.css'
import './solar-theme.css'
import './stellar-layout.css'

import {getLanguage} from './language'

document.documentElement.lang=getLanguage()
document.documentElement.dataset.theme = localStorage.getItem('solartree_theme') === 'dark' ? 'dark' : 'light'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><ClientVersion><App /></ClientVersion></React.StrictMode>
)

