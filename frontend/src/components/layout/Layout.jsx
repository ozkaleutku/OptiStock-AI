import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

const Layout = () => {
    return (
        <div className="flex bg-gray-50 text-gray-900 h-screen overflow-hidden w-full">
            <Sidebar />
            <div className="flex-1 h-screen w-full flex flex-col min-w-0 overflow-hidden">
                <main className="flex-1 p-8 min-h-0">
                    <Outlet />
                </main>
                <footer className="w-full py-4 shrink-0 flex items-center justify-center">
                    <div className="flex items-center gap-2 text-[11px] text-gray-400/40 hover:text-gray-400/80 transition-colors duration-500 select-none">
                        <span className="font-semibold tracking-widest uppercase">OptiStock AI</span>
                        <div className="w-1 h-1 rounded-full bg-gray-300/30"></div>
                        <span className="font-mono tracking-tight">Developed by Utku Altan Özkale</span>
                    </div>
                </footer>
            </div>
        </div>
    );
};

export default Layout;
