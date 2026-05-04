import React from 'react';
import { X, AlertTriangle } from 'lucide-react';

const ConfirmModal = ({
    isOpen,
    onClose,
    onConfirm,
    title = "Emin misiniz?",
    message = "Bu işlem geri alınamaz.",
    confirmText = "Onayla",
    cancelText = "İptal",
    type = "danger" // danger, warning, info
}) => {
    if (!isOpen) return null;

    const colors = {
        danger: "bg-red-100 text-red-600 hover:bg-red-700 bg-red-600",
        warning: "bg-orange-100 text-orange-600 hover:bg-orange-700 bg-orange-600",
        info: "bg-blue-100 text-blue-600 hover:bg-blue-700 bg-blue-600"
    };

    const buttonColors = {
        danger: "bg-red-600 hover:bg-red-700 shadow-red-500/20",
        warning: "bg-orange-600 hover:bg-orange-700 shadow-orange-500/20",
        info: "bg-blue-600 hover:bg-blue-700 shadow-blue-500/20"
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl p-6 scale-100 animate-in zoom-in-95 duration-200 overflow-hidden relative">
                <button
                    onClick={onClose}
                    className="absolute right-4 top-4 text-gray-400 hover:text-gray-600 transition-colors"
                >
                    <X size={20} />
                </button>

                <div className="text-center">
                    <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 ${colors[type].split(' ').slice(0, 2).join(' ')}`}>
                        <AlertTriangle size={32} />
                    </div>

                    <h2 className="text-xl font-bold text-gray-900 mb-2">{title}</h2>
                    <p className="text-sm text-gray-500 mb-6">
                        {message}
                    </p>

                    <div className="flex gap-3">
                        <button
                            onClick={onClose}
                            className="flex-1 px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium transition-colors"
                        >
                            {cancelText}
                        </button>
                        <button
                            onClick={() => {
                                onConfirm();
                                onClose();
                            }}
                            className={`flex-1 px-4 py-2 text-white rounded-lg font-medium shadow-lg transition-all active:scale-95 ${buttonColors[type]}`}
                        >
                            {confirmText}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ConfirmModal;
