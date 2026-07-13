export type ChatRole = "user" | "assistant";

export type Message = {
  id: string;
  role: ChatRole;
  text: string;
  /** Cited book title, for assistant answers only. */
  book?: string | null;
  /** Marks an assistant message that reports an error rather than an answer. */
  error?: boolean;
};
