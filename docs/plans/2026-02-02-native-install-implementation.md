# Native Installation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add cross-platform native installation using uv with service templates for Linux, macOS, and Windows.

**Architecture:** Migrate pyproject.toml to uv-style dependency-groups, add platform-aware config path resolution (XDG_CONFIG_HOME on Linux/macOS, APPDATA on Windows), and ship service templates in contrib/.

**Tech Stack:** Python 3.9+, uv, systemd, launchd, NSSM

---

## Task 1: Migrate pyproject.toml to uv-style

**Files:**

- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml**

Replace the entire `pyproject.toml` with:

```toml
[project]
name = "taggarr"
version = "0.7.0"
description = "Dub Analysis & Tagging for Sonarr/Radarr"
requires-python = ">=3.9"
dependencies = [
    "requests>=2.32",
    "pymediainfo>=7.0",
    "pycountry>=24.6",
    "PyYAML>=6.0",
]

[project.scripts]
taggarr = "main:main"

[dependency-groups]
test = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-mock>=3.0",
    "responses>=0.23",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=taggarr --cov-report=term-missing --cov-fail-under=99"
markers = [
    "integration: marks tests requiring external services (deselect with '-m not integration')",
]

[tool.coverage.run]
branch = true
source = ["taggarr"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
]
```

**Step 2: Remove old venv and regenerate with uv**

Run:

```bash
rm -rf .venv uv.lock
uv sync --group test
```

Expected: New `.venv/` and `uv.lock` created

**Step 3: Verify tests pass**

Run: `uv run pytest`

Expected: 259 tests pass, 99%+ coverage

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: migrate to uv-style pyproject.toml with dependency-groups"
```

---

## Task 2: Add test.sh script

**Files:**

- Create: `test.sh`

**Step 1: Create test.sh**

```bash
#!/bin/sh
uv run pytest "$@"
```

**Step 2: Make executable**

Run: `chmod +x test.sh`

**Step 3: Verify it works**

Run: `./test.sh`

Expected: 259 tests pass

**Step 4: Commit**

```bash
git add test.sh
git commit -m "build: add test.sh wrapper for uv run pytest"
```

---

## Task 3: Add XDG_CONFIG_HOME and APPDATA support to config_loader

**Files:**

- Modify: `taggarr/config_loader.py`
- Modify: `tests/unit/test_config_loader.py`

**Step 1: Write tests for XDG_CONFIG_HOME**

Add to `tests/unit/test_config_loader.py`:

```python
class TestGetConfigPaths:
    """Tests for config path resolution."""

    def test_xdg_config_home_takes_priority(self, tmp_path, monkeypatch):
        """XDG_CONFIG_HOME should be checked before ~/.config."""
        xdg_dir = tmp_path / "xdg"
        xdg_dir.mkdir()
        config_file = xdg_dir / "taggarr" / "config.yaml"
        config_file.parent.mkdir()
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://xdg-host
    api_key: key
    root_path: /media
""")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
        monkeypatch.chdir(tmp_path)  # No local taggarr.yaml

        config = load_config()
        assert config.instances["test"].url == "http://xdg-host"

    def test_falls_back_to_home_config_when_no_xdg(self, tmp_path, monkeypatch):
        """Should use ~/.config when XDG_CONFIG_HOME is not set."""
        # Unset XDG_CONFIG_HOME if present
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

        # Create config in fake home
        fake_home = tmp_path / "home"
        config_dir = fake_home / ".config" / "taggarr"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://home-config
    api_key: key
    root_path: /media
""")
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.chdir(tmp_path)  # No local taggarr.yaml

        config = load_config()
        assert config.instances["test"].url == "http://home-config"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_config_loader.py::TestGetConfigPaths -v`

Expected: FAIL (tests don't exist yet or XDG not implemented)

**Step 3: Write tests for Windows APPDATA**

Add to `tests/unit/test_config_loader.py`:

```python
    def test_appdata_on_windows(self, tmp_path, monkeypatch):
        """Should use APPDATA on Windows."""
        # Mock Windows platform
        monkeypatch.setattr("sys.platform", "win32")

        appdata_dir = tmp_path / "AppData" / "Roaming"
        config_dir = appdata_dir / "taggarr"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("""
instances:
  test:
    type: sonarr
    url: http://appdata-host
    api_key: key
    root_path: /media
""")
        monkeypatch.setenv("APPDATA", str(appdata_dir))
        monkeypatch.chdir(tmp_path)  # No local taggarr.yaml

        config = load_config()
        assert config.instances["test"].url == "http://appdata-host"
```

**Step 4: Update config_loader.py with platform-aware paths**

Replace the `load_config` function in `taggarr/config_loader.py`:

```python
import sys


def _get_config_search_paths() -> list:
    """Get platform-specific config search paths."""
    paths = [Path("./taggarr.yaml")]

    if sys.platform == "win32":
        # Windows: use APPDATA
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "taggarr" / "config.yaml")
    else:
        # Linux/macOS: XDG_CONFIG_HOME or ~/.config, then /etc
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            paths.append(Path(xdg_config) / "taggarr" / "config.yaml")
        paths.append(Path.home() / ".config" / "taggarr" / "config.yaml")
        paths.append(Path("/etc/taggarr/config.yaml"))

    return paths


