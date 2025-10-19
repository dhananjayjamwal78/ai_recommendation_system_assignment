import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Spinner, Banner } from "../components/Ui";

const API = import.meta.env.VITE_API || "http://localhost:8000";

export default function Analytics(){
  const [catData, setCatData] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(()=>{
    (async ()=>{
      try{
        const r = await fetch(`${API}/analytics/summary`);
        if(!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        const j = await r.json();
        setCatData(Object.entries(j.category_counts || {}).map(([category, count]) => ({category, count})));
        setStats(j.price_stats || null);
      }catch(e){ setErr(String(e.message||e)); }
      finally{ setLoading(false); }
    })();
  },[]);

  if (loading) return <Spinner label="Loading analytics…"/>;
  if (err) return <Banner>⚠️ {err}</Banner>;

  return (
    <div>
      <h2 style={{margin:"6px 0 12px"}}>Analytics</h2>

      <div className="card">
        <h4 style={{margin:"0 0 8px 0"}}>Products by Category</h4>
        <div style={{height:320}}>
          <ResponsiveContainer>
            <BarChart data={catData}>
              <XAxis dataKey="category" tick={{fill:"#9aa7bd"}}/>
              <YAxis tick={{fill:"#9aa7bd"}}/>
              <Tooltip contentStyle={{background:"#0f1621", border:"1px solid #22304a", color:"#e8eef7"}}/>
              <Bar dataKey="count" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {stats && (
        <div className="card" style={{marginTop:12}}>
          <h4 style={{margin:"0 0 8px 0"}}>Price Summary</h4>
          <pre className="sub" style={{whiteSpace:"pre-wrap"}}>{JSON.stringify(stats, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
