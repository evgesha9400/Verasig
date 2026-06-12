import React from 'react'
import ReactDOM from 'react-dom/client'
import '@verasig/design-system/styles.css'
import AppRouter from './routes/AppRouter.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppRouter />
  </React.StrictMode>
)
