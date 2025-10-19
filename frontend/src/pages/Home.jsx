import { useEffect, useMemo, useState } from "react";
import { Spinner, Banner, Empty } from "../components/Ui";

const API = import.meta.env.VITE_API || "http://localhost:8000";

export default function Home(){
  const [q, setQ] = useState("modern wooden chair");
  const [category, setCategory] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [results, setResults] = useState([]);
  const [sel, setSel] = useState(null);
  const [recs, setRecs] = useState([]);
  const [gen, setGen] = useState("");
  const [genLoading, setGenLoading] = useState(false);

  const priceOK = (p) => {
    const n = parseFloat(String(p).replace(/[^\d.]/g,""));
    if (Number.isNaN(n)) return false;
    if (minPrice && n < parseFloat(minPrice)) return false;
    if (maxPrice && n > parseFloat(maxPrice)) return false;
    return true;
  };

  const filtered = useMemo(()=>{
    return results.filter(r => {
      const okCat = category ? String(r.categories||"").toLowerCase().includes(category.toLowerCase()) : true;
      const okPrice = (!minPrice && !maxPrice) ? true : priceOK(r.price);
      return okCat && okPrice;
    });
  }, [results, category, minPrice, maxPrice,priceOK]);

  const search = async () => {
    setLoading(true); setErr(""); setSel(null); setRecs([]); setGen("");
    try{
      const r = await fetch(`${API}/search?q=${encodeURIComponent(q)}&k=12`);
      if(!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const j = await r.json();
      setResults(j.results || []);
    }catch(e){ setErr(String(e.message||e)); }
    finally{ setLoading(false); }
  };

  const recommend = async () => {
    if(!sel) return;
    setRecs([]); setGen("");
    try{
      const r = await fetch(`${API}/recommend/${sel.uniq_id}?k=6`);
      const j = await r.json();
      setRecs(j.recommended || []);
    }catch(e){ console.error(e); }
  };

  const generate = async () => {
    if(!sel) return;
    setGenLoading(true);
    try{
      const r = await fetch(`${API}/generate/${sel.uniq_id}`);
      const j = await r.json();
      setGen(j.generated_description || "");
    }catch(e){ setGen("⚠️ generation failed."); }
    finally{ setGenLoading(false); }
  };

  useEffect(()=>{ search(); },[]);

  return (
    <div>
      <h2 style={{margin:"6px 0 12px"}}>Prompt → Recommendations</h2>

      <div className="card" style={{marginBottom:12}}>
        <div className="row" style={{gap:10, flexWrap:"wrap"}}>
          <input className="input" style={{flex:2}} value={q} onChange={e=>setQ(e.target.value)} placeholder="Describe what you want…" />
          <input className="input" style={{flex:1}} value={category} onChange={e=>setCategory(e.target.value)} placeholder="Filter: category" />
          <input className="input" style={{width:120}} value={minPrice} onChange={e=>setMinPrice(e.target.value)} placeholder="Min ₹" />
          <input className="input" style={{width:120}} value={maxPrice} onChange={e=>setMaxPrice(e.target.value)} placeholder="Max ₹" />
          <button className="btn" onClick={search}>Search</button>
        </div>
      </div>

      {err && <Banner>⚠️ {err}</Banner>}

      {loading ? (
        <div className="grid">
          {Array.from({length:6}).map((_,i)=>(
            <div key={i} className="card"><div className="skel"/></div>
          ))}
        </div>
      ) : (
        <>
          {!filtered.length ? <Empty/> : (
            <div className="grid">
              {filtered.map((r)=>(
                <div key={r.uniq_id} className="card">
                  <h4>{r.title}</h4>
                  <div className="sub">{r.brand} {r.price ? `• ₹${r.price}` : ""}</div>
                  {r.images && (
                    <img
                      className="img"
                      src={String(r.images).split(",")[0]}
                      alt=""
                      onError={(e)=>{ e.currentTarget.style.display='none'; }}
                    />
                  )}
                  <div style={{marginTop:6}}>
                    <span className="badge">{r.categories?.split(",")[0] || "Uncategorized"}</span>
                  </div>
                  <button className="btn secondary" style={{marginTop:10}} onClick={()=>{ setSel(r); setGen(""); setRecs([]); }}>
                    Select
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {sel && (
        <>
          <h3 className="sectionTitle">Selected: {sel.title}</h3>
          <div className="row" style={{gap:8, marginBottom:8}}>
            <button className="btn" onClick={recommend}>Get Recommendations</button>
            <button className="btn secondary" onClick={generate}>Generate Description</button>
          </div>

          {genLoading ? <Spinner label="Generating description…"/> : (gen && <div className="card"><div className="sub" style={{whiteSpace:"pre-wrap"}}>{gen}</div></div>)}

          {!!recs.length && (
            <>
              <h4 className="sectionTitle">You might also like</h4>
              <div className="grid">
                {recs.map((r)=>(
                  <div key={r.uniq_id} className="card">
                    <h4>{r.title}</h4>
                    <div className="sub">{r.brand} {r.price ? `• ₹${r.price}` : ""}</div>
                    {r.images && <img className="img" src={String(r.images).split(",")[0]} alt="" onError={(e)=>{e.currentTarget.style.display='none'}}/>}
                    <div style={{marginTop:6}} className="kv">{r.categories}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
