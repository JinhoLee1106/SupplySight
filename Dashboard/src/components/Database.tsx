import { useEffect, useState } from "react";

export function Database() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"monthly" | "daily">("monthly");

  useEffect(() => {
    setLoading(true);

    const url =
      mode === "monthly"
        ? "http://127.0.0.1:8000/api/raw"
        : "http://127.0.0.1:8000/api/raw-daily";

    fetch(url)
      .then(res => res.json())
      .then(res => {
        console.log("DATA:", res);
        setData(res);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [mode]);

  if (loading) return <div className="p-6">Loading...</div>;
  if (data.length === 0) return <div className="p-6">No data</div>;

  const columns = Object.keys(data[0]);



  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl">Database (Raw)</h1>


      <div className="flex gap-2">
        <button
          onClick={() => setMode("monthly")}
          className={`px-4 py-2 rounded ${
            mode === "monthly" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
        >
          Monthly
        </button>

        <button
          onClick={() => setMode("daily")}
          className={`px-4 py-2 rounded ${
            mode === "daily" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
        >
          Daily
        </button>
      </div>


      <div className="overflow-auto border rounded">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-100">
          <tr>
            {columns.map(col => (
                <th key={col} className="p-2 border">
                  {col}
                </th>
            ))}
          </tr>
          </thead>

          <tbody>
          {data.map((row, i) => (
              <tr key={i}>
                {columns.map(col => (
                    <td key={col} className="p-2 border text-center">
                      {row[col] ?? "-"}
                    </td>
                ))}
              </tr>
          ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}