/**
 * Turkish Case-Insensitive String Matcher
 * 
 * Safely compares two strings for a search match, handling Turkish 
 * specific characters (i, I, ı, İ) correctly.
 *
 * @param {string} source - The string to search within.
 * @param {string} query - The search term.
 * @returns {boolean} True if source contains query (case-insensitive Turkish).
 */
export const matchTurkish = (source, query) => {
    if (!source || query === undefined || query === null) return false;
    if (query === '') return true;

    const s = String(source).toLocaleLowerCase('tr-TR');
    const q = String(query).toLocaleLowerCase('tr-TR');

    return s.includes(q);
};
