import { Outlet, Link, useLocation } from 'react-router';
import { LayoutDashboard, Database, Shield, Bell, Settings, User, ChevronRight, Package, Bot } from 'lucide-react';

export function Layout() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/products', label: 'Products', icon: Package },
    { path: '/rules', label: 'Metrics', icon: Shield },
    { path: '/agents', label: 'Agents', icon: Bot },
    { path: '/database', label: 'Database', icon: Database },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top Navigation Bar */}
      <header className="bg-white border-b border-slate-200 h-16 fixed top-0 left-0 right-0 z-10">
        <div className="flex items-center justify-between h-full px-6">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-slate-900">Supply Sight</span>
          </div>
          <div className="flex items-center gap-4">
            <button className="relative p-2 hover:bg-slate-100 rounded-lg transition-colors">
              <Bell className="w-5 h-5 text-slate-600" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
            <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
              <Settings className="w-5 h-5 text-slate-600" />
            </button>
            <button className="flex items-center gap-2 p-2 hover:bg-slate-100 rounded-lg transition-colors">
              <User className="w-5 h-5 text-slate-600" />
            </button>
          </div>
        </div>
      </header>

      {/* Sidebar */}
      <aside className="bg-white border-r border-slate-200 w-64 fixed left-0 top-16 bottom-0 overflow-y-auto">
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  active
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-slate-700 hover:bg-slate-50'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="flex-1">{item.label}</span>
                {active && <ChevronRight className="w-4 h-4" />}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="ml-64 mt-16 p-6">
        <div className="max-w-[1600px] mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}