# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Vue 3 + TypeScript frontend** for Infinite Image Browsing (IIB), a fast image/video browser with infinite scrolling and advanced search capabilities. The project uses Vite as the build tool, supports both web and Tauri desktop app deployment, and integrates with the Python/FastAPI backend.

## Common Development Commands

### Install Dependencies
```bash
yarn
# or
npm install
```

### Run Development Server
```bash
yarn dev        # Starts Vite dev server on port 3002 with backend proxy
```

### Build for Production
```bash
yarn build      # Uses custom tsx build script
```

### Type Checking
```bash
yarn type-check # Runs vue-tsc without emitting files
```

### Lint
```bash
yarn lint       # Runs ESLint
```

### Tauri Desktop App
```bash
yarn tauri          # Run Tauri dev mode
yarn tauri-build    # Build Tauri desktop app
yarn tauri-build-debug # Build debug version
```

## High-Level Architecture

### Tech Stack
- **Framework**: Vue 3 with Composition API and `<script setup>` syntax
- **Language**: TypeScript with Vue 3 TypeScript integration
- **Build Tool**: Vite 4.x with custom tsx-based build script
- **State Management**: Pinia with persisted-state plugin
- **UI Framework**: Ant Design Vue 3.2.20 (customized with orange primary color #d03f0a)
- **Routing**: Vue Router 4.x
- **Internationalization**: vue-i18n 9.x (supports zh-hans, zh-hant, en, de)
- **HTTP Client**: Axios
- **Virtual Scrolling**: @zanllp/vue-virtual-scroller for large datasets
- **Charts**: ECharts 6.x
- **Code Highlighting**: highlight.js 11.x
- **Image Preview/Manipulation**: Custom implementations using sjcl, vue3-colorpicker
- **Desktop App**: Tauri 1.4.x (Rust backend)

### Project Structure

```
vue/
├── src/
│   ├── api/                    # API client functions
│   │   ├── db.ts              # Database endpoints (search, tags, embeddings)
│   │   ├── files.ts           # File operations (move, copy, delete)
│   │   ├── index.ts           # Base API configuration & interceptors
│   │   └── organize.ts        # AI-powered file organization APIs
│   │
│   ├── components/             # Reusable UI components
│   │   ├── FileItem.vue       # Individual file/image item display
│   │   ├── ContextMenu.vue    # Right-click context menu
│   │   ├── MultiSelectKeep.vue# Multi-selection state management
│   │   ├── ExifBrowser.vue    # Generation info/EXIF viewer
│   │   ├── PromptEditorModal.vue # Prompt editing interface
│   │   └── ...
│   │
│   ├── page/                   # Page views (main application routes)
│   │   ├── gridView/          # Grid view for browsing images
│   │   ├── TagSearch/         # Tag-based filtering UI
│   │   ├── TopicSearch/       # Semantic topic clustering UI
│   │   ├── ImgSli/            # "Image Similarity" comparison tools
│   │   ├── batchDownload/     # Batch download functionality
│   │   ├── SplitViewTab/      # Tabbed split-view file explorer
│   │   ├── globalSetting/     # Application settings
│   │   ├── Trend/             # Statistics and trend charts
│   │   └── randomImage/       # Random image browsing
│   │
│   ├── store/                  # Pinia state management stores
│   │   ├── useGlobalStore.ts  # Global app state (tabs, panes, layout)
│   │   ├── useTagStore.ts     # Tags and tag relationships
│   │   ├── useBatchDownloadStore.ts
│   │   ├── useImgSli.ts       # Image similarity UI state
│   │   └── ...
│   │
│   ├── util/                   # Utility functions
│   │   ├── path.ts            # Path manipulation utilities
│   │   ├── file.ts            # File operation helpers
│   │   ├── video.ts           # Video thumbnail/cover generation
│   │   ├── shortcut.ts        # Keyboard shortcuts
│   │   ├── stable-diffusion-image-metadata.ts # SD metadata parsing
│   │   └── const.ts           # Constants and type definitions
│   │
│   ├── i18n/                   # Internationalization
│   │   ├── index.ts           # i18n configuration
│   │   ├── en.ts, zh-hans.ts, zh-hant.ts, de.ts
│   │
│   ├── icon/                   # Icon registrations (Ant Design icons)
│   ├── main.ts                 # Application entry point
│   └── App.vue                 # Root component
│
├── src-tauri/                  # Tauri Rust backend (desktop app)
│   └── tauri.conf.json
│
├── build                       # Custom build configuration (tsx)
├── vite.config.ts              # Vite configuration
└── package.json
```

### Key State Management Patterns

#### useGlobalStore.ts
Central state management for the application's tab/pane architecture:
- Manages multiple tabs, each containing multiple panes
- Supports different pane types: `grid-view`, `local`, `tag-search`, `topic-search`, etc.
- Handles active pane selection and navigation
- Exports functions for embedding IIB in other applications (Gradio integration)

#### Pinia Store Architecture
Stores are modular and use composables pattern:
- Stores persist to localStorage via `pinia-plugin-persistedstate`
- Stores can be auto-tagged based on current active pane
- Example: `[useGlobalStore.currentPaneKey]` dynamic persistence keys

### Core Features

#### View Types
1. **Grid View**: Virtualized grid of images with tags, infinite scroll
2. **Local View**: Filesystem directory browsing
3. **Tag Search**: Match images by AND/OR/NOT tag combinations
4. **Topic Search**: Semantic topic clustering using embeddings
5. **Random Image**: Random browsing interface
6. **Split View**: Side-by-side file comparison/transfer

#### Key Utilities

**path.ts**: Path manipulation for cross-platform compatibility (Windows/Linux/macOS)

**video.ts**: Video handling including cover frame extraction and caching

**stable-diffusion-image-metadata.ts**: Parses generation parameters from SD WebUI, ComfyUI, Fooocus, NovelAI formats

**shortcut.ts**: Keyboard shortcut management integrated with Ant Design Vue's `useFullscreenLayout`

**smartOrganize.ts**: AI-powered automatic file organization configuration and workflow

#### API Layer
Located in `src/api/index.ts`:
- Base URL configured via Vite environment variables (`VITE_IIB_BASE`)
- Default: `http://127.0.0.1:8000/infinite_image_browsing/`
- Request/response interceptors for error handling and auth
- Typed request/response interfaces in `src/api/type.ts`

### Build Configuration Highlights

**vite.config.ts**:
- Proxy config for dev server (`/infinite_image_browsing/` → `http://127.0.0.1:8000/`)
- Auto-imports for Ant Design Vue components via `unplugin-vue-components`
- CSS preprocessor options with Ant Design theme customization
- JSX support via `@vitejs/plugin-vue-jsx`
- Different base paths for dev ( `/` ) vs production ( `/infinite_image_browsing/fe-static` )

**Custom Build Script** (`build` folder):
- Uses `tsx` instead of `tsc` for faster TypeScript compilation
- Handles asset optimization and bundling for production

### Integration Points

#### Gradio Embedding
The application can be embedded in Gradio apps via JavaScript injection. See `vue/usage.md` for complete API documentation on:
- Inserting tab panes programmatically
- Accessing file lists and manipulating views
- Creating grid views with file/tag associations

#### Tauri Desktop App
- Rust backend defined in `src-tauri/`
- Communicates with Vue frontend via Tauri event system
- Provides native OS integration and improved performance

### Internationalization (i18n)

Multi-language support implemented via `vue-i18n`:
- Languages: Simplified Chinese (zh-hans), Traditional Chinese (zh-hant), English (en), German (de)
- Messages organized by feature/module in each language file
- Dynamic locale switching at runtime

### Testing

Frontend testing setup (check `package.json` for test scripts if available):
```bash
# Run tests if configured
npm test
```

For Tauri tests, check `src-tauri` directory for Rust test commands.

### Development Notes

1. **Hot Reload**: Vite dev server automatically reloads on file changes
2. **Type Safety**: Use `vue-tsc` for type checking; avoid `any` types where possible
3. **Component Naming**: Follow Vue naming conventions (PascalCase for components)
4. **Ant Design Icons**: Register in `src/icon/index.ts` before use
5. **Async Operations**: Use async/await pattern consistently; handle errors in API calls
6. **Virtual Scrolling**: For large datasets (1000+ items), ensure virtual scroller is used
7. **Path Handling**: Always use normalized paths; backend may send Windows or Unix-style paths

### Environment Variables

Check `vite.config.ts` for available env prefixes:
- `VITE_` - Frontend-only environment variables
- `TAURI_` - Tauri-specific environment variables

Example `.env` setup:
```env
VITE_IIB_BASE=http://127.0.0.1:8000/infinite_image_browsing
```
