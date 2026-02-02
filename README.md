<p align="center">
  <img width="451px" src="https://raw.githubusercontent.com/STiXzoOR/taggarr/refs/heads/main/assets/logo/banner_transparent.png" alt=""></img>
  <p></p>
</p>

> **Note:** This is a fork of [BassHous3/taggarr](https://github.com/BassHous3/taggarr) with additional features including native installation support, multi-instance configuration, and improved test coverage.

> [!TIP]
>
> - **Don't feel like watching subs?**
> - **You have no idea which of your content is dubbed?**
> - **Or not sure if Sonarr got the right dub?**
>
> **Don't worry, I got you covered.**
>
> **So finally.. you'll be able to filter by dubbed shows.**
>
> <img width="158" height="386" alt="image" src="https://github.com/user-attachments/assets/ee3a6357-668f-436b-8afe-6425647fb87a" />

Started this project for the exact same questions. I felt other people could make use of it as well and here we are.

Taggarr is a tool for scanning and tagging your media content whether if your media is dubbed in your language you desire or not. If Taggarr finds another language other than Original Language and your Target Languages, it will mark it as "wrong-dub" using Sonarr and Kodi standard tagging system.

This way, you can filter your shows based on if they're dubbed or not, using tags within your Sonarr (for managing) or any media player that supports tagging (for watching). Taggarr will also save all the information in a JSON file and will tell you which show, season, episode and language is the wrong-dub.
<br></br>

> [!NOTE]
> **How it Works:**
>
> - `NO TAG` The show is only in its original language.
> - `DUB` The show contains ALL of your target languages.
> - `SEMI-DUB` The show missing at least one of your target languages or some episodes are missing the dub.
> - `WRONG-DUB` The show is missing your target languages and contains another language (excluding original language).
> - `ADD_TAG_TO_GENRE` The tag list in the media players can be massive. This function will add the tag `Dub` in the genre section only for `DUB` shows. From version [0.4.19](https://github.com/STiXzoOR/taggarr/releases/tag/0.4.19).

> [!IMPORTANT]
> **Quick Start:**
>
> 1. **Sonarr**  
>    Make sure you have `METADATA` turned on with KODI/Emby Standard and all checkboxes are turned on.
> 2. **Docker**  
>    Pull the Docker image from `docker.io/stixzoor/taggarr:latest`
> 3. **Configs**  
>    Make sure to use `/tv` as path to your **CONTAINER** (not host). Check out [example of yaml configs](https://github.com/STiXzoOR/taggarr?tab=readme-ov-file#configuration-example) below.
> 4. **Media players**  
>    After tags are applied they should work in the media players, if not, scan TV's library metadata using `Replace all metadata` method (leave `Replace Images` unchecked).

<br></br>
[![GitHub last commit](https://img.shields.io/github/release-date/STiXzoOR/taggarr?style=for-the-badge&logo=github)](https://github.com/STiXzoOR/taggarr)
[![Latest tag](https://img.shields.io/docker/v/stixzoor/taggarr?style=for-the-badge&logo=docker)](https://hub.docker.com/r/stixzoor/taggarr)
[![Docker pulls](https://img.shields.io/docker/pulls/stixzoor/taggarr?style=for-the-badge&logo=docker)](https://hub.docker.com/r/stixzoor/taggarr)
[![Discord](https://img.shields.io/discord/1387237436765241344?style=for-the-badge&logo=discord)](https://discord.com/invite/uggq7JQk89)

<br></br>

<div align="center">
  
<table>
  <tr>
    <th colspan="3" align="center">Upcoming Updates</th>
  </tr>
  <tr>
    <th>Support for all languages</th>
    <th>Support for Radarr</th>
    <th>Filter scanning by genre</th>
  </tr>
  <tr>
    <td align="center"><img src="https://img.shields.io/badge/Status-Ready-green?style=flat-square" /></td>
    <td align="center"><img src="https://img.shields.io/badge/Status-Ready-green?style=flat-square" /></td>
    <td align="center"><img src="https://img.shields.io/badge/Status-Ready-green?style=flat-square" /></td>
  </tr>
    <tr>
    <th colspan="1" align="center">Support for multiple instances</th>
    <th colspan="1" align="center">Native Installation (uv)</th>
    <th colspan="1" align="center">Tag in genre</th>
  </tr>
  <tr>
    <th colspan="1" align="center"><img src="https://img.shields.io/badge/Status-Ready-green?style=flat-square" /></td>
    <th colspan="1" align="center"><img src="https://img.shields.io/badge/Status-Ready-green?style=flat-square" /></td>
    <th colspan="1" align="center"><img src="https://img.shields.io/badge/Status-Ready-green?style=flat-square" /></td>
  </tr>
  <tr>
    <th colspan="3" align="center">UI</th>
  </tr>
  <tr>
    <th colspan="3" align="center"><img src="https://img.shields.io/badge/Status-Ready-green?style=flat-square" /></td>
  </tr>
</table>

</div>
<br>

<h3 align="center"> Found this project helpful? Hit the star ⭐️ at the top right corner. </h3> 
<br>

</div>

<h3 align="center"> Support the original author (BassHous3) with a coffee: </h3>
<h3 align="center"> <a href="https://ko-fi.com/basshouse" target="_blank"><img src="https://cdn.prod.website-files.com/5c14e387dab576fe667689cf/670f5a0172b90570b1c21dab_kofi_logo.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 150px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a> </h3> <br><br>

## INFO & QUICK START

> [!NOTE]
> **Features:**
>
> - Taggarr will save the information of your media in a JSON file located at the root folder of your TV media.
> - Taggarr uses a lightweight scanning method, it reads the name of audio tracks. It DOES NOT scan the audio of your content.
> - Once your library was scanned and indexed in the JSON file, it will only scan for new or modified folders.
> - `QUICK_MODE` `(Bool)` Checks only first video of every season.
> - `TARGET_LANGUAGES` `(Str)` Seperated via comma, you can add multiple languages as your target.
> - `TARGET_GENRE` `(Str)` Filter scan by genre. ie. `Anime`.
> - `TAG_DUB` `(Str)` Optional custom tag.
> - `TAG_SEMI` `(Str)` Optional custom tag.
> - `TAG_WRONG_DUB` `(Str)` Optional custom tag.
> - `RUN_INTERVAL_SECONDS` `(Int)` Custom time interval. Default is every 2 hours.
> - `DRY_RUN` `(Bool)` Not sure? Try it first, without writing any tags, JSON file will still be saved.
> - `WRITE_MODE` `(Int)` Something not working or changed your mind? Don't worry I got you covered.
> - `WRITE_MODE=0` Works like usual.
> - `WRITE_MODE=1` Rewrites everything, all tags and JSON file.
> - `WRITE_MODE=2` Removes everything, all tags and JSON file.
> - `START_RUNNING` `(Bool)` Start the container without initiating scan for CLI usage.
> - `ADD_TAG_TO_GENRE` `(Bool)` Adds the tag `Dub` in the genre section only for `DUB` shows.

<br>

## IMPORTANT & DISCLAIMER

> [!WARNING]
>
> - This project is still in very early stages and can have bugs. Currently only tested on Linux.
> - Coding is only a hobby of mine and I am still learning, use this program at your own discretion.
> - Make sure to read the documentation properly.

<br>

## CREDITS

**This project is a fork of [BassHous3/taggarr](https://github.com/BassHous3/taggarr).**

Original author: **[BassHous3](https://github.com/BassHous3)** - Creator of Taggarr and the core tagging logic.

If you appreciate the original work, consider supporting the original author:
<a href="https://ko-fi.com/basshouse" target="_blank"><img src="https://cdn.prod.website-files.com/5c14e387dab576fe667689cf/670f5a0172b90570b1c21dab_kofi_logo.png" alt="Buy Me A Coffee" style="height: 30px !important;" ></a>

Special thanks for inspiration goes to:

- [Cleanuparr](https://github.com/Cleanuparr/Cleanuparr)
- [Huntarr](https://github.com/plexguide/Huntarr)
- [Sonarr](https://github.com/Sonarr/Sonarr) & [Radarr](https://github.com/Radarr/Radarr)

<br>

## CONFIGURATION

### YAML Config File (v0.7.0+)

Taggarr now supports multiple Sonarr/Radarr instances via a YAML configuration file. See `taggarr.example.yaml` for a complete example.

**Config file search order:** `./taggarr.yaml` → `~/.config/taggarr/config.yaml` → `/etc/taggarr/config.yaml`

**CLI options:**

- `--config PATH` - Use specific config file
- `--instances NAME,NAME` - Process only specified instances
- `--dry-run` - Test without making changes
- `--loop` - Run continuously at configured interval

### Docker Compose Example (Legacy Environment Variables)

```yaml
name: Taggarr
services:
  taggarr:
    image: docker.io/stixzoor/taggarr:latest
    container_name: taggarr
    environment:
      # Sonarr (TV Shows) - set these to enable TV show scanning
      - SONARR_API_KEY=your_sonarr_api_key
      - SONARR_URL=http://sonarr:8989
      - TARGET_GENRE=Anime #OPTIONAL - filter TV shows by genre

      # Radarr (Movies) - set these to enable movie scanning
      - RADARR_API_KEY=your_radarr_api_key
      - RADARR_URL=http://radarr:7878
      - TARGET_GENRE_MOVIES=Anime #OPTIONAL - filter movies by genre

      # Common options
      - TARGET_LANGUAGES=english, french # Supports multiple languages, comma-separated
      - RUN_INTERVAL_SECONDS=7200 #OPTIONAL - default is 2 hours
      - START_RUNNING=true
      - QUICK_MODE=false
      - DRY_RUN=false #OPTIONAL - recommended for first time to avoid writing tags
      - WRITE_MODE=0 #OPTIONAL - 0=NONE, 1=REWRITE, 2=REMOVE
      - TAG_DUB=dub
      - TAG_SEMI=semi-dub
      - TAG_WRONG_DUB=wrong-dub
      - LOG_LEVEL=INFO #OPTIONAL - DEBUG/INFO/WARNING/ERROR
      - ADD_TAG_TO_GENRE=false #OPTIONAL - adds "Dub" genre for fully dubbed content
    volumes:
      - /path/to/your/TV:/tv # TV shows - point to "/tv" container path
      - /path/to/your/Movies:/movies # Movies - point to "/movies" container path
      - /var/log/taggarr:/logs # OPTIONAL - recommended path for logs
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

<details>
<summary><span style="font-size: 10em;"><strong>JSON FILE WITH TARGET LANGUAGES ENGLISH AND FRENCH</strong></span></summary>
  
```json

"/tv/Example Show 1": {
"display_name": "Example Show 1",
"tag": "semi-dub",
"last_scan": "2025-06-26T19:22:11.769510Z",
"original_language": "japanese",
"seasons": {
"Season 1": {
"episodes": 1,
"original_dub": ["E01"],
"dub": ["E01:en"],
"missing_dub": ["E01:fr"],
"unexpected_languages": [],
"last_modified": 1749519136.4969385,
"status": "semi-dub"
},
"Season 2": {
"episodes": 1,
"original_dub": ["E01"],
"dub": ["E01:en"],
"missing_dub": ["E01:fr"],
"unexpected_languages": [],
"last_modified": 1749518483.8193643,
"status": "semi-dub"
},
"Season 3": {
"episodes": 1,
"original_dub": ["E01"],
"dub": [],
"missing_dub": ["E01:en, fr"],
"unexpected_languages": [],
"last_modified": 1750725575.362786,
"status": "original"
}
},
"last_modified": 1749519136.4969385
},
"/tv/Example Show 2": {
"display_name": "Example Show 2",
"tag": "dub-en,fr",
"last_scan": "2025-06-26T19:23:55.967659Z",
"original_language": "french",
"seasons": {
"Season 1": {
"episodes": 1,
"original_dub": ["E01"],
"dub": ["E01:en, fr"],
"missing_dub": [],
"unexpected_languages": [],
"last_modified": 1749517909.2880175,
"status": "fully-dub"
}
},
"last_modified": 1749517909.2880175
},

````
</details>


<details>
<summary><span style="font-size: 10em;"><strong>SCREENSHOTS ON HOW TO USE TAG FILTERING</strong></span></summary>


## Sonarr
<img width="550px" src="assets/images/sonarr_.jpg" alt=""></img>
<br><br>
## Emby & Jellyfin
<img width="522px" src="assets/images/emby.png" alt=""></img>  <img width="250px" src="assets/images/jellyfin.jpg" alt=""></img>

</details>

## Native Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/) package manager
- `mediainfo` system package:
  - **Linux:** `apt install mediainfo` or `dnf install mediainfo`
  - **macOS:** `brew install mediainfo`
  - **Windows:** Download from [MediaArea](https://mediaarea.net/en/MediaInfo/Download/Windows)

### Install
```bash
git clone https://github.com/STiXzoOR/taggarr.git
cd taggarr
uv sync
````

### Configure

```bash
# Linux/macOS
mkdir -p ~/.config/taggarr
cp taggarr.example.yaml ~/.config/taggarr/config.yaml
# Edit config.yaml with your settings

# Windows (PowerShell)
mkdir "$env:APPDATA\taggarr" -Force
cp taggarr.example.yaml "$env:APPDATA\taggarr\config.yaml"
```

### Run

```bash
uv run taggarr           # Single scan
uv run taggarr --loop    # Continuous mode
```

### Run as a Service

<details>
<summary>Linux (systemd user service)</summary>

```bash
mkdir -p ~/.config/systemd/user
cp contrib/systemd/taggarr.user.service ~/.config/systemd/user/taggarr.service
# Edit WorkingDirectory in the service file if taggarr is not in ~/taggarr
systemctl --user daemon-reload
systemctl --user enable --now taggarr
systemctl --user status taggarr
```

</details>

<details>
<summary>Linux (systemd system service)</summary>

```bash
sudo useradd -r -s /bin/false taggarr
sudo mkdir -p /opt/taggarr
sudo cp -r . /opt/taggarr
sudo chown -R taggarr:taggarr /opt/taggarr
sudo cp contrib/systemd/taggarr.system.service /etc/systemd/system/taggarr.service
sudo systemctl daemon-reload
sudo systemctl enable --now taggarr
sudo systemctl status taggarr
```

</details>

<details>
<summary>macOS (launchd)</summary>

```bash
cp contrib/launchd/com.taggarr.plist ~/Library/LaunchAgents/
# Edit the plist file: replace YOURUSER with your actual username
launchctl load ~/Library/LaunchAgents/com.taggarr.plist
# Check status
launchctl list | grep taggarr
```

</details>

<details>
<summary>Windows (NSSM)</summary>

1. Download [NSSM](https://nssm.cc/download) and add to PATH
2. Clone taggarr to `%USERPROFILE%\taggarr`
3. Run PowerShell as Administrator:

```powershell
cd $env:USERPROFILE\taggarr
.\contrib\nssm\install.ps1
```

Check status: `nssm status taggarr`

</details>

<br>

## Web UI

Taggarr includes a web-based admin interface for managing instances, viewing media, and configuring settings.

### Running the Web UI

```bash
# Start the server
taggarr serve --port 8080

# With custom database path
taggarr serve --db /path/to/taggarr.db

# For development with auto-reload
taggarr serve --reload
```

### Docker

```bash
docker-compose up -d
```

Access the web UI at http://localhost:3000

### First Run

1. Navigate to http://localhost:3000
2. Create your admin account on the setup page
3. Add your Sonarr/Radarr instances in Settings > Instances
4. Configure notification channels if desired
5. Run a manual scan or wait for scheduled scans

### API Documentation

The API is available at http://localhost:8080/docs (Swagger UI) when the server is running.

<br>
