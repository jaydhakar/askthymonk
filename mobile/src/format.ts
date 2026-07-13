/**
 * Prettify a raw book id from the index (e.g. "008_Amrit_Ki_Disha") into a
 * human-friendly title ("Amrit Ki Disha") for display under an answer.
 */
export function formatBookTitle(book: string): string {
  return book
    .replace(/^\d+[_\-\s]*/, "") // drop leading catalog number
    .replace(/[_]+/g, " ") // underscores -> spaces
    .replace(/\s+/g, " ")
    .trim();
}

let counter = 0;
/** Simple unique id for chat messages. */
export function makeId(): string {
  counter += 1;
  return `${Date.now().toString(36)}-${counter}`;
}