def load_config(cli_path: "Optional[str]" = None) -> Config:
    """Load configuration from YAML file.

    Search order:
    1. CLI-specified path
    2. ./taggarr.yaml
    3. $XDG_CONFIG_HOME/taggarr/config.yaml (Linux/macOS)
       or %APPDATA%/taggarr/config.yaml (Windows)
    4. ~/.config/taggarr/config.yaml (Linux/macOS only)
    5. /etc/taggarr/config.yaml (Linux/macOS only)
    """
    search_paths = _get_config_search_paths()

    if cli_path:
        config_path = Path(cli_path)
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {cli_path}")
    else:
        config_path = None
        for path in search_paths:
            if path.exists():
                config_path = path
                break

        if config_path is None:
            searched = "\n  ".join(str(p) for p in search_paths)
            raise ConfigError(
                f"No config file found. Searched:\n  {searched}\n\n"
                "Create taggarr.yaml or specify --config path"
            )

    return _parse_config(config_path)
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_config_loader.py -v`

Expected: All tests pass

**Step 6: Commit**

```bash
git add taggarr/config_loader.py tests/unit/test_config_loader.py
git commit -m "feat: add XDG_CONFIG_HOME and Windows APPDATA config path support"
```

---

## Task 4: Create systemd service templates

**Files:**

- Create: `contrib/systemd/taggarr.user.service`
- Create: `contrib/systemd/taggarr.system.service`

**Step 1: Create directory**

Run: `mkdir -p contrib/systemd`

**Step 2: Create user service template**

Create `contrib/systemd/taggarr.user.service`:

```ini
[Unit]
Description=Taggarr - Dub Analysis & Tagging
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/taggarr
ExecStart=/usr/bin/env uv run taggarr --loop
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
```

**Step 3: Create system service template**

Create `contrib/systemd/taggarr.system.service`:

```ini
[Unit]
Description=Taggarr - Dub Analysis & Tagging
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=taggarr
Group=taggarr
WorkingDirectory=/opt/taggarr
ExecStart=/usr/bin/env uv run taggarr --loop
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

**Step 4: Commit**

```bash
git add contrib/systemd/
git commit -m "feat: add systemd service templates for Linux"
```

---

## Task 5: Create launchd template for macOS

**Files:**

- Create: `contrib/launchd/com.taggarr.plist`

**Step 1: Create directory**

Run: `mkdir -p contrib/launchd`

**Step 2: Create plist template**

Create `contrib/launchd/com.taggarr.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.taggarr</string>
    <key>WorkingDirectory</key>
    <string>/Users/YOURUSER/taggarr</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOURUSER/.local/bin/uv</string>
        <string>run</string>
        <string>taggarr</string>
        <string>--loop</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOURUSER/Library/Logs/taggarr.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOURUSER/Library/Logs/taggarr.error.log</string>
</dict>
</plist>
```

**Step 3: Commit**

```bash
git add contrib/launchd/
git commit -m "feat: add launchd plist template for macOS"
```

---

## Task 6: Create NSSM install script for Windows

**Files:**

- Create: `contrib/nssm/install.ps1`

**Step 1: Create directory**

Run: `mkdir -p contrib/nssm`

**Step 2: Create PowerShell install script**

Create `contrib/nssm/install.ps1`:

```powershell
# Taggarr Windows Service Installer
# Requires: NSSM (https://nssm.cc/download) in PATH
# Run as Administrator

$serviceName = "taggarr"
$uvPath = "$env:USERPROFILE\.local\bin\uv.exe"
$workDir = "$env:USERPROFILE\taggarr"

# Check if NSSM is available
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Error "NSSM not found. Download from https://nssm.cc/download and add to PATH"
    exit 1
}

# Check if uv is installed
if (-not (Test-Path $uvPath)) {
    Write-Error "uv not found at $uvPath. Install from https://docs.astral.sh/uv/"
    exit 1
}

# Check if workdir exists
if (-not (Test-Path $workDir)) {
    Write-Error "Taggarr directory not found at $workDir"
    exit 1
}

# Create logs directory
$logsDir = "$workDir\logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

# Install service
Write-Host "Installing taggarr service..."
nssm install $serviceName $uvPath run taggarr --loop
nssm set $serviceName AppDirectory $workDir
nssm set $serviceName AppStdout "$logsDir\service.log"
nssm set $serviceName AppStderr "$logsDir\service.error.log"
nssm set $serviceName AppRotateFiles 1
nssm set $serviceName AppRotateBytes 10485760

# Start service
Write-Host "Starting taggarr service..."
nssm start $serviceName

Write-Host "Done! Check status with: nssm status $serviceName"
```

**Step 3: Commit**

```bash
git add contrib/nssm/
git commit -m "feat: add NSSM install script for Windows"
```

---

## Task 7: Update README with Native Installation section

**Files:**

- Modify: `README.md`

**Step 1: Read current README**

Find the location after Docker Compose section.

**Step 2: Add Native Installation section**

Insert after the Docker section (before IMPORTANT & DISCLAIMER):

````markdown
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
```
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
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Native Installation section to README"
```

---

## Task 8: Final verification

**Step 1: Run full test suite**

Run: `uv run pytest`

Expected: All 259+ tests pass with 99%+ coverage

**Step 2: Verify uv sync works fresh**

Run:

```bash
rm -rf .venv
uv sync --group test
uv run pytest
```

Expected: Fresh install works, all tests pass

**Step 3: Verify entry point works**

Run: `uv run taggarr --help`

Expected: Shows help output

**Step 4: Create final commit if any changes**

If any fixups needed, commit them.

---

## Summary

| Task | Description                        | Files                      |
| ---- | ---------------------------------- | -------------------------- |
| 1    | Migrate pyproject.toml to uv-style | pyproject.toml, uv.lock    |
| 2    | Add test.sh wrapper                | test.sh                    |
| 3    | Add XDG/APPDATA config paths       | config_loader.py, tests    |
| 4    | Create systemd templates           | contrib/systemd/\*.service |
| 5    | Create launchd template            | contrib/launchd/\*.plist   |
| 6    | Create NSSM script                 | contrib/nssm/install.ps1   |
| 7    | Update README                      | README.md                  |
| 8    | Final verification                 | -                          |
