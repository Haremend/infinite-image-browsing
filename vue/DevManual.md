# Developer Manual - Vue Frontend

This document provides development guidance for extending the Infinite Image Browsing Vue frontend.

## Table of Contents

- [Page Layout Structure](#page-layout-structure)
- [Adding Toolbar Buttons](#adding-toolbar-buttons)
- [Internationalization](#internationalization)
- [State Management](#state-management)
- [API Integration](#api-integration)

---

## Page Layout Structure

### Core Architecture Files

| File | Purpose |
|------|---------|
| [`src/App.vue`](src/App.vue) | Root application container |
| [`src/page/SplitViewTab/SplitViewTab.vue`](src/page/SplitViewTab/SplitViewTab.vue) | Multi-tab and split-pane layout manager |
| [`src/page/fileTransfer/stackView.vue`](src/page/fileTransfer/stackView.vue) | Main file browser view with toolbar |
| [`src/store/useGlobalStore.ts`](src/store/useGlobalStore.ts) | Global state management (Pinia store) |

### Layout Hierarchy

```
App.vue
└── SplitViewTab.vue (multi-tab container)
    └── Tab Pane (each type mapped to component)
        ├── grid-view → gridView.vue
        ├── local → stackView.vue
        ├── tag-search → TagSearch.vue
        └── other views...
```

### Key Components

**SplitViewTab.vue** manages:
- Multiple tabs (browser tabs)
- Each tab contains multiple panes (panels)
- Different pane types: `grid-view`, `local`, `tag-search`, `topic-search`, etc.

**stackView.vue** is the main file browser containing:
- **Location Bar** (`location-bar`) - Top toolbar with navigation and actions
- **File List** (`file-list`) - Virtualized grid of images using `RecycleScroller`
- **Bottom Info Bar** (`BaseFileListInfo`) - File count and selection status

---

## Adding Toolbar Buttons

There are two main toolbar locations in the application:

### Location 1: Main File Browser Top Toolbar

Located in [`src/page/fileTransfer/stackView.vue`](src/page/fileTransfer/stackView.vue), lines 290-378.

#### Steps to Add a Button

**1. Add the button HTML in the template:**

Find the `.actions` div (around line 290) and add your button:

```vue
<div class="actions">
  <!-- Existing buttons -->
  <a class="opt" @click.prevent="refresh"> {{ $t('refresh') }} </a>
  <a class="opt" @click.prevent="onTiktokViewClick">{{ $t('TikTok View') }}</a>
  
  <!-- YOUR NEW BUTTON HERE -->
  <a class="opt" @click.prevent="yourCustomAction">{{ $t('yourButtonLabel') }} </a>
  
  <!-- More existing buttons... -->
</div>
```

**2. Add the handler method in the script:**

Add your function in the `<script setup>` section:

```typescript
import { message } from 'ant-design-vue'

// Add your handler function
const yourCustomAction = () => {
  // Your implementation here
  console.log('Custom button clicked!')
  message.success('Button clicked successfully!')
}
```

**3. Add translations:**

Add the button label to all i18n files:

[`src/i18n/zh-hans.ts`](src/i18n/zh-hans.ts):
```typescript
export const zhHans = {
  // ... existing translations
  yourButtonLabel: '中文按钮标签',
}
```

[`src/i18n/en.ts`](src/i18n/en.ts):
```typescript
export const en = {
  // ... existing translations
  yourButtonLabel: 'Your Button Label',
}
```

[`src/i18n/de.ts`](src/i18n/de.ts) and [`src/i18n/zh-hant.ts`](src/i18n/zh-hant.ts):
```typescript
export const de = {
  // ... existing translations
  yourButtonLabel: 'Deutsche Beschriftung',
}

export const zhHant = {
  // ... existing translations
  yourButtonLabel: '繁體中文標籤',
}
```

#### Complete Example: Export Current Folder Button

Here's a complete example adding an "Export Current Folder" button:

**In stackView.vue template (add after line 310):**
```vue
<a class="opt" @click.prevent="exportCurrentFolder">{{ $t('exportFolder') }} </a>
```

**In stackView.vue script (add after existing functions):**
```typescript
const exportCurrentFolder = async () => {
  try {
    message.loading({ content: t('exporting'), key: 'export', duration: 0 })
    // Add your export logic here
    // You can access currLocation.value for the current path
    console.log('Exporting folder:', currLocation.value)
    
    // Simulate export
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    message.destroy('export')
    message.success(t('exportSuccess'))
  } catch (e: any) {
    message.destroy('export')
    message.error(e.message || String(e))
  }
}
```

**In i18n files:**
```typescript
// zh-hans.ts
export: '导出',
exportFolder: '导出当前文件夹',
exporting: '正在导出...',
exportSuccess: '导出成功!',

// en.ts
export: 'Export',
exportFolder: 'Export Current Folder',
exporting: 'Exporting...',
exportSuccess: 'Export successful!',
```

### Location 2: Search Results Action Bar

Located in these files for tag/topic search results:

- [`src/page/TagSearch/MatchedImageGrid.vue`](src/page/TagSearch/MatchedImageGrid.vue) - Line 133
- [`src/page/TopicSearch/MatchedImageGrid.vue`](src/page/TopicSearch/MatchedImageGrid.vue) - Line 144

Example structure:
```vue
<div class="action-bar">
  <div class="title line-clamp-1">🧩 {{ props.title }}</div>
  <div flex-placeholder />
  <a-button @click="onTiktokViewClick" :disabled="!images?.length">{{ $t('tiktokView') }}</a-button>
  <a-button @click="saveLoadedFileAsJson">{{ $t('saveLoadedImageAsJson') }}</a-button>
  
  <!-- Your button here -->
  <a-button @click="yourAction">{{ $t('yourLabel') }}</a-button>
</div>
```

### Location 3: Fullscreen Preview Context Menu

Located in [`src/page/fileTransfer/fullScreenContextMenu.vue`](src/page/fileTransfer/fullScreenContextMenu.vue). This appears when viewing an image in fullscreen mode.

The action bar is around line 502, controlled by `global.fullscreenMenuBlockVisibility.actionBar`.

---

## Using Ant Design Vue Components

The project uses Ant Design Vue 3.2.20. Available components include:

```vue
<script setup>
import { 
  AButton, 
  AModal, 
  ADropdown, 
  AInput,
  AForm,
  ASelect,
  // ... more components
} from 'ant-design-vue'
</script>

<template>
  <a-button type="primary">Primary Button</a-button>
  <a-dropdown>
    <a class="ant-dropdown-link">Dropdown</a>
    <template #overlay>
      <a-menu>
        <a-menu-item>Item 1</a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
</template>
```

For icon imports:
```typescript
import { DownOutlined, SearchOutlined } from '@ant-design/icons-vue'
```

---

## Internationalization

All user-facing text must be translated. The project supports:
- Simplified Chinese (`zh-hans`)
- Traditional Chinese (`zh-hant`)
- English (`en`)
- German (`de`)

### Adding New Translation Keys

1. Find the translation key you want to use (should be unique and descriptive)
2. Add it to all four language files in their respective sections
3. Use `$t('keyName')` in templates or `t('keyName')` in script

### Translation File Structure

Each i18n file exports a default object with all translations. Keep keys organized alphabetically where possible.

---

## State Management

### Using the Global Store

```typescript
import { useGlobalStore } from '@/store/useGlobalStore'

const global = useGlobalStore()

// Access reactive state
console.log(global.tabList)
console.log(global.fullscreenMenuBlockVisibility)

// Call methods
global.saveRecord()
```

### Common Global Store Properties

| Property | Type | Description |
|----------|------|-------------|
| `tabList` | `Tab[]` | All tabs and their panes |
| `fullscreenMenuBlockVisibility` | `object` | Visibility control for fullscreen UI elements |
| `quickMovePaths` | `array` | Quick move destination paths |
| `shortcut` | `object` | Keyboard shortcuts mapping |

---

## API Integration

### Making API Calls

The project uses Axios wrapped in API modules:

```typescript
import { getFileList, matchImagesByTags } from '@/api/db'
import { deleteFiles } from '@/api/files'
import { startOrganizeJob } from '@/api/organize'

// Example usage
const files = await getFileList(folderPath)
await deleteFiles(pathsToDelete)
```

### Available API Modules

| Module | Path | Functions |
|--------|------|-----------|
| Database | `@/api/db.ts` | Search, tags, embeddings, random images |
| Files | `@/api/files.ts` | Move, copy, delete, flatten folder |
| Organize | `@/api/organize.ts` | AI-powered file organization |

### Error Handling Pattern

```typescript
try {
  const result = await someApiCall()
  // Handle success
} catch (e: any) {
  message.error(e.message || String(e))
}
```

---

## Common Patterns

### Accessing Current File/Location

In `stackView.vue`, you have access to:
```typescript
const { currLocation, sortedFiles, multiSelectedIdxs } = useLocation()
const { cellWidth, sortMethod } = useFilesDisplay()

console.log(currLocation.value)      // Current folder path
console.log(sortedFiles.value)       // Currently displayed files
console.log(multiSelectedIdxs.value) // Selected file indices
```

### Emitting Global Events

```typescript
import { globalEvents } from '@/util'

// Emit event
globalEvents.emit('yourCustomEvent', { data: 'value' })
```

### Using Pinia Store with Persistence

```typescript
import { useTagStore } from '@/store/useTagStore'

const tagStore = useTagStore()
// Stores automatically persist to localStorage via pinia-plugin-persistedstate
```

---

## Styling Guidelines

### CSS Variables

The project uses CSS custom properties for theming:
```scss
background: var(--zp-primary-background);
secondary-bg: var(--zp-secondary-background);
border: var(--zp-border);
```

### Scoped Styles

Always use `<style scoped>` for component-specific styles. Use SCSS for advanced features like nested selectors.

### Responsive Design

The app adapts to different screen sizes. For mobile optimization (< 768px), wrap flexible content:

```scss
@media (max-width: 768px) {
  .container {
    flex-direction: column;
    overflow-x: auto;
  }
}
```

---

## Debugging Tips

1. **Enable Vue DevTools** in browser for React-like component inspection
2. **Console logging**: Use `console.log()` freely during development
3. **Pinia DevTools**: Install browser extension to inspect state changes
4. **Network panel**: Check API requests and responses

---

## Building for Production

```bash
yarn install          # Install dependencies
yarn build            # Build optimized production bundle
```

Build output goes to `dist/` directory.

---

## Quick Reference

### Adding a Simple Button - 3 Steps Summary

1. **Template**: Add button in `.actions` or `.action-bar` div
2. **Script**: Add click handler function
3. **i18n**: Add translation keys to all language files

### Component Locations Quick Links

| Component | File Path |
|-----------|-----------|
| Main file browser | [`src/page/fileTransfer/stackView.vue`](src/page/fileTransfer/stackView.vue) |
| Grid view | [`src/page/gridView/gridView.vue`](src/page/gridView/gridView.vue) |
| Tag search results | [`src/page/TagSearch/MatchedImageGrid.vue`](src/page/TagSearch/MatchedImageGrid.vue) |
| Topic search results | [`src/page/TopicSearch/MatchedImageGrid.vue`](src/page/TopicSearch/MatchedImageGrid.vue) |
| Fullscreen menu | [`src/page/fileTransfer/fullScreenContextMenu.vue`](src/page/fileTransfer/fullScreenContextMenu.vue) |
| Global store | [`src/store/useGlobalStore.ts`](src/store/useGlobalStore.ts) |
