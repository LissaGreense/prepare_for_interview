import pluginVue from 'eslint-plugin-vue'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

export default defineConfigWithVueTs(
  { name: 'app/files', files: ['**/*.{ts,mts,tsx,vue}'] },
  { name: 'app/ignores', ignores: ['dist/**', 'coverage/**'] },
  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,
  skipFormatting,

  // Page-level view components are rendered via `<component :is>` (not as
  // in-template custom tags), so single-word names like `Quiz`/`Results` can't
  // collide with native HTML elements. Renaming them would be a behavioral
  // restructure, so relax the multi-word rule for the views directory only.
  {
    name: 'app/views-single-word-ok',
    files: ['src/views/**/*.vue'],
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
)
