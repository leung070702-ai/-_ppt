import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = { title: '赛智 PPT · 科技商业比赛智能修改', description: '让每一页都更有说服力' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
