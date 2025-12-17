# Feature Specification: Update Documentation and PyPI Metadata

**Feature Branch**: `016-update-docs-pypi`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Clean up README and documentation, and update PyPI info, as that page currently points to https://github.com/intersystems-community/iris-devtools"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PyPI Page Shows Correct Repository Links (Priority: P1)

A developer discovers the `iris-devtester` package on PyPI and clicks on the project links (Homepage, Repository, Documentation, Issues). They expect to be taken to the correct GitHub repository where the package is actually maintained, not a non-existent `iris-devtools` repository.

**Why this priority**: Users cannot contribute, report issues, or find documentation if links point to the wrong repository. This is a critical discoverability and trust issue.

**Independent Test**: Navigate to https://pypi.org/project/iris-devtester/, click each project link, and verify all links resolve to the correct `iris-devtester` repository.

**Acceptance Scenarios**:

1. **Given** a user is on the PyPI page for iris-devtester, **When** they click "Homepage", **Then** they are taken to `https://github.com/intersystems-community/iris-devtester`
2. **Given** a user is on the PyPI page for iris-devtester, **When** they click "Repository", **Then** they are taken to `https://github.com/intersystems-community/iris-devtester`
3. **Given** a user is on the PyPI page for iris-devtester, **When** they click "Issues", **Then** they are taken to `https://github.com/intersystems-community/iris-devtester/issues`
4. **Given** a user is on the PyPI page for iris-devtester, **When** they click "Documentation", **Then** they are taken to `https://github.com/intersystems-community/iris-devtester#readme`

---

### User Story 2 - README Contains Accurate Links (Priority: P2)

A developer reads the README.md file (either on GitHub or rendered on PyPI) and clicks on documentation links, constitution references, or contribution guidelines. All links should resolve correctly to existing files in the repository.

**Why this priority**: Broken links in README frustrate users and reduce trust in the project quality.

**Independent Test**: Click every link in README.md and verify each resolves to the correct target.

**Acceptance Scenarios**:

1. **Given** a user is reading README.md, **When** they click "Constitution" link, **Then** they are taken to the correct CONSTITUTION.md file in the repository
2. **Given** a user is reading README.md, **When** they click "Troubleshooting Guide" link, **Then** they are taken to the correct docs/TROUBLESHOOTING.md file
3. **Given** a user is reading README.md, **When** they click "CONTRIBUTING.md" link, **Then** they are taken to the correct CONTRIBUTING.md file
4. **Given** a user is reading README.md, **When** they click "Examples" link, **Then** they are taken to the correct examples/ directory
5. **Given** a user is reading README.md, **When** they click any "iris-devtools" reference link, **Then** it correctly points to `iris-devtester` repository

---

### User Story 3 - README is Well-Organized and Scannable (Priority: P2)

A developer lands on the README.md and wants to quickly find specific information (installation, a particular feature, troubleshooting). The current README is too long (~360 lines) and lacks clear navigation. Developers should be able to scan a table of contents, find what they need, and access detailed documentation via links to separate files.

**Why this priority**: A long, unstructured README overwhelms new users and makes the project appear less professional. Users abandon projects they can't quickly understand.

**Independent Test**: Open README.md and verify a table of contents exists, the core content fits in a reasonable scroll, and detailed sections link to separate documentation files.

**Acceptance Scenarios**:

1. **Given** a user opens README.md, **When** they look at the top of the file, **Then** they see a table of contents with clickable links to major sections
2. **Given** a user wants to understand installation, **When** they read the Quick Start section, **Then** they can complete basic installation in under 30 seconds of reading
3. **Given** a user wants detailed feature documentation, **When** they click a feature link, **Then** they are taken to a dedicated documentation file in `docs/`
4. **Given** a user scans the README, **When** they scroll through it, **Then** the core content (before detailed examples) is under 150 lines
5. **Given** a user wants to see code examples, **When** they look for examples, **Then** they find 1-2 concise examples in README with links to more in `examples/`

---

### User Story 4 - Consistent Package Naming in Documentation (Priority: P3)

A developer reading any documentation file sees consistent references to the package name. Historical references to `iris-devtools` (the original project name before extraction) should be updated to `iris-devtester` (the actual PyPI package name) to avoid confusion.

**Why this priority**: Inconsistent naming confuses users about whether they have the right package.

