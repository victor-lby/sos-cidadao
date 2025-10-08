/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2024 S.O.S Cidadão Contributors
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// Pinia store
app.use(createPinia())

// Vue Router
app.use(router)

// Vuetify with Material Design 3 theming
const vuetify = createVuetify({
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          // Material Design 3 color tokens
          primary: '#6750A4',
          'on-primary': '#FFFFFF',
          'primary-container': '#EADDFF',
          'on-primary-container': '#21005D',

          secondary: '#625B71',
          'on-secondary': '#FFFFFF',
          'secondary-container': '#E8DEF8',
          'on-secondary-container': '#1D192B',

          tertiary: '#7D5260',
          'on-tertiary': '#FFFFFF',
          'tertiary-container': '#FFD8E4',
          'on-tertiary-container': '#31111D',

          error: '#BA1A1A',
          'on-error': '#FFFFFF',
          'error-container': '#FFDAD6',
          'on-error-container': '#410002',

          background: '#FFFBFE',
          'on-background': '#1C1B1F',
          surface: '#FFFBFE',
          'on-surface': '#1C1B1F',
          'surface-variant': '#E7E0EC',
          'on-surface-variant': '#49454F',

          outline: '#79747E',
          'outline-variant': '#CAC4D0',
          shadow: '#000000',
          scrim: '#000000',
          'inverse-surface': '#313033',
          'inverse-on-surface': '#F4EFF4',
          'inverse-primary': '#D0BCFF',
        },
      },
      dark: {
        dark: true,
        colors: {
          // Material Design 3 dark theme
          primary: '#D0BCFF',
          'on-primary': '#381E72',
          'primary-container': '#4F378B',
          'on-primary-container': '#EADDFF',

          secondary: '#CCC2DC',
          'on-secondary': '#332D41',
          'secondary-container': '#4A4458',
          'on-secondary-container': '#E8DEF8',

          tertiary: '#EFB8C8',
          'on-tertiary': '#492532',
          'tertiary-container': '#633B48',
          'on-tertiary-container': '#FFD8E4',

          error: '#FFB4AB',
          'on-error': '#690005',
          'error-container': '#93000A',
          'on-error-container': '#FFDAD6',

          background: '#1C1B1F',
          'on-background': '#E6E1E5',
          surface: '#1C1B1F',
          'on-surface': '#E6E1E5',
          'surface-variant': '#49454F',
          'on-surface-variant': '#CAC4D0',

          outline: '#938F99',
          'outline-variant': '#49454F',
          shadow: '#000000',
          scrim: '#000000',
          'inverse-surface': '#E6E1E5',
          'inverse-on-surface': '#313033',
          'inverse-primary': '#6750A4',
        },
      },
    },
  },
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
  defaults: {
    VBtn: {
      style: 'text-transform: none;',
    },
  },
})

app.use(vuetify)

app.mount('#app')
