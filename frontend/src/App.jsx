import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Layout from "./components/layout/Layout";
import DemandForecast from "./pages/DemandForecast";
import SafetyStock from "./pages/SafetyStock";
import SafetyStockComparison from "./pages/SafetyStockComparison";

// Placeholder components for other pages
const PlaceholderPage = ({ title }) => (
  <div className="p-4">
    <h1 className="text-2xl font-bold mb-4">{title}</h1>
    <p>Bu sayfa yapım aşamasındadır.</p>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ duration: 5000 }} />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DemandForecast />} />
          <Route path="demand-forecast" element={<DemandForecast />} />
          <Route path="safety-stock" element={<SafetyStock />} />
          <Route path="safety-stock/compare" element={<SafetyStockComparison />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
