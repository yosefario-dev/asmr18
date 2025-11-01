# ASMR18 Downloader

Command-line tool for downloading audio content from ASMR18.fans with metadata extraction and chapter support.

## Installation

### Quick Install (Linux/macOS)
```bash
curl -sSL https://techvoid.co/asmr18.sh | sh
```

### Manual Install
```bash
pip install asmr18
```

## Usage

```bash
asmr18 "https://asmr18.fans/boys/rj01439456/"
```

### Options
```bash
asmr18 URL                           # Download single work
asmr18 URL -o /path/to/output        # Custom output directory
asmr18 --batch urls.txt              # Batch download from file
asmr18 URL --template "{id} {title}" # Custom filename
asmr18 --help                        # Show all options
```

## Features

* Metadata extraction (title, voice actors, circle, scenario, illustrator, genres)
* Chapter extraction and embedding
* Filename filesystem safety
* Multiple download methods (ffmpeg or manual segments)
* Batch download support
* Resume capability for interrupted downloads
* Configuration file support (~/.asmr18/config.yaml)
* Progress tracking with ETA

## Requirements

* Python 3.8+
* ffmpeg (recommended for faster downloads)

## Configuration

Create `~/.asmr18/config.yaml`:
```yaml
output_dir: ~/Downloads/ASMR
template: "[{id}] {title}"
use_ffmpeg: true
skip_existing: true
```

## Output

Downloaded files include:
* Video file with embedded chapters
* Metadata JSON file with complete work information

## Legal

This tool is for personal use only. Users must comply with:
* ASMR18.fans terms of service
* Applicable copyright laws
* Content licensing restrictions

## License

GPL-3.0 License - See LICENSE file

## Support

For issues or questions: https://github.com/yosefario-dev/asmr18/issues