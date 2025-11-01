# GitHub Actions Workflows

This directory contains GitHub Actions workflows for CI/CD automation.

## Workflows

### 🚀 CI Quick Check (`ci.yml`)
**Trigger**: Every push and pull request

Fast syntax and compatibility checks:
- Syntax validation
- Import tests
- Version consistency checks
- Multi-Python version compatibility (3.8-3.13)

**Duration**: ~2-3 minutes

---

### 🧪 Test & Lint (`test.yml`)
**Trigger**: Push/PR to main branches

Comprehensive testing:
- Cross-platform testing (Ubuntu, macOS, Windows)
- Python 3.8-3.12 compatibility
- Code quality checks (flake8, pylint, black, isort)
- Security scanning (bandit, safety)
- CLI functionality tests

**Duration**: ~10-15 minutes

---

### 📦 Publish Release (`publish.yml`)
**Trigger**: Release published or manual dispatch

Publishing pipeline:
1. Build distribution packages (wheel + sdist)
2. Publish to PyPI
3. Create GitHub Release with assets
4. Build standalone executables (Linux, macOS, Windows)
5. Test installation on multiple platforms

**Duration**: ~15-20 minutes

---

### 🏷️ Create Release (`release.yml`)
**Trigger**: Manual workflow dispatch

Automated release creation:
1. Validate version format
2. Update version in all files
3. Generate changelog from git history
4. Commit version bump
5. Create git tag
6. Create GitHub Release
7. Trigger publish workflow

**Usage**:
```
Actions → Create Release → Run workflow
Enter version: 0.0.4
```

---

## Secrets Required

### For PyPI Publishing
- `PYPI_API_TOKEN` - PyPI API token for package publishing

### For GitHub
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

## Manual Workflow Triggers

### Create a Release
```bash
# Via GitHub UI
Actions → Create Release → Run workflow → Enter version

# Via GitHub CLI
gh workflow run release.yml -f version=0.0.4
```

### Manual Publish
```bash
# Via GitHub UI
Actions → Publish Release → Run workflow

# Via GitHub CLI
gh workflow run publish.yml
```

## Badges

Add these to your README.md:

```markdown
![CI](https://github.com/yosefario-dev/asmr18/workflows/CI%20Quick%20Check/badge.svg)
![Tests](https://github.com/yosefario-dev/asmr18/workflows/Test%20%26%20Lint/badge.svg)
![PyPI](https://img.shields.io/pypi/v/asmr18)
![Python](https://img.shields.io/pypi/pyversions/asmr18)
```

## Dependabot

Automated dependency updates configured in `dependabot.yml`:
- Python dependencies: Weekly on Monday
- GitHub Actions: Weekly on Monday
- Auto-assign to maintainers
- Ignores patch version updates

## Local Testing

Test workflows locally with [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS
# or
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run CI workflow
act -W .github/workflows/ci.yml

# Run specific job
act -j quick-check
```

## Troubleshooting

### Workflow fails on syntax check
```bash
# Run locally
python -m py_compile src/asmr18/*.py
```

### Version mismatch error
Ensure versions match in:
- `src/asmr18/__init__.py`
- `src/asmr18/cli.py`
- `setup.py`

### PyPI publish fails
- Check `PYPI_API_TOKEN` secret is set
- Verify package name is available on PyPI
- Ensure version number is incremented
