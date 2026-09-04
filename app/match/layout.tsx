/**
 * A layout purely to carry the title.
 *
 * The page itself is a client component — it holds answers in React state so
 * they never leave the browser — and a client component cannot export
 * metadata. A layout can, so the page keeps its privacy property and still
 * gets a title somebody might search for.
 */
export const metadata = {
  title: "Find the right Ghanaian fund for you",
  description:
    "Eight questions, then what fits. Compares Ghanaian funds, Treasury bills, gold and listed shares on what you told us. Your answers stay in your browser.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}