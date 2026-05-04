import { TrendingUp, ShieldCheck, ChevronLeft, ChevronRight } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useState } from "react";

export const SIDEBAR_ITEMS = [
    { name: "Talep Tahmin", icon: TrendingUp, path: "/demand-forecast", description: "AI destekli gelecek dönem talep ve üretim tahminleri." },
    { name: "Emniyet Stok", icon: ShieldCheck, path: "/safety-stock", description: "Emniyet stoku hesaplamaları ve optimizasyonu." },
];

const Sidebar = () => {
    const location = useLocation();
    const [isCollapsed, setIsCollapsed] = useState(false);

    return (
        <div className={`h-screen bg-gray-900 text-white flex flex-col border-r border-gray-800 transition-all duration-300 relative shrink-0 z-50 ${isCollapsed ? 'w-20' : 'w-64'}`}>

            {/* Toggle Button */}
            <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="absolute -right-3 top-8 bg-gray-800 border border-gray-700 rounded-full p-1 hover:bg-gray-700 transition-colors z-50 text-gray-400 hover:text-white shadow-lg"
            >
                {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>

            <div className="p-6 border-b border-gray-800 shrink-0 h-[73px] flex items-center justify-center overflow-hidden">
                <h1 className={`font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent transition-all duration-300 whitespace-nowrap ${isCollapsed ? 'text-xl' : 'text-2xl'}`}>
                    {isCollapsed ? 'OS-AI' : 'OptiStock AI'}
                </h1>
            </div>

            <nav className="flex-1 overflow-y-auto overflow-x-hidden py-4 custom-scrollbar">
                <ul className="space-y-2 px-3">
                    {SIDEBAR_ITEMS.map((item) => {
                        const isActive = location.pathname === item.path;
                        return (
                            <li key={item.path}>
                                <Link
                                    to={item.path}
                                    title={isCollapsed ? item.name : undefined}
                                    className={`flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'} px-4 py-3 rounded-xl transition-all duration-200 group ${isActive
                                        ? "bg-blue-600 shadow-lg shadow-blue-500/20 text-white"
                                        : "text-gray-400 hover:bg-gray-800 hover:text-white"
                                        }`}
                                >
                                    <item.icon
                                        size={22}
                                        className={`shrink-0 transition-colors ${isActive ? "text-white" : "text-gray-400 group-hover:text-white"}`}
                                    />
                                    {!isCollapsed && (
                                        <span className="font-medium whitespace-nowrap overflow-hidden transition-all duration-300">
                                            {item.name}
                                        </span>
                                    )}
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>

            <div className={`p-4 border-t border-gray-800 flex flex-col items-center justify-center overflow-hidden shrink-0 transition-all duration-300 ${isCollapsed ? 'h-24 py-2' : ''}`}>
                {!isCollapsed ? (
                    <div id="sys-signature" className="text-center w-full">
                        <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">Developed By</p>
                        <p className="text-xs font-semibold text-gray-400 font-mono tracking-wide truncate">utku altan özkale</p>
                    </div>
                ) : (
                    <div className="text-[10px] font-bold text-gray-500 rotate-[-90deg] whitespace-nowrap tracking-widest h-full flex items-center">
                        U.A.Ö.
                    </div>
                )}
            </div>
        </div>
    );
};

export default Sidebar;
