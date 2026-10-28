import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import useSiteMetadata from '@/hooks/useSiteMetadata';
export default function NotFoundPage() {
  const { siteTitle } = useSiteMetadata();
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-4 px-6">
      <Helmet>
        <title>页面未找到 · {siteTitle}</title>
      </Helmet>
      <h1 className="text-5xl font-bold">404</h1>
      <p>这个页面不存在。</p>
      <Link to="/" className="underline">
        返回运动主页
      </Link>
    </main>
  );
}
