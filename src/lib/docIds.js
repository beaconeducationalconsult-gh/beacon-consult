/**
 * Deterministic ids for documents that hang off an indicator.
 *
 * Firestore has no unique constraints, so the app builds the id itself and the
 * write is an upsert: one document per author per thing. The *thing* is the
 * indicator — and an indicator code is only unique **within a subject**:
 * `B4.1.1.1.1` exists in every B4 subject, so an id built from the code alone
 * collides across subjects (`data/curriculum/` carries 84 subject-grades and
 * 4,040 indicators; the code alone would name far fewer documents). Two teachers
 * writing a plan for their own B4 strand 1 indicator would share one document.
 *
 * Hence the subject is part of the key, not decoration. The id is stable,
 * readable and sanitised, so it is safe to use as a path segment.
 *
 * @param {string} uid            the author's user id
 * @param {string} subjectId      the dataset subject id (`mathematics`, `owop`, …)
 * @param {string} indicatorCode  the indicator code (`B4.1.1.1.1`)
 * @returns {string} `<uid>_<subject>_<code>`
 */
export const indicatorDocId = (uid, subjectId, indicatorCode) =>
  [uid, subjectId, indicatorCode]
    .map((part) => String(part ?? '').trim().replace(/[^\w.-]/g, '_'))
    .join('_')
