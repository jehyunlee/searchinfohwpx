# search-info-hwpx

Claude Code skill for automated weekly trend report generation in HWPX format.

Searches papers, news, and patents on any given topic using parallel agents, deduplicates results, optionally registers items to Zotero, and produces a Korean HWPX document.

## Features

- **Any topic**: Not limited to a specific field. Works with any research/industry topic.
- **Parallel search**: 3 agents (papers, news, patents) search simultaneously.
- **Deduplication**: URL-based and title-similarity-based (80% threshold) duplicate removal.
- **Zotero integration (optional)**: Auto-registers papers/patents if configured — completely optional, HWPX output works without it.
- **HWPX output**: Generates a native Korean word processor document from a template.
- **Korean output**: All titles and summaries are translated to Korean with noun-ending style.

## Installation

1. Copy this directory to `~/.claude/skills/search-info-hwpx/`
2. Install Python dependency: `pip install lxml`
3. On first run, the skill will ask you to configure:
   - Path to your HWPX template file (`.hwpx`)
   - Output directory for generated reports

Configuration is saved to `config.json` (gitignored).

### Zotero Setup (Optional)

Zotero integration is **entirely optional**. The skill generates HWPX reports without it.

To enable, set the `ZOTERO_API_KEY` environment variable. Your numeric user ID will be **automatically retrieved** via the API.

```bash
export ZOTERO_API_KEY="your_key_here"
```

Get your API key at https://www.zotero.org/settings/keys

The API key is **never** stored in config.json (only the resolved user ID is cached).

## Usage

In Claude Code:

```
/search-info-hwpx 휴머노이드
/search-info-hwpx AI for Science 2주
/search-info-hwpx quantum computing 1개월 --no-zotero
/search-info-hwpx 양자컴퓨팅 출력폴더:D:/reports
```

## HWPX Template

You need to provide your own HWPX template file. The template should contain:
- A title line with "휴머노이드 분야 국내외 동향" (this text gets replaced with your topic)
- A date placeholder `{오늘날짜YY.MM.DD}`
- Repeated entry blocks with `□`, `※`, `○`, `-` markers

## File Structure

```
search-info-hwpx/
├── SKILL.md              # Skill definition (workflow spec)
├── config.json           # User config (gitignored)
├── scripts/
│   ├── build_hwpx.py     # HWPX builder with deduplication
│   ├── fix_namespaces.py # HWPX namespace post-processor
│   └── validate.py       # HWPX structural validator
├── .gitignore
└── README.md
```

## Dependencies

**Required:**
- Python 3.8+
- `lxml` (for HWPX validation)
- Claude Code with `search-info` skill's `info-searcher` agent type

**Optional (Zotero):**
- `ZOTERO_API_KEY` environment variable

## License

MIT
