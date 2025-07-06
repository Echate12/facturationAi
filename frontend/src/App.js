import React, { useState } from 'react';
import './App.css';

const DOC_TYPES = [
  'Facture',
  'Devis',
  'Bon de commande',
  'Bon de livraison',
];

function App() {
  const [prompt, setPrompt] = useState('');
  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleParse = async () => {
    setLoading(true);
    setError('');
    setItems([]);
    try {
      const res = await fetch('http://localhost:5000/api/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      if (data.items) setItems(data.items);
      else setError('No items found.');
    } catch (e) {
      setError('Error parsing prompt.');
    }
    setLoading(false);
  };

  const handleItemChange = (idx, field, value) => {
    setItems(items => items.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  };

  const handleGeneratePDF = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('http://localhost:5000/api/generate-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items, docType }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${docType}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError('Error generating PDF.');
    }
    setLoading(false);
  };

  return (
    <div className="App">
      <h1>Facturation AI WebApp</h1>
      <div className="input-section">
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Enter items, e.g. '2x Widget A at $10, 5x Widget B at $20 for Client X'"
          rows={3}
        />
        <select value={docType} onChange={e => setDocType(e.target.value)}>
          {DOC_TYPES.map(type => <option key={type} value={type}>{type}</option>)}
        </select>
        <button onClick={handleParse} disabled={loading || !prompt}>Parse</button>
      </div>
      {error && <div className="error">{error}</div>}
      {loading && <div>Loading...</div>}
      {items.length > 0 && (
        <div className="table-section">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Reference</th>
                <th>Name</th>
                <th>Quantity</th>
                <th>Unit Price</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr key={idx}>
                  <td>{idx + 1}</td>
                  <td><input value={item.reference || ''} onChange={e => handleItemChange(idx, 'reference', e.target.value)} /></td>
                  <td><input value={item.name || ''} onChange={e => handleItemChange(idx, 'name', e.target.value)} /></td>
                  <td><input type="number" value={item.quantity || ''} onChange={e => handleItemChange(idx, 'quantity', e.target.value)} /></td>
                  <td><input type="number" value={item.unit_price || ''} onChange={e => handleItemChange(idx, 'unit_price', e.target.value)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          <button onClick={handleGeneratePDF} disabled={loading}>Generate PDF</button>
        </div>
      )}
    </div>
  );
}

export default App;
