import { useState, useMemo, useEffect } from "react";
import { Search, RefreshCw, CheckCircle2, Edit2, Save, X, ChevronDown, ChevronUp } from "lucide-react";
import api from "../api";
import toast from "react-hot-toast";
import ConfirmModal from "../components/ConfirmModal";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";
import ForecastDetailChart from "../components/ForecastDetailChart";

const MONTH_NAMES = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
];

const ProductExpandedContent = ({ product, isApproved, editingKey, editAmount, setEditAmount, startEditing, cancelEditing, saveEditing, fetchForecasts }) => {
    const [detailData, setDetailData] = useState(null);

    useEffect(() => {
        api.get(`/forecast/detail/${product.item_id}`).then(res => setDetailData(res.data)).catch(console.error);
    }, [product.item_id]);

    const historyYears = useMemo(() => {
        if (!detailData || !detailData.sales_history) return [];
        const allYears = [...new Set(detailData.sales_history.map(s => s.year))].sort((a, b) => a - b);
        return allYears.slice(-4); // Sadece son 4 yıl (Arayüzde tablo için)
    }, [detailData]);

    const forecastYears = useMemo(() => {
        if (!product.months || product.months.length === 0) return "";
        const years = [...new Set(product.months.map(m => m.date.slice(0, 4)))];
        return years.sort().join("-");
    }, [product.months]);

    const salesHistoryMap = useMemo(() => {
        const map = {};
        if (detailData && detailData.sales_history) {
            detailData.sales_history.forEach(s => {
                if (!map[s.month]) map[s.month] = {};
                map[s.month][s.year] = s.total_sales;
            });
        }
        return map;
    }, [detailData]);

    return (
        <div className="border-t border-gray-100 p-6 bg-gray-50/30 animate-in slide-in-from-top-2 duration-300">
            {/* AI Chart Component */}
            <div className="mb-8">
                <ForecastDetailChart itemId={product.item_id} hideTable={true} />
            </div>

            {/* Inline Monthly 12-Month Table */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 bg-gradient-to-r from-gray-50 to-slate-50 border-b border-gray-200 flex items-center justify-between">
                    <h4 className="font-semibold text-gray-800 text-sm">Aylık Tahmin ve Onay Tablosu</h4>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-gray-50/50 border-b border-gray-100">
                                <th className="px-5 py-3 text-left font-semibold text-gray-500 uppercase">Tarih (Ay)</th>
                                {historyYears.map(y => (
                                    <th key={y} className="px-5 py-3 text-right font-semibold text-gray-500 uppercase">{y}</th>
                                ))}
                                <th className="px-5 py-3 text-right font-semibold text-purple-400 uppercase bg-purple-50/30">Güven Aralığı</th>
                                <th className="px-5 py-3 text-right font-semibold text-indigo-500 uppercase bg-indigo-50/20">Tahmin Edilen Miktar ({forecastYears})</th>
                                <th className="px-5 py-3 text-right font-semibold text-gray-500 uppercase">Durum & İşlemler</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {product.months.map((item) => {
                                const key = `${item.item_id}-${item.date}`;
                                const isEditing = editingKey === key;
                                const rowLocked = isApproved || item.is_approved;

                                const monthIndex = parseInt(item.date.slice(5, 7), 10);
                                const monthName = MONTH_NAMES[monthIndex - 1];
                                const displayDate = monthName;

                                const historicalSales = salesHistoryMap[monthIndex] || {};

                                return (
                                    <tr key={key} className={rowLocked ? "bg-gray-50/40 text-gray-500" : "hover:bg-indigo-50/30"}>
                                        <td className="px-5 py-3 font-medium whitespace-nowrap">{displayDate}</td>

                                        {/* History Columns */}
                                        {historyYears.map(y => (
                                            <td key={y} className="px-5 py-3 text-right text-gray-600 tabular-nums">
                                                {historicalSales[y] != null ? Number(historicalSales[y]).toLocaleString("tr-TR", { minimumFractionDigits: 5, maximumFractionDigits: 5 }) : "—"}
                                            </td>
                                        ))}

                                        {/* Confidence Range */}
                                        <td className="px-5 py-3 text-right text-purple-500 bg-purple-50/20 tabular-nums text-xs">
                                            {item.yhat_lower != null && item.yhat_upper != null
                                                ? `${Number(item.yhat_lower).toLocaleString("tr-TR", { minimumFractionDigits: 5, maximumFractionDigits: 5 })} – ${Number(item.yhat_upper).toLocaleString("tr-TR", { minimumFractionDigits: 5, maximumFractionDigits: 5 })}`
                                                : "—"
                                            }
                                        </td>

                                        {/* Editable Forecast */}
                                        <td className="px-5 py-3 text-right font-semibold bg-indigo-50/10">
                                            {isEditing && !rowLocked ? (
                                                <input
                                                    type="number"
                                                    step="0.00001"
                                                    value={editAmount}
                                                    onChange={(e) => setEditAmount(e.target.value)}
                                                    className="w-32 px-2 py-1.5 border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 outline-none text-indigo-700 bg-white shadow-sm text-right"
                                                    autoFocus
                                                />
                                            ) : (
                                                <span className={`text-base ${rowLocked ? "text-gray-500" : "text-indigo-600"}`}>
                                                    {Number(item.amount).toLocaleString('tr-TR', { minimumFractionDigits: 5, maximumFractionDigits: 5 })}
                                                </span>
                                            )}
                                        </td>

                                        {/* Actions */}
                                        <td className="px-5 py-3 text-right">
                                            {rowLocked ? (
                                                <div className="flex justify-end pr-1">
                                                    <button disabled className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-400 rounded-lg transition-colors font-medium text-xs cursor-not-allowed border border-gray-200" title="Onaylı">
                                                        <CheckCircle2 size={14} /> Onaylı
                                                    </button>
                                                </div>
                                            ) : isEditing ? (
                                                <div className="flex justify-end gap-2 pr-1">
                                                    <button onClick={() => saveEditing(item.item_id, item.date)} className="flex items-center gap-1 text-green-700 bg-green-50 px-3 py-1.5 rounded-lg hover:bg-green-100 transition-colors font-medium text-xs">
                                                        <Save size={14} /> Kaydet
                                                    </button>
                                                    <button onClick={cancelEditing} className="flex items-center gap-1 text-red-600 bg-red-50 px-3 py-1.5 rounded-lg hover:bg-red-100 transition-colors font-medium text-xs">
                                                        <X size={14} /> İptal
                                                    </button>
                                                </div>
                                            ) : (
                                                <div className="flex justify-end gap-2 text-gray-400 pr-1">
                                                    <button onClick={() => startEditing(item)} className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-indigo-50 hover:text-indigo-600 text-gray-700 rounded-lg transition-colors border border-gray-200 font-medium text-xs shadow-sm" title="Düzenle">
                                                        <Edit2 size={14} /> Düzenle
                                                    </button>
                                                    <button onClick={async () => {
                                                        const tid = toast.loading("Onaylanıyor...");
                                                        try {
                                                            await api.post("/forecast/approve-row", { item_id: item.item_id, date: item.date });
                                                            toast.success("Ay onaylandı!", { id: tid });
                                                            fetchForecasts();
                                                        } catch (err) { toast.error("Hata!", { id: tid }); }
                                                    }} className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white hover:bg-emerald-700 rounded-lg transition-colors shadow-sm font-medium text-xs" title="Onayla">
                                                        <CheckCircle2 size={14} /> Onayla
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

const DemandForecast = () => {
    const [forecasts, setForecasts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [calculating, setCalculating] = useState(false);
    const [filters, setFilters] = useState({
        itemId: "",
        startDate: "",
        endDate: "",
    });

    // Editing State
    const [editingKey, setEditingKey] = useState(null); // combined item_id and date
    const [editAmount, setEditAmount] = useState("");
    const isApproved = useMemo(() => {
        if (forecasts.length === 0) return false;
        return forecasts.every(f => f.is_approved);
    }, [forecasts]);

    // Confirmation Modal State
    const [confirmAction, setConfirmAction] = useState({ isOpen: false, title: "", message: "", onConfirm: () => { }, type: "danger" });

    // Expandable Row State
    const [expandedItemKey, setExpandedItemKey] = useState(null);

    // Fetch Forecasts on Mount
    useEffect(() => {
        fetchForecasts();
    }, []);

    const fetchForecasts = async () => {
        setLoading(true);
        try {
            const response = await api.get("/forecast/temporary");
            setForecasts(response.data);
        } catch (error) {
            console.error("Error fetching forecasts:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleRecalculate = async () => {
        setCalculating(true);
        const toastId = toast.loading("Tahminler hesaplanıyor...");
        try {
            await api.post("/forecast/calculate");
            await fetchForecasts();
            toast.success("Tahminler güncellendi.", { id: toastId });
        } catch (error) {
            console.error("Error recalculating:", error);
            toast.error("Hesaplama sırasında hata oluştu.", { id: toastId });
        } finally {
            setCalculating(false);
        }
    };

    const triggerRecalculate = () => {
        setConfirmAction({
            isOpen: true,
            title: "Tahminleri Yeniden Hesapla",
            message: "Bütün tahminleri yeniden hesaplamak istediğinize emin misiniz? Bu işlem biraz zaman alabilir.",
            onConfirm: handleRecalculate,
            type: "warning"
        });
    };

    const handleApprove = async () => {
        const toastId = toast.loading("Tahminler onaylanıyor...");
        try {
            await api.post("/forecast/approve");
            await fetchForecasts();
            toast.success("Tahminler başarıyla onaylandı ve kaydedildi.", { id: toastId });
        } catch (error) {
            console.error("Error approving:", error);
            toast.error("Onaylama başarısız oldu.", { id: toastId });
        }
    };

    const triggerApprove = () => {
        setConfirmAction({
            isOpen: true,
            title: "Tahminleri Onayla",
            message: "Bu tahminleri onaylayıp geçmiş verilerine kaydetmek istediğinize emin misiniz?",
            onConfirm: handleApprove,
            type: "info"
        });
    };

    const startEditing = (item) => {
        if (isApproved) return;
        setEditingKey(`${item.item_id}-${item.date}`);
        setEditAmount(item.amount.toString());
    };

    const cancelEditing = () => {
        setEditingKey(null);
        setEditAmount("");
    };

    const saveEditing = async (item_id, date) => {
        const toastId = toast.loading("Güncelleniyor...");
        try {
            await api.put("/forecast/update", {
                item_id,
                date,
                amount: parseFloat(editAmount)
            });

            setForecasts(prev => prev.map(f =>
                (f.item_id === item_id && f.date === date)
                    ? { ...f, amount: parseFloat(editAmount) }
                    : f
            ));

            toast.success("Tahmin güncellendi.", { id: toastId });
            setEditingKey(null);
        } catch (error) {
            console.error("Error updating forecast:", error);
            toast.error("Güncelleme başarısız.", { id: toastId });
        }
    };

    const clearFilters = () => {
        setFilters({
            itemId: "",
            startDate: "",
            endDate: "",
        });
    };

    // Filter Logic
    const filteredData = useMemo(() => {
        return forecasts.filter((item) => {
            const matchesId = item.item_id.toLowerCase().includes(filters.itemId.toLowerCase());
            return matchesId; 
        });
    }, [forecasts, filters]);

    // Grouping by Product
    const groupedProducts = useMemo(() => {
        const productMap = {};
        filteredData.forEach(item => {
            if (!productMap[item.item_id]) {
                productMap[item.item_id] = {
                    item_id: item.item_id,
                    totalForecast: 0,
                    months: []
                };
            }
            productMap[item.item_id].totalForecast += item.amount;
            productMap[item.item_id].months.push(item);
        });

        Object.values(productMap).forEach(prod => {
            prod.months.sort((a, b) => a.date.localeCompare(b.date));
        });

        return Object.values(productMap).sort((a, b) => a.item_id.localeCompare(b.item_id));
    }, [filteredData]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFilters((prev) => ({ ...prev, [name]: value }));
    };

    // Apply Infinite Scroll
    const { visibleData, hasMore, loaderRef } = useInfiniteScroll(groupedProducts, filters);

    if (loading && !calculating) return <div className="p-6">Yükleniyor...</div>;

    return (
        <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300 overflow-hidden">
            {/* Header */}
            <div className="flex-shrink-0 flex justify-between items-center px-2">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                        Tahminleme Ana Sayfası
                    </h1>
                    <p className="text-gray-500 mt-1">Gelecek dönem talep ve üretim tahminleri — Ürün Bazlı Görünüm.</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={triggerApprove}
                        disabled={loading || groupedProducts.length === 0 || isApproved}
                        className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-white shadow-lg active:scale-95 transition-all
                            ${isApproved ? "bg-gray-400 cursor-not-allowed" : "bg-green-600 hover:bg-green-700 shadow-green-500/20"}`}
                    >
                        <CheckCircle2 size={20} />
                        <span>{isApproved ? "Tümü Onaylı" : "Tümünü Onayla"}</span>
                    </button>
                    <button
                        onClick={triggerRecalculate}
                        disabled={calculating}
                        className={`flex items-center gap-2 px-5 py-2.5 rounded-xl transition-all shadow-lg active:scale-95 ${calculating
                            ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                            : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-500/20"
                            }`}
                    >
                        <RefreshCw size={20} className={calculating ? "animate-spin" : ""} />
                        <span>{calculating ? "Hesaplanıyor..." : "Hesapla"}</span>
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="flex-shrink-0 bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap items-center gap-4 mx-2">
                <div className="relative flex-1 min-w-[200px]">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                    <input
                        type="text"
                        name="itemId"
                        placeholder="Ürün Kodu Ara..."
                        value={filters.itemId}
                        onChange={handleInputChange}
                        className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                    />
                </div>

                <div className="flex items-center gap-3 ml-auto">
                    <button
                        onClick={clearFilters}
                        className="px-6 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium border border-gray-200"
                    >
                        Aramayı Temizle
                    </button>

                    {isApproved && (
                        <div className="flex items-center gap-2 text-amber-600 bg-amber-50 px-4 py-2 rounded-lg border border-amber-100 text-sm font-medium animate-in slide-in-from-right-2 duration-300">
                            <CheckCircle2 size={16} />
                            Genel Onay Verildi
                        </div>
                    )}
                </div>
            </div>

            {/* Product Table */}
            <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-4">
                {visibleData.length > 0 ? (
                    <>
                        {visibleData.map((product) => {
                            const isExpanded = expandedItemKey === product.item_id;
                            return (
                                <div key={product.item_id} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                                    {/* Product Main Row */}
                                    <div
                                    onClick={() => setExpandedItemKey(isExpanded ? null : product.item_id)}
                                    className="flex items-center justify-between p-5 cursor-pointer hover:bg-gray-50/50 transition-colors"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600">
                                            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-bold text-gray-900">{product.item_id}</h3>
                                            <p className="text-sm text-gray-500">Önümüzdeki Yıl İçin Toplam Tahmin: <span className="font-semibold text-indigo-600">{Number(product.totalForecast).toLocaleString("tr-TR", { minimumFractionDigits: 5, maximumFractionDigits: 5 })} Birim</span></p>
                                        </div>
                                    </div>
                                </div>

                                {/* Expanded Details */}
                                {isExpanded && (
                                    <ProductExpandedContent
                                        product={product}
                                        isApproved={isApproved}
                                        editingKey={editingKey}
                                        editAmount={editAmount}
                                        setEditAmount={setEditAmount}
                                        startEditing={startEditing}
                                        cancelEditing={cancelEditing}
                                        saveEditing={saveEditing}
                                        fetchForecasts={fetchForecasts}
                                    />
                                )}
                                </div>
                            );
                        })}

                        {hasMore && (
                            <div ref={loaderRef} className="py-6 flex justify-center items-center">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="text-gray-400 text-center py-20 bg-white rounded-2xl border border-gray-100">
                        Gösterilecek ürün veya tahmin bulunamadı.
                    </div>
                )}
            </div>

            <ConfirmModal
                isOpen={confirmAction.isOpen}
                onClose={() => setConfirmAction({ ...confirmAction, isOpen: false })}
                onConfirm={confirmAction.onConfirm}
                title={confirmAction.title}
                message={confirmAction.message}
                type={confirmAction.type}
            />
        </div>
    );
};

export default DemandForecast;
