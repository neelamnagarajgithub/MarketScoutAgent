import "./globals.css";

export const metadata = {
  title: "Scout AI",
  description: "Chat-style interface for market intelligence",
  icons: {
    icon: [
      { url: "/logo_nobg.png", type: "image/png" },
      { url: "/logo_whitebg.png", type: "image/png", sizes: "32x32" }
    ],
    shortcut: "/logo_nobg.png",
    apple: "/logo_whitebg.png"
  }
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
