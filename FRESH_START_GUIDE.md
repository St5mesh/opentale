# Fresh Start Guide - OpenTale

## Overview
The OpenTale application now supports **completely fresh starts** - you can delete the entire `book_output` folder and the app will automatically initialize all necessary state files on the first request.

## Why This Matters
- **Testing**: Delete `book_output` to start fresh testing runs
- **Clean Slate**: No leftover state from previous book projects
- **Automatic Recovery**: App self-heals by creating required files

## How to Start Fresh

### Option 1: Delete via Docker (Safe)
```bash
cd /home/st5mesh/opentale

# Stop containers
docker compose down

# Delete entire book_output
rm -rf book_output

# Restart containers
docker compose up -d
```

### Option 2: Delete on Host (Quick)
```bash
rm -rf /home/st5mesh/opentale/book_output
```
The next request to the web UI will auto-initialize everything.

### Option 3: Manual Reset via UI
Simply navigate to http://localhost:5000 - the app will:
1. Detect missing state files
2. Create `book_output/chapters` directory
3. Initialize all required state files:
   - `story_state.json` - Global narrative state
   - `scene_chain.json` - Chapter scene mapping
   - `character_arcs.json` - Character development tracking
   - `theme.json` - Theme/setting state

## What Gets Auto-Created

When `book_output` is missing, these files are automatically created:

| File | Purpose | Size |
|------|---------|------|
| `story_state.json` | Current narrative state | ~191 bytes |
| `scene_chain.json` | Scene structure for chapters | ~126 bytes |
| `character_arcs.json` | Character development tracking | ~22 bytes |
| `theme.json` | Theme/setting tracking | ~124 bytes |
| `chapters/` | Directory for chapter files | (created on demand) |

## Workflow

1. **Delete book_output** - Remove all existing project files
2. **Start fresh** - App auto-initializes state files
3. **Create new book** - Fill in topic/world/characters as usual
4. **Finalize outline** - Phase 1 extracts and populates states
5. **Generate chapters** - Phase 2-4 work with fresh state

## Testing Scenarios

### Scenario 1: Fresh Book Creation
```bash
rm -rf book_output
# Visit http://localhost:5000
# Fill in book topic → world → characters → outline
# All states are fresh and clean
```

### Scenario 2: Rapid Iteration
```bash
# After each test iteration
rm -rf book_output
# Containers stay up, just state is reset
curl http://localhost:5000  # Triggers auto-init
# New iteration ready
```

### Scenario 3: Recovery from Corruption
```bash
# If any state file gets corrupted
rm -rf book_output
# App auto-fixes everything
```

## Files Created on Demand

During the book creation process, additional files are created:

| File | Created When | Purpose |
|------|------------|---------|
| `world.txt` | World page completed | World description |
| `characters.txt` | Characters page completed | Character profiles |
| `outline.txt` | Outline page completed | Full chapter outline |
| `outline.json` | Outline page completed | Structured outline data |
| `chapters/chapter_N.txt` | Chapter generated | Individual chapter content |
| `chapters/chapter_N_scenes/scene_M.txt` | Scene generated | Individual scene content |

## Technical Details

### Auto-Initialization Process
1. App loads on first request
2. `ensure_state_files_exist()` is called
3. Checks if state files exist
4. If missing, `os.makedirs('book_output/chapters', exist_ok=True)` creates directories
5. Initializes all required state files with empty/default values
6. App is ready for use

### State File Defaults

**story_state.json** (empty state):
```json
{
  "topic": "",
  "world_theme": "",
  "characters": [],
  "artifacts": [],
  "world_elements": [],
  "thematic_elements": [],
  "character_arcs": {},
  "current_chapter": 0
}
```

**scene_chain.json** (empty):
```json
{
  "chapter_scenes": {}
}
```

**character_arcs.json** (empty):
```json
[]
```

**theme.json** (empty):
```json
{}
```

## Troubleshooting

### Q: I deleted book_output but still get errors
**A**: Ensure containers are running and make a request to http://localhost:5000. Check logs:
```bash
docker logs opentale-web | tail -20
```

### Q: Where are my files after delete?
**A**: They're permanently deleted from `book_output/`. If you need them, back up before deleting:
```bash
cp -r book_output book_output_backup
rm -rf book_output
```

### Q: Can I partially delete?
**A**: Yes! You can delete specific files:
```bash
rm book_output/world.txt          # Delete world, keep others
rm -rf book_output/chapters       # Delete all chapters
```
The app will handle it gracefully.

### Q: Do state files in Docker volume persist?
**A**: The `book_output/` volume is mounted in `docker-compose.yml`:
```yaml
volumes:
  - ./book_output:/app/book_output
```
Files persist between container restarts. To truly reset, delete from your host machine.

## Best Practices

✅ **DO:**
- Backup `book_output` before major testing
- Delete fresh for each new test run
- Check logs if auto-init seems stuck

❌ **DON'T:**
- Delete while a request is being processed
- Delete individual critical files unless you know why
- Assume deleted files are recoverable

## Summary

**Fresh starts are now fully supported and automatic!**
- ✅ Delete `book_output` anytime
- ✅ App auto-heals on first request  
- ✅ No manual file creation needed
- ✅ Clean slate for testing