**Independent Test**: Search all documentation files for `iris-devtools` references that should be `iris-devtester` and verify none remain in user-facing documentation.

**Acceptance Scenarios**:

1. **Given** a user reads pyproject.toml, **When** they look at project.urls, **Then** all URLs point to `iris-devtester` repository
2. **Given** a user reads CHANGELOG.md, **When** they look at release links, **Then** all links point to `iris-devtester` repository
3. **Given** a user reads any user-facing documentation, **When** they see package references, **Then** the references use `iris-devtester` consistently

---

### Edge Cases

- What happens when historical spec files reference the old `iris-devtools` name?
  - These are internal development artifacts and can retain historical references for context, but should be clearly marked as historical where confusion could arise.
- How does the system handle links that reference specific commits or tags?
  - Tags and releases should use the correct repository name; if releases were made with wrong links, create new releases with corrected metadata.
- What content should remain in README vs. be moved to docs/?
  - README keeps: project overview, installation, minimal "hello world" example, feature list with brief descriptions, links to detailed docs. Detailed examples, configuration options, and extended feature documentation move to docs/.
- How should PyPI rendering be considered when splitting docs?
  - PyPI only renders README.md; links to docs/ files will work on GitHub but show as links on PyPI. This is acceptable as long as README provides enough context for PyPI visitors to understand the package value.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: pyproject.toml MUST contain correct project.urls pointing to `https://github.com/intersystems-community/iris-devtester`
- **FR-002**: README.md MUST contain correct links to repository resources (constitution, troubleshooting, examples, contributing)
- **FR-003**: CHANGELOG.md MUST contain correct release and comparison links to the iris-devtester repository
- **FR-004**: User-facing documentation (README.md, GETTING_STARTED.md, CONTRIBUTING.md) MUST use `iris-devtester` package name consistently
- **FR-005**: PyPI metadata MUST be updated by publishing a new version (version bump required to push new metadata)
- **FR-006**: Internal development documents (specs/, CLAUDE.md, AGENTS.md) MAY retain historical `iris-devtools` references where they provide context, but should be reviewed for user-facing consistency
- **FR-007**: README.md MUST include a table of contents with anchor links to major sections
- **FR-008**: README.md MUST be reorganized to keep core content (intro, installation, basic usage) concise, with detailed feature documentation moved to separate files in `docs/`
- **FR-009**: README.md MUST link to dedicated documentation files for detailed features (DAT fixtures, Docker-Compose integration, Performance Monitoring, etc.)
- **FR-010**: New documentation files MUST be created in `docs/` directory for detailed feature guides currently embedded in README

### Key Entities

- **pyproject.toml**: Central configuration file containing PyPI metadata including project.urls
- **README.md**: Primary user-facing documentation rendered on both GitHub and PyPI
- **CHANGELOG.md**: Version history with links to releases and comparisons
- **User-facing docs**: GETTING_STARTED.md, CONTRIBUTING.md, CONSTITUTION.md, docs/TROUBLESHOOTING.md
- **docs/ directory**: Contains detailed feature documentation split out from README (new feature guides to be created)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 5 links in pyproject.toml project.urls section point to correct `iris-devtester` repository
- **SC-002**: 100% of links in README.md resolve to valid targets (no 404 errors)
- **SC-003**: Zero occurrences of `github.com/intersystems-community/iris-devtools` in user-facing documentation files
- **SC-004**: After PyPI publish, clicking project links on https://pypi.org/project/iris-devtester/ navigates to correct repository
- **SC-005**: Users can navigate from PyPI to GitHub issues page within 2 clicks
- **SC-006**: README.md core content (before "Documentation" section) is under 150 lines
- **SC-007**: README.md contains a table of contents with working anchor links
- **SC-008**: At least 3 detailed feature sections are moved to separate docs/ files with links from README
- **SC-009**: Users can find installation instructions within 10 seconds of opening README

## Clarifications

### Session 2025-12-16

- Q: Should README organization be addressed as part of this feature? → A: Yes, README is too long and needs TOC, better organization, and content split to separate docs files

## Assumptions

- The package will continue to be named `iris-devtester` on PyPI (not renamed to `iris-devtools`)
- A version bump (e.g., 1.2.1 -> 1.2.2) is acceptable to push updated metadata to PyPI
- Historical references in specs/ directories can remain for development context
- The Constitution principle examples (which show error message format with URLs) may retain the example URLs
