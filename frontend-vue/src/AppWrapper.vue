<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="themeOverrides">
    <n-global-style />
    <n-message-provider>
      <n-notification-provider>
        <AppContent />
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { darkTheme, NConfigProvider, NMessageProvider, NNotificationProvider, NGlobalStyle } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import AppContent from './AppContent.vue'

// Studio Dark Theme - Audio Production Aesthetic
const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#22c55e',
    primaryColorHover: '#16a34a',
    primaryColorPressed: '#15803d',
    primaryColorSuppl: '#22c55e',
    successColor: '#22c55e',
    warningColor: '#f59e0b',
    errorColor: '#ef4444',
    infoColor: '#3b82f6',

    // Backgrounds
    bodyColor: '#0a0a0f',
    cardColor: '#18181bcc',
    modalColor: '#18181b',
    popoverColor: '#18181b',

    // Borders & Dividers
    borderColor: '#27272a',
    dividerColor: '#27272a',

    // Text
    textColor1: '#fafafa',
    textColor2: '#e4e4e7',
    textColor3: '#a1a1aa',
    textColorDisabled: '#52525b',
    placeholderColor: '#71717a',

    // Radius - subtle, professional
    borderRadius: '8px',
    borderRadiusSmall: '6px',

    // Fonts
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif',
    fontFamilyMono: '"Fira Code", "SF Mono", Consolas, "Liberation Mono", Monaco, monospace',
    fontWeight: '400',
    fontWeightStrong: '600',
  },
  Card: {
    borderRadius: '8px',
    paddingMedium: '20px 24px',
    color: 'rgba(24, 24, 27, 0.8)',
    colorEmbedded: 'rgba(24, 24, 27, 0.6)',
    borderColor: '#27272a',
  },
  Button: {
    borderRadiusMedium: '6px',
    paddingMedium: '0 18px',
    heightMedium: '38px',
    fontSizeMedium: '14px',
    fontWeight: '500',
    textColorPrimary: '#ffffff',
    colorPrimary: '#22c55e',
    colorHoverPrimary: '#16a34a',
    colorPressedPrimary: '#15803d',
  },
  Input: {
    borderRadius: '6px',
    heightMedium: '38px',
    paddingMedium: '0 12px',
    color: 'rgba(24, 24, 27, 0.8)',
    colorFocus: 'rgba(24, 24, 27, 0.9)',
    border: '1px solid #27272a',
    borderHover: '1px solid #3f3f46',
    borderFocus: '1px solid #22c55e',
  },
  Select: {
    peers: {
      InternalSelection: {
        borderRadius: '6px',
        heightMedium: '38px',
        color: 'rgba(24, 24, 27, 0.8)',
        border: '1px solid #27272a',
        borderHover: '1px solid #3f3f46',
        borderFocus: '1px solid #22c55e',
      }
    }
  },
  Tabs: {
    tabFontWeightActive: '600',
    tabTextColorActiveSegment: '#fafafa',
    tabTextColorSegment: '#a1a1aa',
    tabBorderColor: '#27272a',
    barColor: '#22c55e',
  },
  Alert: {
    borderRadius: '8px',
  },
  Progress: {
    fillColor: '#22c55e',
    railColor: 'rgba(39, 39, 42, 0.8)',
  },
}
</script>
