# Plan: Symbolic Links Support (Linux)

> Source PRD: specs/010-symbolic-links-support/prd.md

## Architectural decisions

Durable decisions that apply across all phases:

- **Routes**: Keep existing file and analysis routes; symlink support is implemented behind `GET /api/v1/projects/{project_id}/files`, `GET /api/v1/projects/{project_id}/files/{filepath:path}`, and existing analysis start routes without adding new public endpoints.
- **Schema**: No SQLite or Neo4j schema migration for this feature; existing `ASTNode.source_file` remains the path identity used by graph queries.
- **Key models**: Keep current response model shape for file listing/content (`FileInfo`-based payloads) and AST graph models (`ASTNode`, `Relationship`).
- **Security boundary**: Shift from strict `realpath within physical source root` to `project-visible alias path rooted in the in-project tree`, while still rejecting malformed/traversal input.
- **Symlink policy**: Linux-focused read/navigation and analysis support only; ZIP upload semantics and write semantics remain unchanged.

---

## Phase 1: Symlink-safe browsing baseline

**User stories**: 1, 2, 3, 4, 5, 6, 8, 9, 10, 22, 23, 24

### What to build

Enable FilesPage browsing and file-content reads through symlinked entries reachable from the project tree, while preserving project-relative alias paths in API interactions and maintaining strict validation for direct user input.

### Acceptance criteria

- [ ] Listing a symlinked directory reachable from the project tree returns entries in the existing files API response shape.
- [ ] Reading file content through one or more symlink hops works via project-relative alias path.
- [ ] Alias paths that resolve outside the physical `source` root are allowed only when reached from an in-project alias path.
- [ ] Raw traversal patterns (absolute paths, `..`, malformed direct paths) are rejected with controlled client errors.
- [ ] Broken/inaccessible symlink targets surface controlled API errors and useful logs.

---

## Phase 2: Discovery and normalization for alias identity

**User stories**: 11, 14, 15, 16, 17, 22, 24

### What to build

Extend parser discovery and path normalization so symlinked source trees are included safely, folder/language filters still behave as expected, and normalized source identities preserve project-visible alias semantics instead of collapsing to physical targets.

### Acceptance criteria

- [ ] Discovery includes files behind symlinked directories using alias-visible traversal.
- [ ] Discovery terminates safely on symlink cycles without hangs or infinite recursion.
- [ ] Folder filters match paths that traverse symlinked segments.
- [ ] Language classification for symlinked files continues to work by extension.
- [ ] Source path normalization preserves valid alias identities and rejects malformed/out-of-policy paths.

---

## Phase 3: Analysis pipeline preserves alias paths end-to-end

**User stories**: 12, 13, 18, 19

### What to build

Ensure analysis orchestration and graph persistence retain alias paths from discovery through parsing and storage, including intentional treatment of multiple aliases to the same physical file as distinct source entries.

### Acceptance criteria

- [ ] Parsed nodes for linked files keep the alias path used during discovery.
- [ ] Two distinct alias paths to the same target are represented as distinct source entries in analysis output.
- [ ] Graph storage/query behavior remains coherent with alias-preserved `source_file` identities.
- [ ] Graph-to-file navigation resolves to FilesPage-visible alias paths.

---

## Phase 4: Regression matrix and Linux-focused hardening

**User stories**: 7, 20, 21, 25

### What to build

Complete automated regression coverage and platform-focused hardening for symlink behavior in API browsing, parser discovery, normalization, and orchestration, while explicitly preserving existing ZIP behavior and scope limits.

### Acceptance criteria

- [ ] Backend endpoint tests cover symlink directory listing, alias file read, invalid traversal rejection, and controlled failures.
- [ ] Parser/discovery tests cover symlink traversal, cycle prevention, filter compatibility, and alias normalization behavior.
- [ ] Orchestrator/analysis tests verify alias identity preservation and distinct alias handling in results.
- [ ] Frontend FilesPage tests verify lazy expansion/open behavior for linked entries without adding new symlink-specific UI metadata.
- [ ] Existing ZIP upload behavior remains unchanged and documented as out of scope.
