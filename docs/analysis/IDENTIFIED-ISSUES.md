> **Snapshot — prepared before the NCOS kernel app was folded out to `legacy/`.**
> File names and line numbers below describe the code as it was then; treat them as the
> reasoning, not as current locations. Status of each finding as of 2026-09-18:
>
> | # | Finding | Status |
> |---|---|---|
> | 1 | Search/Generator load everything on mount | **Partly fixed** — `Search.jsx` now caps each collection at `limit(100)`; the client-side filtering remains |
> | 2 | Unbounded/no-pagination question queries | **Open** — `QuestionGenerator.jsx` no longer fetches 1,000 rows, but there is still no pagination anywhere (TODO P2-4) |
> | 3 | Feed page's independent queries | **Superseded** — `Feed.jsx` and its `RecentPanel` are gone (merged into `Workspace.jsx`) |
>
> Kept because the reasoning behind the current architecture is here; see `FINAL ANALYSIS.md`
> for the priorities drawn from it, and `docs/TODO.md` for what is actually outstanding.

I'll analyze the repository for potential performance issues by examining the codebase structure and key files.Now I'll gather evidence about the repository structure, configuration, and code to identify performance issues.Now let me examine the source structure to understand the code organization:Based on my review of the Beacon Educational Consult codebase, here are the **key performance issues** I've identified:

## 1. **Excessive Firestore Reads in Search and Generator Pages**
- **`Search.jsx`** (lines 91–98): Loads **all schemes, plans, and up to 1,000 questions** from Firestore on mount, every time the component mounts. This is a heavy, unoptimized query with `limit(1000)`.
- **`QuestionGenerator.jsx`** (lines 68): Also fetches `limit(1000)` questions on every mount.
- **Impact**: Each user accessing these pages triggers multiple large Firestore reads. With many concurrent users, this will rapidly deplete the read quota.

## 2. **Unbounded Firestore Query in QuestionGenerator**
- The question bank is fetched with `limit(1000)` but there's no pagination or filtering at the query level. All filtering happens client-side in `useMemo()`.
- If the question bank grows beyond 1,000 items, data is silently truncated without warning.

## 3. **Feed Page Runs Multiple Independent Firestore Queries**
- **`Feed.jsx`** (lines 142–151, 205–214, 221–223): The `RecentPanel` component and the progress/quota checks each run their own Firestore queries on mount, without proper dependency management.
- The `statusFilter` dependency in the `useEffect` of `RecentPanel` is commented out of the dependency array (line 151), which can cause stale data or missed updates.

## 4. **Large Object Tree Building on Every Render**
- **`useCurriculum.js`** `buildTree()` function (lines 123–162): Creates deep nested Map structures and arrays on every call. `SubjectBrowser.jsx` calls this in a `useMemo`, but the filtering and conversion happens repeatedly for large grade curricula.
- **`SubjectBrowser.jsx`** (line 84): The tree is recalculated every time `indicators` or `subjectId` changes, even if only one changed.

## 5. **Missing Pagination and Lazy Loading**
- Search results and question lists show all results at once with a "Show more" toggle for UI only — data is already fetched and filtered in memory.
- No virtual scrolling or lazy loading for large lists (e.g., the entire curriculum or question bank).

## 6. **Inefficient Client-Side Text Filtering**
- **`Search.jsx`** (lines 109–143): Performs substring matching on every field of every document (schemes, plans, questions, indicators) client-side after fetch. With complex filtering logic spread across multiple `has()` calls, this can become a bottleneck on slow devices.

## 7. **No Firestore Composite Index Optimization**
- README mentions (line 236–239) that "some filtered queries… may prompt Firestore to create a composite index the first time they run."
- Queries like "lesson plans by indicator" or "author pages" lack precomputed indexes, causing latency spikes on first access.

## 8. **PDF/Word/PPTX Export Generates Full Documents Synchronously**
- `questionPaper.js` and similar exporters build large DOM-like object trees (especially for Word with `docx` library) before serialization. For large papers (100+ questions), this can freeze the UI.

## 9. **AuthContext Live Subscription Fires Even for Static Profile Data**
- **`AuthContext.jsx`** (lines 23–29): Sets up a real-time listener on `users/{uid}` for every authenticated user, even if the profile data doesn't change frequently. This keeps an open WebSocket per user.

## 10. **Module-Level Caches Have No Expiry**
- **`useCurriculum.js`** (lines 8–12): Global `cache` and `scheduleCache` Maps never invalidate. If curriculum data is updated on the server, users see stale data until they reload the page.

---

## Recommended Fixes (Priority Order)

1. **Add query-level filtering** to Firestore calls in `Search.jsx` and `QuestionGenerator.jsx` (e.g., filter by `grade`, `subject` before fetching).
2. **Implement pagination** with `startAfter()` cursors for large result sets.
3. **Debounce search input** and use `onSnapshot()` with `where()` constraints rather than fetching all data upfront.
4. **Memoize `buildTree()`** output and deep-compare `indicators` array by reference, not contents.
5. **Use Firestore composite indexes** for filtered queries; document the required index definitions in setup.
6. **Consider a local cache layer** (IndexedDB) with TTL for curriculum data instead of fetch-on-mount.
7. **Defer PDF/Word generation** to a Web Worker to avoid main-thread blocking.
8. **Cache static curriculum JSON** more aggressively with service-worker etag-based revalidation.