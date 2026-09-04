import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Landing from "@/pages/Landing";
import Admin from "@/pages/Admin";
import ReviewPage from "@/pages/ReviewPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/avis/:token" element={<ReviewPage />} />
        <Route path="/admin/*" element={<Admin />} />
      </Routes>
      <Toaster
        position="top-center"
        theme="dark"
        toastOptions={{
          style: { background: "#0F1C30", border: "1px solid rgba(0,240,255,0.3)", color: "#F8FAFC" },
        }}
      />
    </BrowserRouter>
  );
}

export default App;
