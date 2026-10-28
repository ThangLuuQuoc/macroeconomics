import type { Metadata } from "next";
import type { ReactNode } from "react";

import { DataModeBar } from "./DataModeBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tổng quan vĩ mô",
  description: "Theo dõi và giả lập kinh tế vĩ mô Việt Nam",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <DataModeBar />
        {children}
      </body>
    </html>
  );
}
