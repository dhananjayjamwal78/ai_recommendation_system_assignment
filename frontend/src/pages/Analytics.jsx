import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
const API = import.meta.env.VITE_API || "http://localhost:8000";

export default function Analytics(){
  const [catData, setCatData] = useState([]);
  const [stats, setStats] = useState(null);

  useEffect(()=>{
    (async ()=>{
      const r = await fetch(`${API}/analytics/summary`);
      const j = await r.json();
      setCatData(Object.entries(j.category_counts || {}).map(([category, count]) => ({category, count})));
      setStats(j.price_stats || null);
    })();
  },[]);

  return (
    <div style={{padding:16}}>
      <h2>Analytics</h2>
      <h4>Products by Category</h4>
      <div style={{height:320}}>
        <ResponsiveContainer>
          <BarChart data={catData}>
            <XAxis dataKey="category" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {stats && (
        <>
          <h4 style={{marginTop:16}}>Price Summary</h4>
          <pre>{JSON.stringify(stats, null, 2)}</pre>
        </>
      )}
    </div>
  );
}
