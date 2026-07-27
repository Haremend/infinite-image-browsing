# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Infinite Image Browsing (IIB)** - A fast image/video browser with infinite scrolling and advanced search capabilities. It parses metadata from AI generation tools including:
- Stable Diffusion Web UI / Stealth
- ComfyUI
- Fooocus
- NovelAI
- StableSwarmUI
- Invoke.AI
- Pixiv (via separate plugin)

## Running the Application

### Standalone Mode
```bash
# Basic startup
python app.py --port <port>

# With SD WebUI config
python app.py --sd_webui_config path/to/config.json --update_image_index

# Pre-generate caches for performance
python app.py --generate_video_cover --generate_image_cache
```

### As SD WebUI Extension
Install via Extensions tab → Install from URL: `https://github.com/zanllp/sd-webui-infinite-image-browsing`

### Desktop App
Download pre-compiled executables from releases page. For custom builds, see `.github/workflows/tauri_app_build.yml`.

## Common Development Tasks

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt
```

### Building Vue Frontend
```bash
cd vue
npm install
npm run build
```

### Updating Index
```bash
python app.py --update_image_index
```

### Preview Changes
After making changes, rebuild Vue and restart server:
```bash
cd vue && npm run build && cd ..
python app.py
```

## Core Architecture

### Backend (Python/FastAPI)
Located in `scripts/iib/`:

| Module | Purpose |
|--------|---------|
| `api.py` | FastAPI route registration, middleware, core endpoints |
| `db/datamodel.py` | SQLite database models (Image, Tag, Folder, ExtraPath, etc.) |
| `db/update_image_data.py` | Image indexing and scanning logic |
| `parsers/` | Metadata parsers for each AI tool (ComfyUI, SD WebUI, Fooocus, etc.) |
| `tool.py` | Utility functions (paths, dates, file operations) |
| `organize_files.py` | AI-powered automatic file organization |
| `topic_cluster.py` | Semantic clustering using embeddings |
| `tag_graph.py` | Tag relationship graph visualization |
| `trend.py` | Statistics and trend charts |

### Database Schema (`iib.db`)
Key tables:
- `image` - Image paths, EXIF, size, date
- `image_tag`, `tag` - Tag assignments and definitions
- `folder` - Directory structure
- `extra_path` - User-added browsable paths
- `image_embedding` - Semantic embedding vectors
- `topic_title_cache`, `topic_cluster_cache` - Clustering results

### Frontend (Vue 3 + TypeScript)
Located in `vue/src/`:

| Directory | Purpose |
|-----------|---------|
| `components/` | Reusable UI components |
| `page/` | Page views (search, grid, preview, etc.) |
| `api/` | API client functions |
| `store/` | Vuex/Pinia state management |
| `util/` | Utility functions |
| `i18n/` | Internationalization (zh-hans, en, de, etc.) |

## Key Configuration Variables (from `.env.example`)

| Variable | Purpose |
|----------|---------|
| `IIB_SECRET_KEY` | Authentication key |
| `OPENAI_BASE_URL` | OpenAI-compatible API endpoint |
| `OPENAI_API_KEY` | API key for embeddings/chat |
| `EMBEDDING_MODEL` | Model for semantic embeddings (default: `text-embedding-3-small`) |
| `AI_MODEL` | Default chat model (for topic titles) |
| `IIB_ACCESS_CONTROL` | File system access control (`auto`, `enable`, `disable`) |
| `IIB_CACHE_DIR` | Cache directory for thumbnails/video covers |

### Optional Features

**TwelveLabs Marengo Embeddings:** Set `EMBEDDING_MODEL=marengo3.0` and install `twelvelabs>=1.2.8`.

**Prompt Normalization:** Enable `IIB_PROMPT_NORMALIZE=1` to strip boilerplate terms before embedding for better clustering.

## API Endpoints

Base URL: `/infinite_image_browsing` (or your configured base)

### Search & Browse
- `GET /files?folder_path=...` - List folder contents
- `POST /db/search_by_substr` - Keyword regex search
- `POST /db/match_images_by_tags` - Tag-based filtering (AND/OR/NOT)
- `GET /db/random_images` - Random image browsing

### Metadata
- `GET /image_geninfo?path=...` - EXIF/generation parameters
- `GET /db/basic_info` - Tags, models, Lora statistics

### File Operations
- `POST /move_files`, `/copy_files`, `/delete_files`
- `POST /db/add_custom_tag`, `/batch_update_image_tag`

### Advanced
- `POST /db/organize_files_start` - AI-powered organization
- `POST /db/cluster_iib_output_job_start` - Image clustering
- `POST /db/build_iib_output_embeddings` - Build embeddings for NLP features

See `skills/iib/references/api-reference.md` for complete API documentation.

## Parsers Architecture

Each AI tool has its own parser in `scripts/iib/parsers/`:

```
parsers/
├── index.py        # Parser factory/dispatcher
├── model.py        # Base classes (ImageGenerationParams, ImageGenerationInfo)
├── sd_webui.py     # Standard SD WebUI formats
├── sd_webui_stealth.py   # Stealth extension format (disabled by default)
├── comfyui.py      # ComfyUI workflow JSON extraction
├── fooocus.py      # Fooocus metadata parsing
├── novelai.py      # NovelAI format
├── stable_swarm_ui.py
└── invoke_ai.py
```

When a new parser is added, register it in `parsers/index.py`.

## Performance Considerations

1. **Caching**: Thumbnails at configurable resolution (default 512px). Generate upfront with `--generate_image_cache`.
2. **Indexing**: Incremental updates on folder changes. Full rebuild triggers via `/rebuild_index` or CLI.
3. **Embeddings**: Cached per prompt hash to avoid repeated API calls. Use `force=true` to regenerate.
4. **Database**: Uses thread-local SQLite connections. WAL mode disabled for compatibility.

## Testing

The project uses Python's standard testing framework. Tests are located alongside modules they test. Run specific tests:

```bash
python scripts/iib/test_marengo_embedding.py
```

For frontend tests, check `vue/package.json` scripts.

## Development Notes

- The backend uses thread-local storage for SQLite connections (`DataBase.get_conn()`)
- Access control is enforced at multiple layers (file paths, API permissions)
- Secret key authentication uses SHA256 hashing with salt (`_ciallo`)
- All timestamps stored as ISO strings; file stats use Unix epoch internally
- Path handling uses `os.path.normpath()` for cross-platform consistency

## AI Agent Integration

When using with AI agents (Claude Code, Cursor, etc.):
1. Always start IIB service first
2. Ask user for port if not using default
3. Test connectivity with hello endpoint before other operations

See `docs/ai-agents.md` for agent usage patterns and `skills/iib/SKILL.md` for complete skill documentation.
