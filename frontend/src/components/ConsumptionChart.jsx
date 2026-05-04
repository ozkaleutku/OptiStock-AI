import { useState, useEffect, useMemo } from "react";
import { Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart, Line } from "recharts";
import { TrendingUp } from "lucide-react";
import api from "../api";

const MONTH_NAMES = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];

const ConsumptionChart = ({ itemId }) => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchConsumption = async () => {
            setLoading(true);
            try {
                const res = await api.get(`/consumption/${itemId}`);
                setData(res.data);
            } catch (err) {
                console.error("Consumption fetch error:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchConsumption();
    }, [itemId]);

    const chartData = useMemo(() => {
        return data
            .filter(d => d.date >= "2024-01-01") // Geçici filtre: 2024 ve sonrası // silinecek
            .map(d => {
                const date = new Date(d.date);
                return {
                    ...d,
                    displayDate: `${MONTH_NAMES[date.getMonth()]} ${date.getFullYear().toString().slice(2)}`,
                    consumption: parseFloat(d.consumption) || 0,
                    historical_ss: parseFloat(d.historical_ss) || null,
                    future_ai: parseFloat(d.future_ai) || null
                };
            });
    }, [data]);

    if (loading) return <div className="h-40 flex items-center justify-center text-gray-400">Yükleniyor...</div>;
    if (data.length === 0) return <div className="h-40 flex items-center justify-center text-gray-400">Veri bulunamadı.</div>;

    return (
        <div className="bg-gradient-to-br from-slate-50 via-white to-indigo-50/10 rounded-2xl border border-gray-100 p-6 shadow-sm mb-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <div className="p-2 bg-indigo-100 rounded-xl">
                        <TrendingUp size={18} className="text-indigo-600" />
                    </div>
                    <div>
                        <h3 className="font-bold text-gray-800 text-base">Emniyet Stoğu & Tüketim Analizi</h3>
                    </div>
                </div>
            </div>
            <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={chartData}>
                    <defs>
                        <linearGradient id="colorConsume" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f97316" stopOpacity={0.1} />
                            <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" strokeOpacity={0.5} />
                    <XAxis
                        dataKey="displayDate"
                        tick={{ fontSize: 10, fill: "#9ca3af" }}
                        axisLine={false}
                        tickLine={false}
                        minTickGap={20}
                    />
                    <YAxis
                        tick={{ fontSize: 10, fill: "#9ca3af" }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(val) => val.toLocaleString("tr-TR")}
                    />
                    <Tooltip
                        contentStyle={{
                            borderRadius: '16px',
                            border: 'none',
                            boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)',
                            background: 'rgba(255, 255, 255, 0.95)',
                            backdropFilter: 'blur(4px)',
                            padding: '12px'
                        }}
                        formatter={(val, name) => {
                            const labels = {
                                consumption: "Fiili Tüketim",
                                historical_ss: "Geçmiş Emniyet Stoğu",
                                future_ai: "Gelecek AI Önerisi"
                            };
                            return [val ? val.toLocaleString("tr-TR") : "—", labels[name] || name];
                        }}
                    />
                    <Legend
                        wrapperStyle={{ paddingTop: 20, fontSize: 12 }}
                        formatter={(value) => {
                            const labels = {
                                consumption: "Fiili Tüketim",
                                historical_ss: "Geçmiş SS",
                                future_ai: "Gelecek AI Önerisi"
                            };
                            return <span className="text-gray-600 font-medium">{labels[value] || value}</span>;
                        }}
                    />

                    {/* Consumption Area */}
                    <Area
                        type="monotone"
                        dataKey="consumption"
                        stroke="#f97316"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorConsume)"
                        name="consumption"
                    />

                    {/* Historical Safety Stock Line */}
                    <Line
                        type="monotone"
                        dataKey="historical_ss"
                        stroke="#3b82f6"
                        strokeWidth={2.5}
                        dot={{ fill: "#3b82f6", r: 3 }}
                        activeDot={{ r: 5 }}
                        name="historical_ss"
                        connectNulls
                    />

                    {/* Future AI Safety Stock Line */}
                    <Line
                        type="monotone"
                        dataKey="future_ai"
                        stroke="#10b981"
                        strokeWidth={3}
                        strokeDasharray="5 5"
                        dot={{ fill: "#10b981", r: 4 }}
                        activeDot={{ r: 6 }}
                        name="future_ai"
                        connectNulls
                    />
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    );
};

export default ConsumptionChart;
