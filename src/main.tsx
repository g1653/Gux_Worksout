import React from 'react';
import ReactDOM from 'react-dom/client';
import {
  Navigate,
  RouterProvider,
  createBrowserRouter,
  useLocation,
} from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import NotFound from './pages/404';
import ReactGA from 'react-ga4';
import {
  GOOGLE_ANALYTICS_TRACKING_ID,
  USE_GOOGLE_ANALYTICS,
} from './utils/const';
import '@/styles/index.css';
import { withOptionalGAPageTracking } from './utils/trackRoute';

const Dashboard = React.lazy(() => import('@/pages/dashboard'));
// Keep old bookmarks useful without shipping the old pages.
const Redirect = ({ to }: { to: string }) => {
  const { search, hash } = useLocation();
  return <Navigate to={{ pathname: to, search, hash }} replace />;
};
if (USE_GOOGLE_ANALYTICS) ReactGA.initialize(GOOGLE_ANALYTICS_TRACKING_ID);
const dashboard = withOptionalGAPageTracking(
  <React.Suspense
    fallback={
      <div role="status" className="p-8">
        正在加载运动主页…
      </div>
    }
  >
    <Dashboard />
  </React.Suspense>
);
const routes = createBrowserRouter(
  [
    { path: '/', element: dashboard },
    { path: 'summary', element: dashboard },
    { path: 'dashboard', element: <Redirect to="/" /> },
    { path: 'dashboard/summary', element: <Redirect to="/summary" /> },
    { path: 'classic', element: <Redirect to="/" /> },
    { path: 'classic/summary', element: <Redirect to="/summary" /> },
    { path: '*', element: <NotFound /> },
  ],
  { basename: import.meta.env.BASE_URL }
);
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HelmetProvider>
      <RouterProvider router={routes} />
    </HelmetProvider>
  </React.StrictMode>
);
