import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Home from "./pages/Home";
import Analytics from "./pages/Analytics";

export default function App() {
  return (
    <BrowserRouter>
      <nav style={{padding:12, display:"flex", gap:12, borderBottom:"1px solid #eee"}}>
        <Link to="/">Recommend</Link>
        <Link to="/analytics">Analytics</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analytics" element={<Analytics />} />
      </Routes>
    </BrowserRouter>
  );
}
