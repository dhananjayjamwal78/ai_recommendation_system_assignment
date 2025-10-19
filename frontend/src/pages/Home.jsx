import { useEffect, useState } from "react";
const API = import.meta.env.VITE_API || "http://localhost:8000";

export default function Home(){
  const [q, setQ] = useState("modern wooden chair");
  const [results, setResults] = useState([]);
  const [sel, setSel] = useState(null);
  const [recs, setRecs] = useState([]);
  const [gen, setGen] = useState("");

  const search = async () => {
    try{
      const r = await fetch(`${API}/search?q=${encodeURIComponent(q)}&k=6`);
      const j = await r.json();
      setResults(j.results || []);
    }catch(e){ console.error(e); }
  };

  const pick = (row) => {
    setSel(row);
    setGen("");
    setRecs([]);
  };

  const recommend = async () => {
    if(!sel) return;
    const r = await fetch(`${API}/recommend/${sel.uniq_id}?k=5`);
    const j = await r.json();
    setRecs(j.recommended || []);
  };

  const generate = async () => {
    if(!sel) return;
    const r = await fetch(`${API}/generate/${sel.uniq_id}`);
    const j = await r.json();
    setGen(j.generated_description || "");
  };

  useEffect(()=>{ search(); },[]);

  return (
    <div style={{padding:16}}>
      <h2>Prompt → Recommendations</h2>
      <div style={{display:'flex', gap:8}}>
        <input style={{flex:1}} value={q} onChange={e=>setQ(e.target.value)} />
        <button onClick={search}>Search</button>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(240px,1fr))', gap:12, marginTop:12}}>
        {results.map((r)=>(
          <div key={r.uniq_id} style={{border:'1px solid #ddd', padding:12, borderRadius:8}}>
            <div style={{fontWeight:600}}>{r.title}</div>
            <div style={{fontSize:12, opacity:.7}}>{r.brand} • ₹{r.price}</div>
            {r.images && <img src={String(r.images).split(',')[0]} alt="" style={{width:'100%', height:140, objectFit:'cover', marginTop:6}} onError={(e)=>e.currentTarget.style.display='none'}/>}
            <div style={{fontSize:12, opacity:.7, marginTop:6}}>{r.categories}</div>
            <button style={{marginTop:8}} onClick={()=>pick(r)}>Select</button>
          </div>
        ))}
      </div>

      {sel && (
        <>
          <h3 style={{marginTop:16}}>Selected: {sel.title}</h3>
          <div style={{display:'flex', gap:8}}>
            <button onClick={recommend}>Get Recommendations</button>
            <button onClick={generate}>Generate Description</button>
          </div>
          {gen && <p style={{whiteSpace:'pre-wrap', marginTop:8}}>{gen}</p>}
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(240px,1fr))', gap:12, marginTop:12}}>
            {recs.map((r)=>(
              <div key={r.uniq_id} style={{border:'1px solid #ddd', padding:12, borderRadius:8}}>
                <div style={{fontWeight:600}}>{r.title}</div>
                <div style={{fontSize:12, opacity:.7}}>{r.brand} • ₹{r.price}</div>
                {r.images && <img src={String(r.images).split(',')[0]} alt="" style={{width:'100%', height:140, objectFit:'cover', marginTop:6}} onError={(e)=>e.currentTarget.style.display='none'}/>}
                <div style={{fontSize:12, opacity:.7, marginTop:6}}>{r.categories}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
