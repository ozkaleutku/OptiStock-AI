import { useState, useMemo, useEffect } from "react";
import { Search, Filter, Layers, Calendar, ArrowLeft, Save, CheckCircle, ChevronDown, ChevronUp } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import toast from "react-hot-toast";
import ConfirmModal from "../components/ConfirmModal";
import ConsumptionChart from "../components/ConsumptionChart";

const formatQuantity = (value, unit) => {
    if (value == null) return "0,00000";
    const num = parseFloat(value);
    if (isNaN(num)) return value;

    return num.toLocaleString("tr-TR", { minimumFractionDigits: 5, maximumFractionDigits: 5 });
};

const SafetyStockExpandedContent = ({ product, handleManualChange, handlePreferenceChange, handleApproveRow }) => {
    return (
        <div className="border-t border-gray-100 p-6 bg-gray-50/30 animate-in slide-in-from-top-2 duration-300">
            <ConsumptionChart itemId={product.item_id} />
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-700 uppercase bg-gray-50 border-b border-gray-200">
                        <tr>
                            <th className="px-6 py-4">Tarih</th>
                            <th className="px-6 py-4 bg-emerald-50 text-emerald-700 border-l border-emerald-100">AI Sonucu</th>
                            <th className="px-6 py-4 bg-blue-50 text-blue-700 border-l border-blue-100">Formül</th>
                            <th className="px-6 py-4 bg-orange-50 text-orange-700 border-l border-orange-100">Manuel Giriş</th>
                            <th className="px-6 py-4 border-l border-gray-200">Tercih</th>
                            <th className="px-6 py-4 bg-gray-100 font-bold border-l border-gray-200">Sonuç</th>
                            <th className="px-6 py-4 bg-emerald-50 text-emerald-700 border-l border-emerald-100 text-center">İşlem</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {product.months.map((row) => (
                            <tr key={row.ui_id} className={`bg-white hover:bg-gray-50/50 transition-colors ${row.is_approved ? "border-l-4 border-l-emerald-500" : ""}`}>
                                <td className="px-6 py-4 text-gray-600">
                                    {row.date}
                                    {row.is_approved && <span className="ml-2 px-2 py-0.5 bg-emerald-100 text-emerald-700 text-[10px] font-bold rounded-full uppercase">Onaylı</span>}
                                </td>
                                <td className="px-6 py-4 font-bold text-emerald-600 bg-emerald-50/30 border-l border-emerald-100">
                                    {formatQuantity(row.amount, row.item_quantity_type)} <span className="text-xs font-normal text-gray-500">{row.item_quantity_type}</span>
                                </td>
                                <td className="px-6 py-4 text-blue-700 bg-blue-50/30 border-l border-blue-100">
                                    {formatQuantity(row.formula_result, row.item_quantity_type)}
                                </td>
                                <td className="px-6 py-4 bg-orange-50/30 border-l border-orange-100">
                                    <input
                                        type="number"
                                        step="0.00001"
                                        className="w-32 border border-orange-200 rounded-lg px-2 py-1.5 focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 outline-none text-gray-700 bg-white"
                                        value={row.manualInput}
                                        onChange={(e) => handleManualChange(row.ui_id, e.target.value)}
                                        placeholder="Amount"
                                    />
                                </td>
                                <td className="px-6 py-4 border-l border-gray-200">
                                    <select
                                        className="w-full border border-gray-200 rounded-lg px-2 py-1.5 bg-white outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 cursor-pointer"
                                        value={row.preference}
                                        onChange={(e) => handlePreferenceChange(row.ui_id, e.target.value)}
                                    >
                                        <option value="AI">AI (Öneri)</option>
                                        <option value="Formula">Formül</option>
                                        <option value="Manual">Manuel</option>
                                    </select>
                                </td>
                                <td className="px-6 py-4 font-bold text-gray-900 bg-gray-50 border-l border-gray-200">
                                    {formatQuantity(row.finalAmount, row.item_quantity_type)} <span className="text-xs font-normal text-gray-500">{row.item_quantity_type}</span>
                                </td>
                                <td className="px-6 py-4 border-l border-gray-200 text-center">
                                    <button
                                        onClick={() => handleApproveRow(row.ui_id)}
                                        className={`p-2 rounded-full transition-all flex items-center justify-center mx-auto ${row.is_approved ? "text-emerald-500 bg-emerald-50" : "text-gray-300 hover:text-emerald-600 hover:bg-emerald-50"}`}
                                        title={row.is_approved ? "Zaten Onaylı (Güncellemek için tekrar tıklayın)" : "Onayla"}
                                    >
                                        <CheckCircle size={22} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

const SafetyStockComparison = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [comparisonData, setComparisonData] = useState([]);
    const [expandedItemKey, setExpandedItemKey] = useState(null);

    const [filters, setFilters] = useState({
        itemId: "",
        month: ""
    });

    const [isApproveConfirmOpen, setIsApproveConfirmOpen] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const response = await api.get("/safety-stock/temporary");
            
            const initial = response.data.map((item, index) => {
                let preference = item.preference || "AI";
                let manualInput = item.manual_amount != null ? item.manual_amount.toString() : "";
                let finalAmount = item.ai_amount;

                // If preference was saved, respect it. Otherwise use the heuristic
                if (!item.preference) {
                    if (item.formula_result > 0 && !(item.ai_amount > 0)) {
                        preference = "Formula";
                    }
                }
                
                // Calculate finalAmount based on preference
                if (preference === "AI") finalAmount = item.ai_amount;
                else if (preference === "Formula") finalAmount = item.formula_result || 0;
                else if (preference === "Manual") finalAmount = parseFloat(manualInput) || 0;

                return {
                    ...item,
                    ui_id: `v_${Date.now()}_${index}`,
                    preference,
                    manualInput,
                    finalAmount,
                    amount: item.ai_amount,
                    formula_result: item.formula_result || 0
                };
            });
            setComparisonData(initial);
        } catch (error) {
            console.error("Error fetching safety stock data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handlePreferenceChange = (ui_id, value) => {
        setComparisonData(prev => prev.map(item => {
            if (item.ui_id !== ui_id) return item;
            
            let finalAmount = item.finalAmount;
            if (value === "AI") finalAmount = item.amount;
            else if (value === "Formula") finalAmount = item.formula_result || 0;
            else if (value === "Manual") finalAmount = parseFloat(item.manualInput) || 0;

            return { ...item, preference: value, finalAmount };
        }));
    };

    const handleManualChange = (ui_id, value) => {
        setComparisonData(prev => prev.map(item => {
            if (item.ui_id !== ui_id) return item;
            
            const manualInput = value;
            let finalAmount = item.finalAmount;
            if (item.preference === "Manual") {
                finalAmount = parseFloat(value) || 0;
            }
            return { ...item, manualInput, finalAmount };
        }));
    };

    const handleApproveRow = async (ui_id) => {
        const item = comparisonData.find(d => d.ui_id === ui_id);
        if (!item) return;

        const payload = [{
            item_id: item.item_id,
            date: item.date,
            amount: item.finalAmount,
            preference: item.preference,
            item_quantity_type: item.item_quantity_type
        }];

        const toastId = toast.loading(`${item.item_id} onaylanıyor...`);
        try {
            await api.post("/safety-stock/approve", payload);
            toast.success(`${item.item_id} onaylandı!`, { id: toastId });
            setComparisonData(prev => prev.map(d => 
                d.ui_id === ui_id ? { ...d, is_approved: true } : d
            ));
        } catch (error) {
            console.error("Approval error:", error);
            toast.error("Hata oluştu.", { id: toastId });
        }
    };

    const handleApprove = async () => {
        const toastId = toast.loading("Emniyet stokları güncelleniyor...");
        try {
            // Bulk approval
            const payload = comparisonData.map(item => ({
                item_id: item.item_id,
                date: item.date,
                amount: item.finalAmount,
                preference: item.preference,
                item_quantity_type: item.item_quantity_type
            }));
            
            await api.post("/safety-stock/approve", payload);
            toast.success("Tüm emniyet stokları başarıyla güncellendi!", { id: toastId });
            setComparisonData(prev => prev.map(item => ({ ...item, is_approved: true })));
        } catch (error) {
            console.error("Approval error:", error);
            toast.error("Onaylama sırasında hata oluştu.", { id: toastId });
        }
    };

    const filteredData = useMemo(() => {
        return comparisonData.filter(item => {
            const matchesId = item.item_id.toLowerCase().includes(filters.itemId.toLowerCase());
            const matchesMonth = filters.month ? item.date.startsWith(filters.month) : true;
            return matchesId && matchesMonth;
        });
    }, [comparisonData, filters]);

    const groupedProducts = useMemo(() => {
        const productMap = {};
        filteredData.forEach(item => {
            if (!productMap[item.item_id]) {
                productMap[item.item_id] = {
                    item_id: item.item_id,
                    item_type: item.item_type,
                    months: []
                };
            }
            productMap[item.item_id].months.push(item);
        });

        Object.values(productMap).forEach(prod => {
            prod.months.sort((a, b) => a.date.localeCompare(b.date));
        });

        return Object.values(productMap).sort((a, b) => a.item_id.localeCompare(b.item_id));
    }, [filteredData]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFilters(prev => ({ ...prev, [name]: value }));
    };

    if (loading) return <div className="p-8 text-center text-gray-500">Yükleniyor...</div>;

    return (
        <div className="h-full flex flex-col space-y-6 animate-in fade-in duration-300">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <button
                        onClick={() => navigate("/safety-stock")}
                        className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-2 transition-colors"
                    >
                        <ArrowLeft size={18} /> Geri Dön
                    </button>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                        <Layers className="text-emerald-600" /> Karşılaştırma ve Onay
                    </h1>
                    <p className="text-gray-500 mt-1">Ürün bazlı gruplanmış görünümlü karşılaştırma ekranı.</p>
                </div>
                <div>
                    <button
                        onClick={() => setIsApproveConfirmOpen(true)}
                        disabled={comparisonData.length === 0}
                        className={`flex items-center gap-2 px-6 py-3 rounded-xl text-white font-medium shadow-lg shadow-emerald-500/20 active:scale-95 transition-all ${comparisonData.length === 0 ? "bg-gray-400 cursor-not-allowed" : "bg-emerald-600 hover:bg-emerald-700"}`}
                    >
                        <Save size={20} />
                        Tümünü Onayla ve Kaydet
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-4 mb-6">
                <div className="relative flex-1 w-full md:w-auto">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                    <input
                        type="text"
                        name="itemId"
                        placeholder="Ürün Kodu Ara..."
                        value={filters.itemId}
                        onChange={handleInputChange}
                        className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                    />
                </div>
                <button
                    onClick={() => setFilters({ itemId: "", month: "" })}
                    className="px-6 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium border border-gray-200 w-full md:w-auto"
                >
                    Temizle
                </button>
            </div>

            {/* Grouped Content */}
            <div className="flex-1 overflow-y-auto space-y-4 pb-10">
                {groupedProducts.length > 0 ? (
                    groupedProducts.map((product) => {
                        const isExpanded = expandedItemKey === product.item_id;
                        return (
                            <div key={product.item_id} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                                <div
                                    onClick={() => setExpandedItemKey(isExpanded ? null : product.item_id)}
                                    className="flex items-center justify-between p-5 cursor-pointer hover:bg-gray-50/50 transition-colors"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
                                            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-bold text-gray-900">{product.item_id}</h3>
                                            <p className="text-sm text-gray-500">{product.months.length} ay için bekleyen plan.</p>
                                        </div>
                                    </div>
                                </div>

                                {isExpanded && (
                                    <SafetyStockExpandedContent
                                        product={product}
                                        handleManualChange={handleManualChange}
                                        handlePreferenceChange={handlePreferenceChange}
                                        handleApproveRow={handleApproveRow}
                                    />
                                )}
                            </div>
                        );
                    })
                ) : (
                    <div className="text-gray-400 text-center py-20 bg-white rounded-2xl border border-gray-100">
                        Gösterilecek ürün bulunamadı.
                    </div>
                )}
            </div>

            <ConfirmModal
                isOpen={isApproveConfirmOpen}
                onClose={() => setIsApproveConfirmOpen(false)}
                onConfirm={handleApprove}
                title="Emniyet Stoklarını Onayla"
                message="Listedeki tüm ürünler için seçilen tercihleri onaylayıp kaydetmek istediğinize emin misiniz?"
                confirmText="Onayla ve Kaydet"
                type="warning"
            />
        </div>
    );
};

export default SafetyStockComparison;
