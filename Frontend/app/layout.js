import "./globals.css";

export const metadata = {
  title: "MarketScout Chat",
  description: "Chat-style interface for market intelligence"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
