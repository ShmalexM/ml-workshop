export type BookLocation = { bookId: string; location: number; anchor?: string }
export type BookEntry = { title: string; location: number; label: string; depth: number; key?: string }
export type Book = { id: string; title: string; author: string; format: 'pdf' | 'epub'; count: number; toc: BookEntry[]; rights: string; attribution: string; sha256: string; cover?: string; assets: { path: string; bytes: number; sha256: string; mediaType: string }[] }
export type ReadingState = { location: number; notes: string; bookmarks: number[]; completed: string[]; updatedAt: number }
export type StudyGuide = { id: string; bookId: string; bookTitle: string; title: string; focus: string; question: string; readings: { location: number; title: string }[]; lessons: string[] }
export type LibraryData = { books: Book[]; guides: StudyGuide[]; readingState: Record<string, ReadingState> }
export type Chapter = { location: number; title: string; label: string; text: string; html?: string }
export type SearchHit = { bookId: string; bookTitle: string; location: number; label: string; title: string; excerpt: string }

export function bookLink(bookId: string, location: number) { return `#books/${bookId}/${location}` }
